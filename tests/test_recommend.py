from dataclasses import asdict
import json

import pytest

from core.llm import validate_explanations
from core.models import RecommendRequest, RecommendResponse
from core.recommend import recommend


def request(**kwargs):
    defaults = dict(allow_fallback=True, location_preset="custom", latitude=51.1, longitude=71.4,
                    weather_mode="clear", time_mode="simulated", simulated_datetime="2026-01-05T12:00:00")
    return RecommendRequest(**{**defaults, **kwargs})


def test_grounded_response_schema_and_max_twenty(synthetic_db):
    result = recommend(request(), synthetic_db)
    assert isinstance(result, RecommendResponse)
    assert result.answer_mode == "template"
    assert 0 < len(result.recommendations) <= 20
    allowed = {"synthetic:park", "synthetic:cafe-unknown", "synthetic:cafe-confirmed", "synthetic:museum"}
    assert {card.poi_id for card in result.recommendations} <= allowed
    assert all(card.total_minutes_estimated <= 60 for card in result.recommendations)
    assert result.time_is_simulated
    assert result.local_datetime.endswith("+05:00")
    assert json.loads(json.dumps(asdict(result)))["recommendations"][0]["name"].startswith("SYNTHETIC")


def test_time_budget_includes_return_and_reserve(synthetic_db):
    result = recommend(request(duration_minutes=30, return_to_start=True), synthetic_db)
    assert result.recommendations
    for card in result.recommendations:
        assert card.total_minutes_estimated <= 200
        assert card.total_minutes_estimated == pytest.approx(card.travel_minutes_estimated * 2 + card.visit_minutes_estimated + 5, abs=0.2)
    assert recommend(request(duration_minutes=5), synthetic_db).recommendations == []


def test_unknown_hours_and_simulation_do_not_invent_availability(synthetic_db):
    daytime = recommend(request(query="кофе", interests=["power_outlets"]), synthetic_db)
    nighttime = recommend(request(query="кофе", interests=["power_outlets"], simulated_datetime="2026-01-05T23:00:00"), synthetic_db)
    assert daytime.recommendations[0].opening_note == nighttime.recommendations[0].opening_note
    assert "Доступность сейчас не проверена" in nighttime.recommendations[0].opening_note
    assert any("Позднее местное время" in note for note in nighttime.limitations)
    assert any("Позднее местное время" in note for note in nighttime.recommendations[0].warnings)
    assert not any("Позднее местное время" in note for note in daytime.recommendations[0].warnings)
    unknown = recommend(request(query="nature"), synthetic_db)
    assert "Часы работы неизвестны" in unknown.recommendations[0].opening_note


def test_confirmed_outlet_requirement_honest_and_empty_when_too_short(synthetic_db):
    result = recommend(request(query="кафе с розеткой"), synthetic_db)
    assert [card.poi_id for card in result.recommendations] == ["synthetic:cafe-confirmed"]
    empty = recommend(request(query="кафе с розеткой", duration_minutes=5), synthetic_db)
    assert empty.answer_mode == "empty"
    assert "Неизвестные свойства" in empty.general_message


def test_wind_shield_changes_candidates_and_estimated_exposure(synthetic_db):
    shield_off = recommend(request(query="park", weather_mode="wind", climate_shield_enabled=False), synthetic_db)
    shield_on = recommend(request(query="park", weather_mode="wind", climate_shield_enabled=True), synthetic_db)
    assert shield_off.recommendations[0].poi_id == "synthetic:park"
    assert all(card.indoor_status in {"confirmed_indoor", "likely_indoor"} for card in shield_on.recommendations)
    assert shield_on.estimated_outdoor_minutes < shield_off.estimated_outdoor_minutes
    assert all(any("Неблагоприятная" in warning for warning in card.warnings) for card in shield_off.recommendations)
    assert "Альтернатива" in shield_on.recommendations[0].reason
    assert any("альтернативный вариант" in warning for warning in shield_on.recommendations[0].warnings)


@pytest.mark.parametrize("explicit,query", [(True, "Есть два часа"), (False, "2 часа до вылета"), (False, "two hours before my flight")])
def test_airport_flight_never_suggests_city_trip(synthetic_db, explicit, query):
    result = recommend(request(location_preset="airport", duration_minutes=120, query=query, flight_constraint=explicit), synthetic_db)
    assert result.recommendations == []
    assert "покидать аэропорт" in result.general_message


def test_duration_alone_does_not_create_flight_deadline(synthetic_db):
    result = recommend(request(location_preset="airport", duration_minutes=120), synthetic_db)
    assert result.recommendations
    assert result.recommendations[0].poi_id == "synthetic:airport-nearby"


