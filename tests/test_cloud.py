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
    assert 1 <= len(response.recommendations) <= 20
    assert not response.weather.is_simulated
    assert response.weather.status == "unknown"  # Offline weather must not imply clear skies.
    assert len(offline_app.subheader) == min(6, len(response.recommendations))
    assert sha256(DATABASE.read_bytes()).hexdigest() == before


def test_changing_controls_hides_stale_result(offline_app):
    offline_app.button[0].click().run()
    assert offline_app.subheader
    offline_app.selectbox[0].select("baiterek").run()
    assert not offline_app.exception
    assert not offline_app.subheader
    assert any("Условия изменились" in item.value for item in offline_app.info)


def test_sorting_uses_stored_result_without_search(offline_app, monkeypatch):
    from core.result_order import sort_results

    offline_app.button[0].click().run()
    assert not offline_app.exception
    stored = offline_app.session_state["qalago_result"]
    assert len(stored[1].recommendations) > 3

    def unexpected_search(*args, **kwargs):
        raise AssertionError("Sorting must not run a new search")

    monkeypatch.setattr("core.recommend.recommend", unexpected_search)
    offline_app.selectbox(key="result_sort").select("name").run()
    assert not offline_app.exception
    expected = sort_results(stored[1].recommendations, "name")
    assert [item.value for item in offline_app.subheader] == [
        f"{index}. {card.name}" for index, card in enumerate(expected[:6], 1)]


def test_more_results_reveals_stored_cards_and_new_search_resets(offline_app, monkeypatch):
    offline_app.button[0].click().run()
    original = offline_app.session_state["qalago_result"]
    assert len(original[1].recommendations) > 12
    assert len(offline_app.subheader) == 6
    map_panel = next(item for item in offline_app.expander if item.label == "Посмотреть на карте")
    advanced = next(item for item in offline_app.expander if item.label == "Дополнительные условия")
    assert not map_panel.proto.expanded
    assert not advanced.proto.expanded
    with monkeypatch.context() as patch:
        def unexpected_search(*args, **kwargs):
            raise AssertionError("Showing more must not repeat retrieval or LLM calls")
        patch.setattr("core.recommend.recommend", unexpected_search)
        more = next(item for item in offline_app.button if item.label == "Показать ещё места")
        more.click().run()
        assert not offline_app.exception
        assert len(offline_app.subheader) == 12
        assert offline_app.session_state["qalago_result"][0] == original[0]
        assert len({item.value for item in offline_app.subheader}) == 12
    offline_app.button[0].click().run()
    assert not offline_app.exception
    assert len(offline_app.subheader) == 6


def test_weather_simulation_is_visible_outside_advanced_controls(offline_app):
    weather = next(item for item in offline_app.selectbox if item.label == "Погода")
    weather.select("Дождь · симуляция").run()
    offline_app.button[0].click().run()
    assert not offline_app.exception
    result = offline_app.session_state["qalago_result"][1]
    assert result.weather.is_simulated
    assert any("Погода: учебный сценарий" in item.value for item in offline_app.main.caption)


def test_airport_flight_ui_has_no_excursion(offline_app):
    offline_app.selectbox[0].select("airport").run()
    offline_app.checkbox(key="flight_constraint").check().run()
    offline_app.button[0].click().run()
    assert not offline_app.exception
    response = offline_app.session_state["qalago_result"][1]
    assert response.recommendations == []
    assert "аэропорт" in response.general_message
    assert any("Мест не найдено" in item.value for item in offline_app.error)


def test_closed_cards_have_visible_hours_and_collapsed_details(offline_app, monkeypatch):
    from core.models import Recommendation, RecommendResponse
    import core.recommend

    card = Recommendation(poi_id="test", name="Closed test", category="cafe", lat=51.1, lon=71.4,
                          distance_m=100, travel_minutes_estimated=2, visit_minutes_estimated=20,
                          reason="Details", action="Visit", opening_note="Source hours", indoor_status="unknown",
                          source="Test", source_url="https://example.com", opening_hours="Mo-Fr 09:00-18:00",
                          opening_status="closed", arrival_datetime="2026-10-19T20:00:00+05:00",
                          opening_status_now="closed",
                          description="A concise description <with escaped text>.",
                          description_source="https://example.com/description")
    monkeypatch.setattr(core.recommend, "recommend", lambda *args, **kwargs: RecommendResponse(recommendations=[card]))
    offline_app.button[0].click().run()
    assert not offline_app.exception
    assert any("Сейчас закрыто" in item.value and "Пн-Пт" in item.value for item in offline_app.markdown)
    assert any("A concise description &lt;with escaped text&gt;." in item.value for item in offline_app.markdown)
    assert any(item.label == "Источник описания" for item in offline_app.get("link_button"))
    details = next(item for item in offline_app.expander if item.label == "Подробнее")
    assert not details.proto.expanded


def test_cloud_configuration_keeps_credential_files_separate():
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["server"]["headless"]
    assert config["server"]["enableXsrfProtection"]
    assert config["browser"]["gatherUsageStats"] is False
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=\n" in env_example


def test_custom_time_reaches_backend_and_invalidates_results(offline_app):
    offline_app.selectbox(key="duration_choice").select("custom").run()
    offline_app.number_input[0].set_value(77).run()
    offline_app.button[0].click().run()
    assert not offline_app.exception
    _, result, request = offline_app.session_state["qalago_result"]
    assert request.duration_minutes == 77
    assert all(card.total_minutes_estimated <= 77 for card in result.recommendations)
    offline_app.number_input[0].set_value(78).run()
    assert not offline_app.subheader
    assert any("Условия изменились" in item.value for item in offline_app.info)


def test_live_results_expire_at_new_minute_and_show_sidebar_conditions(offline_app, monkeypatch):
    from datetime import datetime
    from config import TIMEZONE
    import core.clock
    import core.recommend as backend

    clock = [datetime(2026, 10, 19, 12, 0, tzinfo=TIMEZONE)]
    monkeypatch.setattr(core.clock, "local_now", lambda: clock[0])
    monkeypatch.setattr(backend, "local_now", lambda: clock[0])
    offline_app.button[0].click().run()
    assert offline_app.session_state["qalago_result"][1].local_datetime == clock[0].isoformat()
    clock[0] = datetime(2026, 10, 20, 0, 0, tzinfo=TIMEZONE)
    monkeypatch.setattr(backend, "generate_explanations", lambda *args: pytest.fail("Clock refresh must not call the LLM"))
    offline_app.run()
    assert not offline_app.exception
    result = offline_app.session_state["qalago_result"][1]
    assert result.local_datetime == clock[0].isoformat()
    assert any("Условия подбора" in item.value for item in offline_app.sidebar.markdown)
    assert not any("Условия подбора" in item.value for item in offline_app.main.markdown)
    assert any("**≈" in item.value and "мин пешком" in item.value for item in offline_app.main.markdown)


def test_simulated_result_keeps_selected_time(offline_app, monkeypatch):
    from datetime import datetime
    from config import TIMEZONE
    import core.clock

    offline_app.radio(key="time_choice").set_value("Симуляция").run()
    offline_app.button[0].click().run()
    original = offline_app.session_state["qalago_result"][1].local_datetime
    monkeypatch.setattr(core.clock, "local_now", lambda: datetime(2030, 1, 1, tzinfo=TIMEZONE))
    offline_app.run()
    assert not offline_app.exception
    assert offline_app.session_state["qalago_result"][1].local_datetime == original
