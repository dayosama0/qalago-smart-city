"""Published hours survive rebuilding and reach cards with their own evidence."""
import csv
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from core.hours import visit_status
from core.models import RecommendRequest
from core.recommend import recommend
from core.retrieval import get_candidates
from ingestion.build_database import build_database

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_hours_survive_offline_rebuild(tmp_path):
    database = tmp_path / "hours.db"
    build_database([ROOT / "data/snapshots/astana.json", ROOT / "data/snapshots/airport.json"],
                   database, ROOT / "data/manual_overrides.csv", ROOT / "data/curated_places.json")
    with (ROOT / "data/hours_review.tsv").open(encoding="utf-8", newline="") as handle:
        reviewed = list(csv.DictReader(handle, delimiter="\t"))
    with sqlite3.connect(database) as rebuilt, sqlite3.connect(ROOT / "data/pois.db") as shipped:
        query = "SELECT id,opening_hours,verified_fields_json FROM pois ORDER BY id"
        assert rebuilt.execute(query).fetchall() == shipped.execute(query).fetchall()
        for row in reviewed:
            # The reviewed node and polygon describe the same MEGA building.
            poi_id = {"osm:node:4965336822": "osm:way:499328514"}.get(row["poi_id"], row["poi_id"])
            hours, metadata = rebuilt.execute(
                "SELECT opening_hours,verified_fields_json FROM pois WHERE id=?", (poi_id,)).fetchone()
            assert hours == row["opening_hours"]
            evidence = json.loads(metadata)["opening_hours"]
            assert evidence["evidence_url"] == row["evidence_url"]
            assert evidence["checked_at"] == "2026-10-20"
            assert visit_status(hours, datetime(2026, 10, 20, 12), 20) != "unknown"


def test_cards_retain_hours_evidence():
    result = recommend(RecommendRequest(location_preset="baiterek", weather_mode="clear",
                       time_mode="simulated", simulated_datetime="2026-10-20T12:00:00"), use_llm=False)
    assert result.recommendations
    with sqlite3.connect(ROOT / "data/pois.db") as connection:
        for card in result.recommendations:
            metadata, source = connection.execute(
                "SELECT verified_fields_json,source_url FROM pois WHERE id=?", (card.poi_id,)).fetchone()
            evidence = json.loads(metadata).get("opening_hours", {})
            assert card.opening_hours_source == evidence.get("evidence_url", source)
            if evidence:
                assert card.opening_hours_checked_at == evidence["checked_at"]
                assert evidence["evidence_url"] in card.opening_note


def test_verified_breaks_weekends_and_midnight():
    with sqlite3.connect(ROOT / "data/pois.db") as connection:
        def hours(poi_id):
            return connection.execute("SELECT opening_hours FROM pois WHERE id=?", (poi_id,)).fetchone()[0]
        assert visit_status(hours("osm:way:230401645"), datetime(2026, 10, 20, 13, 15), 0) == "closed"
        assert visit_status(hours("osm:way:240376692"), datetime(2026, 10, 19, 12), 20) == "closed"
        assert visit_status(hours("osm:node:12041597369"), datetime(2026, 10, 20, 0), 20) == "closed"
        assert visit_status(hours("osm:node:4246528694"), datetime(2026, 10, 20, 1), 20) == "open"
        # Saturday 01:00 belongs to Friday's late service at Asatu.
        assert visit_status(hours("osm:node:12973410493"), datetime(2026, 10, 24, 1), 20) == "open"
        assert visit_status(hours("osm:node:12973410493"), datetime(2026, 10, 20, 1), 20) == "closed"
        # Espresso Bar opens later on weekends; the park schedule is an override.
        assert visit_status(hours("osm:node:5074875221"), datetime(2026, 10, 24, 7, 45), 0) == "closed"
        assert visit_status(hours("osm:node:5074875221"), datetime(2026, 10, 23, 7, 45), 0) == "open"
        assert visit_status(hours("2gis:70000001061880425"), datetime(2026, 10, 20, 3), 20) == "open"
        # Fuller's is closed on Monday; Tuesday's service continues into Wednesday.
        assert visit_status(hours("osm:node:5890174288"), datetime(2026, 10, 19, 19), 20) == "closed"
        assert visit_status(hours("osm:node:5890174288"), datetime(2026, 10, 21, 1), 20) == "open"
        assert visit_status(hours("osm:node:5890174288"), datetime(2026, 10, 21, 1, 50), 20) == "closes_during_visit"
        assert visit_status(hours("osm:node:4922406025"), datetime(2026, 10, 24, 9), 20) == "closed"
        assert visit_status(hours("osm:node:4922406025"), datetime(2026, 10, 23, 9), 20) == "open"


def test_gap_review_retains_unknowns_and_excludes_reported_closures():
    audit = json.loads((ROOT / "data/hours_gap_review_2026-10-20.json").read_text(encoding="utf-8"))
    assert len(audit["records"]) == audit["initial_missing_count"]
    assert len({row["poi_id"] for row in audit["records"]}) == audit["initial_missing_count"]
    with sqlite3.connect(ROOT / "data/pois.db") as connection:
        for row in audit["records"]:
            hours, raw_metadata = connection.execute(
                "SELECT opening_hours,verified_fields_json FROM pois WHERE id=?", (row["poi_id"],)).fetchone()
            if row["result"] == "unresolved":
                assert not hours  # Conflicting/absent evidence must not become 24/7.
                continue
            assert hours == row["opening_hours"]
            evidence = json.loads(raw_metadata)["opening_hours"]
            assert evidence["evidence_url"] == row["evidence_url"]
            assert evidence["checked_at"] == audit["checked_at"]
            if row["result"] in {"temporarily_closed", "permanently_closed"}:
                candidates = get_candidates((row["lat"], row["lon"]), 120, db_path=ROOT / "data/pois.db")
                assert candidates
                assert row["poi_id"] not in {candidate.id for candidate in candidates}
