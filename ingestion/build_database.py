"""Run as `python -m ingestion.build_database [--offline]`."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

from ingestion.fetch_osm import AREAS, DownloadError, cached_snapshots, download_area, utc_now
from ingestion.normalize import normalize_elements
from ingestion.deduplicate import deduplicate_records
from ingestion.curated import load_curated

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = """
CREATE TABLE IF NOT EXISTS pois (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  category TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '{}',
  description TEXT,
  description_source TEXT,
  opening_hours TEXT,
  indoor_status TEXT NOT NULL DEFAULT 'unknown',
  power_outlets_status TEXT NOT NULL DEFAULT 'unknown',
  wifi_status TEXT NOT NULL DEFAULT 'unknown',
  visit_minutes INTEGER NOT NULL DEFAULT 20,
  verified_fields_json TEXT NOT NULL DEFAULT '{}',
  source TEXT NOT NULL DEFAULT 'OpenStreetMap',
  source_url TEXT,
  fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pois_lat_lon ON pois(lat, lon);
CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
"""
OVERRIDE_FIELDS = {"description", "indoor_status", "power_outlets_status", "wifi_status", "opening_hours", "visit_minutes"}
INDOOR_VALUES = {"confirmed_indoor", "likely_indoor", "outdoor", "unknown"}
FEATURE_VALUES = {"confirmed", "no", "unknown"}


def apply_overrides(records: list[dict], path: Path) -> int:
    """Apply only evidenced field-level facts; reject missing source IDs."""
    if not path.is_file():
        return 0
    by_id = {row["id"]: row for row in records}
    applied = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"poi_id", "field", "value", "evidence_url", "checked_at"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Override CSV requires: " + ", ".join(sorted(required)))
        for line, override in enumerate(reader, 2):
            poi_id, field = override["poi_id"].strip(), override["field"].strip()
            if poi_id not in by_id:
                raise ValueError(f"Override line {line}: missing OSM ID {poi_id}; remove or recheck the override")
            if field not in OVERRIDE_FIELDS:
                raise ValueError(f"Override line {line}: field is not allowed: {field}")
            value = override["value"].strip()
            evidence_url, checked_at = override["evidence_url"].strip(), override["checked_at"].strip()
            parsed_url = urlparse(evidence_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError(f"Override line {line}: public HTTP(S) evidence URL required")
            try:
                datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(f"Override line {line}: checked_at must be an ISO date/time") from error
            if field == "indoor_status" and value not in INDOOR_VALUES:
                raise ValueError(f"Override line {line}: invalid indoor status")
            if field in {"power_outlets_status", "wifi_status"} and value not in FEATURE_VALUES:
                raise ValueError(f"Override line {line}: invalid feature status")
            if field == "visit_minutes":
                try:
                    value = int(value)
                except ValueError as error:
                    raise ValueError(f"Override line {line}: visit_minutes must be an integer") from error
                if not 1 <= value <= 480:
                    raise ValueError(f"Override line {line}: visit_minutes must be 1..480")
            elif not value:
                raise ValueError(f"Override line {line}: empty override values are not accepted")
            record = by_id[poi_id]
            record[field] = value
            if field == "description":
                record["description_source"] = evidence_url
            provenance = json.loads(record["verified_fields_json"])
            provenance[field] = {"evidence_url": evidence_url, "checked_at": checked_at, "method": "manual_reference"}
            record["verified_fields_json"] = json.dumps(provenance, ensure_ascii=False, sort_keys=True)
            applied += 1
    return applied


def write_database(records: list[dict], db_path: Path) -> dict:
    """Atomic transaction, stable keys, and removal of records absent from rebuild."""
    if not records:
        raise ValueError("No usable genuine POIs: refusing to replace an existing snapshot")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(records[0])
    names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{key}=excluded.{key}" for key in columns if key != "id")
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        existing_ids = {row[0] for row in connection.execute("SELECT id FROM pois")}
        current_ids = {row["id"] for row in records}
        connection.executemany(
            f"INSERT INTO pois ({names}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            [[record[key] for key in columns] for record in records],
        )
        # Temporary staging avoids SQLite parameter count limits for large snapshots.
        connection.execute("CREATE TEMP TABLE current_ids (id TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO current_ids VALUES (?)", [(value,) for value in current_ids])
        connection.execute("DELETE FROM pois WHERE id NOT IN (SELECT id FROM current_ids)")
        usable, hours, descriptions = connection.execute(
            "SELECT COUNT(*), SUM(opening_hours IS NOT NULL AND opening_hours != ''), "
            "SUM(description IS NOT NULL AND description != '') FROM pois"
        ).fetchone()
        validation = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if validation != "ok":
            raise ValueError(f"SQLite validation failed: {validation}")
    return {"usable": usable, "opening_hours_available": hours, "descriptions_available": descriptions,
            "merged_replaced": len(existing_ids & current_ids), "removed_stale": len(existing_ids - current_ids),
            "sqlite_integrity": validation}


def build_database(raw_paths: list[Path], db_path: Path, overrides_path: Path | None = None,
                   curated_path: Path | None = None) -> dict:
    all_records: dict[str, dict] = {}
    downloaded = dropped = duplicates = 0
    source_snapshots = []
    for path in raw_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list) or payload.get("remark"):
            raise ValueError(f"Invalid/incomplete snapshot: {path}")
        metadata_path = path.with_suffix(".metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        # OSM source timestamp is honest fallback for manually cached public JSON.
        fetched_at = metadata.get("fetched_at") or payload.get("osm3s", {}).get("timestamp_osm_base")
        if not fetched_at:
            raise ValueError(f"Snapshot {path} needs fetched_at metadata or OSM base timestamp")
        records, invalid, repeated = normalize_elements(payload["elements"], fetched_at)
        downloaded += len(payload["elements"])
        dropped += invalid
        duplicates += repeated
        for record in records:
            duplicates += int(record["id"] in all_records)
            all_records[record["id"]] = record
        source_snapshots.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "raw_elements": len(payload["elements"]), "fetched_at": fetched_at,
                                 "osm_timestamp": payload.get("osm3s", {}).get("timestamp_osm_base")})
    records = list(all_records.values())
    curated = load_curated(curated_path) if curated_path is not None else []
    records.extend(curated)
    overrides_applied = apply_overrides(records, overrides_path) if overrides_path is not None else 0
    records, duplicate_places = deduplicate_records(records)
    stats = write_database(records, db_path)
    stats["duplicate_places_removed"] = duplicate_places
    stats["curated_places_loaded"] = len(curated)
    if curated_path is not None:
        stats["curated_dataset"] = {"file": curated_path.name,
                                    "sha256": hashlib.sha256(curated_path.read_bytes()).hexdigest()}
    stats.update({"downloaded_elements": downloaded, "dropped_invalid_or_unnamed": dropped,
                  "duplicate_osm_ids": duplicates, "overrides_applied": overrides_applied,
                  "last_fetched_at": max(row["fetched_at"] for row in records),
                  "source_snapshots": source_snapshots,
                  "database_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest()})
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Require cached astana.json and airport.json; no HTTP")
    parser.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "pois.db")
    parser.add_argument("--raw-dir", type=Path, default=None,
                        help="Defaults to shipped data/snapshots offline, data/raw for live Overpass")
    parser.add_argument("--overrides", type=Path, default=PROJECT_ROOT / "data" / "manual_overrides.csv")
    parser.add_argument("--curated", type=Path, default=PROJECT_ROOT / "data" / "curated_places.json")
    parser.add_argument("--attempts", type=int, choices=range(1, 4), default=3)
    args = parser.parse_args()
    if args.raw_dir is None:
        args.raw_dir = PROJECT_ROOT / "data" / ("snapshots" if args.offline else "raw")
    try:
        paths = cached_snapshots(args.raw_dir) if args.offline else [
            download_area(area, args.raw_dir, attempts=args.attempts) for area in AREAS
        ]
        stats = build_database(paths, args.db, args.overrides, args.curated)
        stats["build_mode"] = "offline_cached_osm" if args.offline else "live_download"
        stats["built_at"] = utc_now()
        args.db.with_suffix(".manifest.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    except (DownloadError, ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Ingestion failed: {error}\nExisting database preserved when no complete rebuild is available.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
