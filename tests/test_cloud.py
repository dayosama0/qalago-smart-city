"""Offline integration checks for the actual artifact shipped to Community Cloud."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tomllib

import pytest
import requests
import streamlit
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pois.db"


def test_shipped_snapshot_has_valid_source_records_and_manifest():
    manifest = json.loads((ROOT / "data" / "pois.manifest.json").read_text(encoding="utf-8"))
    assert sha256(DATABASE.read_bytes()).hexdigest() == manifest["database_sha256"]
    with sqlite3.connect(DATABASE.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        rows = connection.execute("SELECT * FROM pois").fetchall()
    assert len(rows) == manifest["usable"] > 0
    assert len({row["id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["name"].strip() and "SYNTHETIC" not in row["name"]
        assert -90 <= row["lat"] <= 90 and -180 <= row["lon"] <= 180
        kind, number = row["id"].removeprefix("osm:").split(":")
        assert kind in {"node", "way", "relation"} and int(number) > 0
        assert row["source"] == "OpenStreetMap"
        assert row["source_url"] == f"https://www.openstreetmap.org/{kind}/{number}"
        tags = json.loads(row["tags_json"])
        assert not any(key.startswith("contact:") or key in {"phone", "email", "fax"} for key in tags)
    for snapshot in manifest["source_snapshots"]:
        path = ROOT / "data" / "snapshots" / snapshot["file"]
        snapshot_bytes = path.read_bytes()
        assert b"\r\n" not in snapshot_bytes  # Stable hashes after Windows/Linux checkout.
        assert sha256(snapshot_bytes).hexdigest() == snapshot["sha256"]


@pytest.fixture
def offline_app(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("WEATHER_ENABLED", "0")
    # Even a developer's ignored local Cloud secrets must not trigger a paid call.
    monkeypatch.setattr(streamlit, "secrets", {})

    def unexpected_network(*args, **kwargs):
        raise AssertionError("Default startup/recommendation must not use network")

    monkeypatch.setattr(requests, "get", unexpected_network)
    monkeypatch.setattr(requests, "post", unexpected_network)
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def test_cloud_start_and_recommend_without_secrets_network_or_db_writes(offline_app):
    before = sha256(DATABASE.read_bytes()).hexdigest()
    assert not offline_app.exception
    assert not offline_app.button[0].disabled
    offline_app.button[0].click().run()
    assert not offline_app.exception
    response = offline_app.session_state["qalago_result"][1]
    assert response.answer_mode == "template"
    options = [*response.recommendations, *response.alternatives]
    assert 1 <= len(options) <= 3
    assert response.weather.is_simulated
    assert len(offline_app.subheader) == len(options)
    assert sha256(DATABASE.read_bytes()).hexdigest() == before


def test_changing_controls_hides_stale_result(offline_app):
    offline_app.button[0].click().run()
    assert offline_app.subheader
    offline_app.selectbox[0].select("baiterek").run()
    assert not offline_app.exception
    assert not offline_app.subheader
    assert any("Условия изменились" in item.value for item in offline_app.info)


def test_airport_flight_ui_has_no_excursion(offline_app):
    offline_app.selectbox[0].select("airport").run()
    offline_app.checkbox[2].check().run()
    offline_app.button[0].click().run()
    assert not offline_app.exception
    response = offline_app.session_state["qalago_result"][1]
    assert response.recommendations == []
    assert "аэропорт" in response.general_message


def test_cloud_configuration_keeps_credential_files_separate():
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["server"]["headless"]
    assert config["server"]["enableXsrfProtection"]
    assert config["browser"]["gatherUsageStats"] is False
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=\n" in env_example
