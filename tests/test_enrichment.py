"""Offline integrity checks for field-level enrichment of the shipped artifact."""

import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from ingestion.normalize import normalize_elements

ROOT = Path(__file__).resolve().parents[1]


def source_records():
    records = {}
    for area in ("astana", "airport"):
        path = ROOT / "data" / "snapshots" / f"{area}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        normalized, _, _ = normalize_elements(payload["elements"], metadata["fetched_at"])
        records.update({row["id"]: row for row in normalized})
    return records


def test_enrichment_preserves_the_original_osm_identity_and_unknown_features():
    originals = source_records()
    with sqlite3.connect((ROOT / "data" / "pois.db").resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM pois").fetchall()
    assert {row["id"] for row in rows} == set(originals)
    for row in rows:
        original = originals[row["id"]]
        for field in ("name", "lat", "lon", "category", "tags_json", "indoor_status", "power_outlets_status", "wifi_status"):
            assert row[field] == original[field], (row["id"], field)


def test_every_enriched_field_has_the_exact_recorded_public_reference():
    with (ROOT / "data" / "manual_overrides.csv").open(encoding="utf-8", newline="") as handle:
        overrides = list(csv.DictReader(handle))
    assert 5 <= len({row["poi_id"] for row in overrides}) <= 8
    assert len({(row["poi_id"], row["field"]) for row in overrides}) == len(overrides)
    with sqlite3.connect((ROOT / "data" / "pois.db").resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        records = {row["id"]: row for row in connection.execute("SELECT * FROM pois")}
    for override in overrides:
        assert override["field"] in {"description", "opening_hours"}
        record = records[override["poi_id"]]
        assert record[override["field"]] == override["value"]
        provenance = json.loads(record["verified_fields_json"])[override["field"]]
        assert provenance == {"evidence_url": override["evidence_url"],
                              "checked_at": override["checked_at"], "method": "manual_reference"}
        if override["field"] == "description":
            assert record["description_source"] == override["evidence_url"]


def test_enrichment_keeps_original_snapshot_bytes():
    expected = {
        "astana.json": "fb45c09f37c7d97da322fdd631d873dffaab5be2b73eb1a576c6e43f7de079b4",
        "airport.json": "dd4fe276faa43c16f094f6ed3d53cfd260c1ec5a5ba8ed050327d501d0fd43bd",
    }
    for name, digest in expected.items():
        assert sha256((ROOT / "data" / "snapshots" / name).read_bytes()).hexdigest() == digest
