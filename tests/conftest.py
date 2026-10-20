"""Offline backend test data is deliberately synthetic and isolated."""
import json
from pathlib import Path
import sqlite3

import pytest


@pytest.fixture
def synthetic_db(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    path = tmp_path / "synthetic-test-only.db"
    fixture = json.loads((Path(__file__).parent / "fixtures" / "pois_test.json").read_text(encoding="utf-8"))
    assert "SYNTHETIC" in fixture["provenance"]
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE pois (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
              category TEXT NOT NULL, tags_json TEXT NOT NULL DEFAULT '{}', description TEXT,
              description_source TEXT, opening_hours TEXT, indoor_status TEXT NOT NULL DEFAULT 'unknown',
              power_outlets_status TEXT NOT NULL DEFAULT 'unknown', wifi_status TEXT NOT NULL DEFAULT 'unknown',
              visit_minutes INTEGER NOT NULL DEFAULT 20, verified_fields_json TEXT NOT NULL DEFAULT '{}',
              source TEXT NOT NULL DEFAULT 'SYNTHETIC TEST FIXTURE', source_url TEXT,
              fetched_at TEXT NOT NULL
            );
        """)
        for row in fixture["pois"]:
            row = {"fetched_at": "2026-01-01T00:00:00+05:00", "source_url": "https://example.invalid/synthetic", **row}
            fields = ",".join(row)
            placeholders = ",".join("?" for _ in row)
            connection.execute(f"INSERT INTO pois ({fields}) VALUES ({placeholders})", list(row.values()))
    return path
