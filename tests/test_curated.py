from datetime import datetime
import json
from pathlib import Path
import sqlite3

import pytest

from core.ai_search import Plan, filter_requirements
from core.hours import format_hours, visit_status
from core.retrieval import get_candidates
from ingestion.build_database import build_database
from ingestion.curated import load_curated
from ingestion.deduplicate import deduplicate_records

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/curated_places.json"
SNAPSHOTS = [ROOT / "data/snapshots/astana.json", ROOT / "data/snapshots/airport.json"]


def test_curated_rebuild_is_complete_and_idempotent(tmp_path):
    db = tmp_path / "pois.db"
    for _ in range(2):
        stats = build_database(SNAPSHOTS, db, ROOT / "data/manual_overrides.csv", CURATED)
        assert stats["curated_places_loaded"] == 10
        assert stats["usable"] == 207
        assert stats["duplicate_places_removed"] == 2
    with sqlite3.connect(db) as rebuilt, sqlite3.connect(ROOT / "data/pois.db") as shipped:
        assert rebuilt.execute("SELECT * FROM pois ORDER BY id").fetchall() == shipped.execute(
            "SELECT * FROM pois ORDER BY id").fetchall()


@pytest.mark.parametrize("problem", ["coordinates", "evidence", "duplicate_id"])
def test_invalid_curated_data_leaves_database_untouched(tmp_path, problem):
    rows = json.loads(CURATED.read_text(encoding="utf-8"))
    if problem == "coordinates":
        rows[0]["lat"], rows[0]["lon"] = rows[0]["lon"], rows[0]["lat"]
    elif problem == "evidence":
        del rows[0]["evidence"]["opening_hours"]
    else:
        rows.append(rows[0])
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(rows), encoding="utf-8")
    db = tmp_path / "existing.db"
    db.write_bytes((ROOT / "data/pois.db").read_bytes())
    before = db.read_bytes()
    with pytest.raises(ValueError):
        build_database(SNAPSHOTS, db, curated_path=invalid)
    assert db.read_bytes() == before


def test_new_budget_coffee_candidates_respect_distance_and_time():
    candidates = get_candidates((51.10514, 71.431063), 60, db_path=ROOT / "data/pois.db")
    plan = Plan(categories=["cafe"], coffee_shop_only=True,
                max_average_check_kzt=2000, duration_minutes=None)
    selected = filter_requirements(candidates, plan)
    assert "2gis:70000001045554424" in {row.id for row in selected}
    assert all(row.total_minutes <= 60 and float(row.tags["average_check:kzt"]) <= 2000 for row in selected)
    far = get_candidates((51.17, 71.42), 30, db_path=ROOT / "data/pois.db")
    assert "2gis:70000001045554424" not in {row.id for row in far}


def test_museum_monthly_closure_and_park_uncertainty():
    rows = {row["id"]: row for row in load_curated(CURATED)}
    schedule = rows["2gis:70000001018608940"]["opening_hours"]
    assert visit_status(schedule, datetime(2026, 10, 20, 12), 35) == "open"
    assert visit_status(schedule, datetime(2026, 10, 27, 12), 35) == "closed"
    assert visit_status(schedule, datetime(2026, 12, 29, 12), 35) == "closed"
    assert visit_status(schedule, datetime(2026, 10, 26, 12), 35) == "closed"
    assert visit_status(schedule, datetime(2026, 10, 20, 17, 45), 35) == "closes_during_visit"
    assert "последний Вт месяца" in format_hours(schedule)
    assert rows["2gis:70000001061880425"]["opening_hours"] is None


def test_mega_transliteration_without_language_alias_tags():
    first = dict(id="osm:way:1", name="Mega Silk Way", category="mall", lat=51.1, lon=71.4,
                 tags_json="{}", verified_fields_json="{}")
    second = {**first, "id": "osm:node:2", "name": "Мега Силк Вей"}
    assert len(deduplicate_records([first, second])[0]) == 1
