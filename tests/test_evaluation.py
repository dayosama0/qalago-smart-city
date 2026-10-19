"""Meaningful evaluator regressions; hand-built cards here are SYNTHETIC only."""

import csv
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest

from config import PRESETS
from core.models import Recommendation, RecommendResponse, Weather
from scripts.evaluate_queries import load_cases, make_request, prohibit_network, run_evaluation, validate_response, write_outputs


def synthetic_case_and_response():
    case = {"id": "SYNTHETIC_EVALUATOR_UNIT_TEST", "topic": "cafe", "query": "Кофе",
            "interests": ["coffee"], "location_preset": "expo", "duration_minutes": 60,
            "weather_mode": "clear"}
    request = make_request(case, "2026-10-19T14:00:00+05:00")
    preset = PRESETS["expo"]
    record = {"id": "osm:node:1", "name": "SYNTHETIC evaluator cafe", "lat": preset["lat"], "lon": preset["lon"],
              "category": "cafe", "indoor_status": "likely_indoor", "source": "OpenStreetMap",
              "source_url": "https://www.openstreetmap.org/node/1", "description": None, "description_source": None,
              "visit_minutes": 20, "opening_hours": "Mo-Su 10:00-22:00", "power_outlets_status": "unknown"}
    card = Recommendation(poi_id=record["id"], name=record["name"], lat=record["lat"], lon=record["lon"],
                          category="cafe", distance_m=0, travel_minutes_estimated=0, visit_minutes_estimated=20,
                          reason="SYNTHETIC reason", action="SYNTHETIC proposed action", opening_note="Listed hours; availability unverified",
                          indoor_status="likely_indoor", source="OpenStreetMap", source_url=record["source_url"],
                          total_minutes_estimated=25, opening_status="listed_open")
    response = RecommendResponse(recommendations=[card], answer_mode="template", time_is_simulated=True,
                                 weather=Weather(is_simulated=True, source="scenario:clear"))
    return case, request, response, {record["id"]: record}


def test_fifteen_authored_cases_cover_requested_topics_and_fixed_night():
    body, cases = load_cases()
    assert "SYNTHETIC" in body["prompt_provenance"]
    assert len(cases) == len({case["id"] for case in cases}) == 15
    assert {"architecture", "nature", "quiet", "family", "bad_weather", "night", "airport", "cafe"}.issubset({case["topic"] for case in cases})
    night = next(case for case in cases if case["topic"] == "night")
    assert "T23:00:00+05:00" in night["local_datetime"]
    assert all(case["weather_mode"] != "live" for case in cases)


def test_valid_synthetic_card_passes_independent_arithmetic():
    assert validate_response(*synthetic_case_and_response())["passed"]


@pytest.mark.parametrize("field,value,expected", [
    ("poi_id", "osm:node:999", "poi_outside_snapshot"),
    ("name", "SYNTHETIC invented name", "source_fields"),
    ("source_url", "https://example.invalid/wrong-object", "source_link"),
    ("total_minutes_estimated", 90, "time_budget"),
    ("distance_m", 1000, "time_budget"),
])
def test_checker_detects_grounding_or_arithmetic_corruption(field, value, expected):
    case, request, response, records = synthetic_case_and_response()
    response.recommendations[0] = replace(response.recommendations[0], **{field: value})
    checks = validate_response(case, request, response, records)
    assert not checks["passed"]
    assert any(error.startswith(expected) for error in checks["errors"])


def test_checker_rejects_unknown_required_features_and_closed_visit():
    case, request, response, records = synthetic_case_and_response()
    case["required_features"] = ["power_outlets_status"]
    request.simulated_datetime = "2026-10-19T23:00:00+05:00"
    checks = validate_response(case, request, response, records)
    assert any(error.startswith("strict_features") for error in checks["errors"])
    assert any(error.startswith("schedule") for error in checks["errors"])


def test_checker_detects_direct_match_hidden_as_alternative():
    case, request, response, records = synthetic_case_and_response()
    response.alternatives, response.recommendations = response.recommendations, []
    assert any(error.startswith("direct_category_label") for error in validate_response(case, request, response, records)["errors"])


def test_network_guard_blocks_socket_before_connecting():
    with prohibit_network(), socket.socket() as connection:
        with pytest.raises(RuntimeError, match="forbids network"):
            connection.connect(("127.0.0.1", 9))


def test_actual_offline_evaluation_exports_no_secrets_or_fabricated_ratings(tmp_path, monkeypatch):
    secret_canary = "SYNTHETIC_TEST_SECRET_DO_NOT_EXPORT"
    monkeypatch.setenv("OPENAI_API_KEY", secret_canary)

    def unexpected_call(*args, **kwargs):
        raise AssertionError("Offline evaluation must not call providers")

    monkeypatch.setattr("core.recommend.generate_explanations", unexpected_call)
    monkeypatch.setattr("requests.sessions.Session.request", unexpected_call)
    report = run_evaluation()
    assert report["metrics"]["cases_passing_automated_checks"] == 15
    assert report["metrics"]["database_unchanged"]
    assert report["metrics"]["human_relevance"] == "not_measured"
    assert report["metrics"]["unsupported_free_text_claims"] == "not_human_reviewed"
    write_outputs(report, tmp_path)
    assert secret_canary not in (tmp_path / "automated_results.json").read_text(encoding="utf-8")
    assert report["metrics"]["returned_cards"] == sum(len(result["checks"]["cards"]) for result in report["results"])
    for label in ("rater_a", "rater_b"):
        with (tmp_path / f"{label}_blank.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 15
        assert all(all(not value for field, value in row.items() if field not in {"case_id", "rater_role"}) for row in rows)
