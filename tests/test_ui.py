"""Offline UI interactions against the shipped real snapshot; no provider calls."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pytest
import requests
import streamlit
from streamlit.testing.v1 import AppTest

from core.models import RecommendRequest
from config import TIMEZONE
from ui import interface

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ui_app(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("WEATHER_ENABLED", "0")
    monkeypatch.setattr(streamlit, "secrets", {})
    # Fixed test clock: the real mall's listed hours must not make this
    # provenance test depend on the time at which CI happens to run.
    import core.recommend as recommendations
    original_clock = recommendations._request_time
    monkeypatch.setattr(recommendations, "_request_time", lambda request:
                        datetime(2026, 10, 19, 14, 0, tzinfo=TIMEZONE)
                        if request.time_mode == "live" else original_clock(request))

    def unexpected_network(*args, **kwargs):
        raise AssertionError("UI scenarios must use the local snapshot and simulated weather")

    monkeypatch.setattr(requests, "get", unexpected_network)
    monkeypatch.setattr(requests, "post", unexpected_network)
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


@pytest.mark.parametrize("scenario,origin,duration,weather,flight", [
    ("walk", "expo", 60, "clear", False),
    ("child", "central_park", 120, "clear", False),
    ("wind", "expo", 60, "wind", False),
    ("flight", "airport", 120, "clear", True),
])
def test_quick_scenarios_set_real_controls_and_execute_fresh_backend(ui_app, monkeypatch, scenario, origin, duration, weather, flight):
    calls = []
    original = interface.recommend

    def record_request(request, **kwargs):
        calls.append(asdict(request))
        return original(request, **kwargs)

    monkeypatch.setattr(interface, "recommend", record_request)
    # A quick scenario must reset a prior strict filter, not only change its label.
    ui_app.checkbox(key="strict_outlets").check().run()
    ui_app.button(key=f"scenario_{scenario}").click().run()
    assert not ui_app.exception
    assert len(calls) == 1
    assert calls[0]["location_preset"] == ui_app.session_state["origin"] == origin
    assert calls[0]["duration_minutes"] == ui_app.session_state["duration"] == duration
    assert calls[0]["weather_mode"] == ui_app.session_state["weather_mode"] == weather
    assert calls[0]["flight_constraint"] == ui_app.session_state["flight_constraint"] == flight
    assert "power_outlets" not in calls[0]["interests"]
    response = ui_app.session_state["qalago_result"][1]
    cards = interface.displayed_options(response)
    assert len(cards) <= 3
    assert all(card.source == "OpenStreetMap" for card in cards)
    assert all(card.total_minutes_estimated <= duration for card in cards)
    if flight:
        assert not cards and "аэропорт" in response.general_message


def test_advanced_settings_are_collapsed_and_simulation_label_is_visible(ui_app):
    assert not ui_app.exception
    settings = [item for item in ui_app.get("expander") if item.label == "Погода, время и дополнительные условия"]
    assert len(settings) == 1 and not settings[0].proto.expanded
    assert any("СИМУЛЯЦИЯ ПОГОДЫ" in item.value and "РЕАЛЬНЫЕ ЧАСЫ" in item.value for item in ui_app.caption)
    transparency = [item for item in ui_app.sidebar.get("expander") if item.label == "Прозрачность данных"]
    assert len(transparency) == 1 and not transparency[0].proto.expanded
    assert any("С описанием" in item.value for item in transparency[0].markdown)


def test_control_change_hides_both_direct_and_alternative_cards(ui_app):
    ui_app.button(key="generate").click().run()
    assert ui_app.subheader
    ui_app.radio(key="duration").set_value(120).run()
    assert not ui_app.exception
    assert not ui_app.subheader
    assert any("Условия изменились" in item.value for item in ui_app.info)


def test_card_groups_map_and_2gis_remain_grounded(ui_app):
    ui_app.button(key="scenario_wind").click().run()
    response = ui_app.session_state["qalago_result"][1]
    cards = interface.displayed_options(response)
    assert len(ui_app.subheader) == len(cards)
    assert any("Запасные варианты" in item.value for item in ui_app.markdown)
    assert any("Карта ·" in item.label for item in ui_app.get("expander"))
    assert not ui_app.get("link_button")  # 2GIS is a secondary text link.
    assert sum("[Найти в 2ГИС" in item.value for item in ui_app.markdown) == len(cards)
    # Every warning shared by several cards is printed once in common details.
    for warning in interface.shared_warnings(response):
        assert sum(item.value == warning for item in ui_app.caption) == 1


def test_curated_description_and_operator_schedule_keep_evidence_visible(ui_app):
    ui_app.button(key="scenario_wind").click().run()
    response = ui_app.session_state["qalago_result"][1]
    mega = next(card for card in interface.displayed_options(response) if card.poi_id == "osm:way:499328514")
    assert mega.description and "MEGA Silk Way" in mega.description
    assert any(item.value == mega.description for item in ui_app.caption)
    assert any("Источник краткого описания" in item.value and mega.description_source in item.value for item in ui_app.markdown)
    assert any("Источник расписания" in item.value and mega.opening_hours_source_url in item.value for item in ui_app.markdown)


def test_comparison_uses_same_weather_and_time_and_invalidates_on_change(ui_app):
    ui_app.button(key="scenario_wind").click().run()
    ui_app.button(key="compare").click().run()
    assert not ui_app.exception
    comparison = ui_app.session_state["qalago_comparison"][1]
    assert comparison.off.weather == comparison.on.weather
    assert comparison.off.local_datetime == comparison.on.local_datetime == comparison.evaluated_at
    assert comparison.off.answer_mode in {"template", "empty"}
    assert comparison.on.answer_mode in {"template", "empty"}
    assert len(ui_app.subheader) == sum(len(interface.displayed_options(value)) for value in (comparison.off, comparison.on))
    assert all(len(interface.displayed_options(value)) <= 3 for value in (comparison.off, comparison.on))
    ui_app.selectbox(key="origin").select("baiterek").run()
    assert not ui_app.subheader
    assert any("Условия изменились" in item.value for item in ui_app.info)


def test_request_fingerprint_tracks_constraints_without_exposing_coordinates():
    first = RecommendRequest(location_preset="custom", latitude=51.123456, longitude=71.123456)
    fingerprint = interface.request_fingerprint(first)
    second = RecommendRequest(**{**asdict(first), "return_to_start": True})
    assert fingerprint != interface.request_fingerprint(second)
    assert len(fingerprint) == 64 and "51.123456" not in fingerprint
