"""Editorial coverage, offline reproducibility and the DB-to-card contract."""
import csv
import json
from pathlib import Path
import sqlite3

from core.models import RecommendRequest
from core.recommend import recommend
from ingestion.build_database import build_database

ROOT = Path(__file__).resolve().parents[1]


def test_all_shipped_descriptions_are_distinct_and_evidenced():
    with (ROOT / "data/manual_overrides.csv").open(encoding="utf-8", newline="") as handle:
        overrides = {row["poi_id"]: row for row in csv.DictReader(handle) if row["field"] == "description"}
    with sqlite3.connect(ROOT / "data/pois.db") as connection:
        rows = connection.execute("SELECT id,description,description_source,verified_fields_json FROM pois").fetchall()
    assert len(rows) == len(overrides) == len({row[1] for row in rows}) == 199
    for poi_id, text, source, metadata in rows:
        assert 40 <= len(text) <= 320
        assert text == overrides[poi_id]["value"]
        assert source == overrides[poi_id]["evidence_url"]
        assert source.startswith("https://")
        assert json.loads(metadata)["description"]["checked_at"] == overrides[poi_id]["checked_at"]


def test_offline_rebuild_preserves_editorial_texts_and_sources(tmp_path):
    database = tmp_path / "rebuilt.db"
    stats = build_database([ROOT / "data/snapshots/astana.json", ROOT / "data/snapshots/airport.json"],
                           database, ROOT / "data/manual_overrides.csv")
    assert stats["descriptions_available"] == 199
    with (ROOT / "data/manual_overrides.csv").open(encoding="utf-8", newline="") as handle:
        assert stats["overrides_applied"] == len(list(csv.DictReader(handle)))
    query = "SELECT id,description,description_source FROM pois ORDER BY id"
    with sqlite3.connect(database) as rebuilt, sqlite3.connect(ROOT / "data/pois.db") as shipped:
        assert rebuilt.execute(query).fetchall() == shipped.execute(query).fetchall()


def test_recommendations_keep_exact_database_descriptions(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    result = recommend(RecommendRequest(location_preset="baiterek", weather_mode="clear",
                       time_mode="simulated", simulated_datetime="2026-10-20T12:00:00"))
    assert result.recommendations
    with sqlite3.connect(ROOT / "data/pois.db") as connection:
        for card in result.recommendations:
            assert card.description
            assert (card.description, card.description_source) == connection.execute(
                "SELECT description,description_source FROM pois WHERE id = ?", (card.poi_id,)).fetchone()