def test_missing_db_has_actionable_empty_state(tmp_path):
    result = recommend(request(), tmp_path / "missing.db")
    assert result.answer_mode == "empty"
    assert "python -m ingestion.build_database" in result.general_message


def test_no_key_never_contacts_llm(synthetic_db, monkeypatch):
    import requests
    def must_not_run(*args, **kwargs):
        pytest.fail("No HTTP request is allowed without a Groq key")
    monkeypatch.setattr(requests, "post", must_not_run)
    assert recommend(request(), synthetic_db).answer_mode == "template"


@pytest.mark.parametrize("failure", ["timeout", "malformed", "invalid_category", "refusal", "quota"])
def test_provider_failures_preserve_grounded_template(synthetic_db, monkeypatch, failure):
    import requests
    baseline = recommend(request(), synthetic_db, use_llm=False)
    def post(url, **kwargs):
        assert url == "https://api.groq.com/openai/v1/chat/completions"
        if failure == "timeout":
            raise requests.Timeout("offline test")
        response = requests.Response()
        response.status_code = 429 if failure == "quota" else 200
        if failure == "quota":
            body = {"error":{"code":"rate_limit_exceeded"}}
        elif failure == "malformed":
            body = {"arbitrary":"bad schema"}
        else:
            content = json.dumps({"categories":["invented"], "coffee_shop_only":False,
                "max_average_check_kzt":None, "duration_minutes":None})
            body = {"choices":[{"finish_reason":"stop", "message":{
                "content":content, "refusal":"refused" if failure == "refusal" else None}}]}
        response._content = json.dumps(body).encode()
        return response
    monkeypatch.setenv("GROQ_API_KEY", "test-only-not-a-real-secret")
    monkeypatch.setattr(requests, "post", post)
    result = recommend(request(), synthetic_db)
    assert result.answer_mode == "template"
    assert [asdict(c) for c in result.recommendations] == [asdict(c) for c in baseline.recommendations]
    assert result.general_message


def test_postvalidation_rejects_untrusted_facts_and_ids():
    safe = {"recommendations": [{"poi_id": "known", "reason": "A possible short visit.", "action": "Consider a stop.", "warnings": []}]}
    assert validate_explanations(safe, {"known"}) is not None
    assert validate_explanations(safe, {"other"}) is None
    for fact in ["Open now", "Бесплатный вход", "Тёплое помещение", "Guaranteed safe", "Цена 500 тенге", "концерт вечером"]:
        safe["recommendations"][0]["reason"] = fact
        assert validate_explanations(safe, {"known"}) is None


@pytest.mark.parametrize("kwargs", [{"duration_minutes": 0}, {"duration_minutes": True}, {"latitude": float("nan")}, {"time_mode": "simulated", "simulated_datetime": "bad"}])
def test_invalid_inputs_rejected(synthetic_db, kwargs):
    with pytest.raises(ValueError):
        recommend(request(**kwargs), synthetic_db)


@pytest.mark.parametrize("kwargs", [
    {"group_size": 0}, {"group_size": 6}, {"group_size": True},
    {"member_preferences": ["a", "b"]}, {"member_preferences": ["x" * 301]},
    {"member_preferences": "coffee"}, {"language": "unsupported"}, {"require_open_hours": "yes"},
])
def test_invalid_group_preferences_rejected(synthetic_db, kwargs):
    with pytest.raises(ValueError):
        recommend(request(**kwargs), synthetic_db, use_llm=False)


def test_open_hours_filter_also_applies_to_fallback(synthetic_db):
    import sqlite3
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours='Mo-Fr 09:00-18:00' WHERE id='synthetic:cafe-confirmed'")
    daytime = recommend(request(require_open_hours=True), synthetic_db, use_llm=False)
    assert [card.poi_id for card in daytime.recommendations] == ["synthetic:cafe-confirmed"]
    for time in ("2026-01-05T23:00:00", "2026-01-05T17:50:00"):
        result = recommend(request(require_open_hours=True, simulated_datetime=time), synthetic_db, use_llm=False)
        assert not result.recommendations
        assert "на всё время посещения" in result.general_message


def test_group_fallback_does_not_claim_personalized_compromise(synthetic_db):
    result = recommend(request(group_size=3, member_preferences=["кофе", "музей", "прогулка"]),
                       synthetic_db, use_llm=False)
    assert result.recommendations
    assert "не согласует пожелания" in result.general_message
