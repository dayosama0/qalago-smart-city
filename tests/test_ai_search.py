from dataclasses import replace
from types import SimpleNamespace
import pytest
from core.ai_search import Plan, Selection, Choice, AIUnavailable, filter_requirements, select_places
from core.models import RecommendRequest, Weather
from core.retrieval import Candidate
from core.recommend import recommend
from ingestion.deduplicate import deduplicate_records


def request(**kwargs):
    return RecommendRequest(**{**dict(location_preset="custom", latitude=51.1, longitude=71.4,
        time_mode="simulated", simulated_datetime="2026-01-05T12:00:00", weather_mode="clear"), **kwargs})


def test_no_silent_fallback(synthetic_db, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    result = recommend(request(), synthetic_db)
    assert result.answer_mode == "ai_error"
    assert not result.recommendations
    fallback = recommend(request(allow_fallback=True), synthetic_db)
    assert fallback.answer_mode == "template"
    assert fallback.general_message


def test_coffee_shop_and_budget_are_hard_filters():
    base = Candidate("coffee", "Coffee", 51.1, 71.4, "cafe", tags={"cuisine": "coffee_shop", "average_check:kzt": "2500"})
    candidates = [base, replace(base, id="restaurant", category="restaurant"),
        replace(base, id="generic", tags={}), replace(base, id="expensive", tags={"cuisine": "coffee_shop", "average_check:kzt": "4000"}),
        replace(base, id="unknown", tags={"cuisine": "coffee_shop"})]
    plan = Plan(categories=["cafe"], coffee_shop_only=True, max_average_check_kzt=3000, duration_minutes=None)
    assert [c.id for c in filter_requirements(candidates, plan)] == ["coffee"]


def test_ai_selects_only_supplied_places_and_keeps_its_explanations(synthetic_db, monkeypatch):
    import core.recommend as backend
    monkeypatch.setattr(backend, "plan_query", lambda r: Plan(categories=["cafe"], coffee_shop_only=False, max_average_check_kzt=None, duration_minutes=30))
    def choose(candidates, req, weather):
        assert req.duration_minutes == 30
        assert all(c.category == "cafe" and c.total_minutes <= 30 for c in candidates)
        return Selection(recommendations=[Choice(description="A place for a short break.", poi_id=c.id, reason="A short break nearby.", action="Consider a coffee break.") for c in candidates[:3]], message="")
    monkeypatch.setattr(backend, "select_places", choose)
    result = recommend(request(), synthetic_db)
    assert result.answer_mode == "llm"
    assert 1 <= len(result.recommendations) <= 3
    assert all(c.reason == "A short break nearby." and c.total_minutes_estimated <= 30 for c in result.recommendations)
    assert all(c.description == "A place for a short break." and not c.description_source for c in result.recommendations)


@pytest.mark.parametrize("ids", [["invented"], ["known", "known"]])
def test_unknown_and_duplicate_ai_ids_rejected(monkeypatch, ids):
    import core.ai_search as ai
    monkeypatch.setattr(ai, "complete", lambda *args: Selection(recommendations=[Choice(description="A place for a short break.", poi_id=value, reason="Reason", action="Action") for value in ids], message=""))
    with pytest.raises(AIUnavailable):
        select_places([Candidate("known", "Known", 51.1, 71.4, "park")], request(), Weather())


@pytest.mark.parametrize("language", ["auto", "ru", "kk", "en"])
def test_group_and_language_reach_both_ai_steps(monkeypatch, language):
    import core.ai_search as ai
    calls = []
    def complete(schema, system, payload):
        calls.append(payload)
        if schema is Plan:
            return Plan(categories=[], coffee_shop_only=False, max_average_check_kzt=None, duration_minutes=None)
        assert payload["language"] == language
        return Selection(recommendations=[Choice(poi_id="park", description="Серуендеуге арналған саябақ.",
            reason="Бірге серуендеп, әңгімелесуге болады.", action="Серуендеу.")], message="")
    monkeypatch.setattr(ai, "complete", complete)
    req = request(group_size=3, member_preferences=["прогулка", "архитектура", "поговорить"], language=language)
    ai.plan_query(req)
    result = ai.select_places([Candidate("park", "Park", 51.1, 71.4, "park")], req, Weather())
    assert len(calls) == 2
    assert all(call["group_size"] == 3 and call["member_preferences"] == req.member_preferences for call in calls)
    assert result.recommendations[0].description == "Серуендеуге арналған саябақ."


def test_ai_never_receives_unknown_or_closed_hours_when_required(synthetic_db, monkeypatch):
    import core.recommend as backend
    import sqlite3
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours='Mo-Fr 09:00-18:00' WHERE id='synthetic:cafe-confirmed'")
        connection.execute("UPDATE pois SET opening_hours='Mo-Fr 09:00-10:00' WHERE id='synthetic:museum'")
    monkeypatch.setattr(backend, "plan_query", lambda req: Plan(categories=[], coffee_shop_only=False,
                       max_average_check_kzt=None, duration_minutes=None))
    def choose(candidates, req, weather):
        assert [candidate.id for candidate in candidates] == ["synthetic:cafe-confirmed"]
        return Selection(recommendations=[Choice(poi_id=candidates[0].id, description="Кафе.",
            reason="Подходит для перерыва.", action="Отдохнуть.")], message="")
    monkeypatch.setattr(backend, "select_places", choose)
    result = recommend(request(require_open_hours=True), synthetic_db)
    assert result.answer_mode == "llm"
    assert len(result.recommendations) == 1


def test_duplicate_language_aliases_and_distinct_branches():
    first = dict(id="osm:way:1", name="Mega Silk Way", category="mall", lat=51.1, lon=71.4,
        tags_json='{"name:ru": "Мега Силк Вей"}', verified_fields_json="{}")
    duplicate = {**first, "id": "osm:node:2", "name": "Мега Силк Вей", "lat": 51.1001, "tags_json": "{}"}
    branch = {**duplicate, "id": "osm:node:3", "lat": 51.2}
    records, removed = deduplicate_records([first, duplicate, branch])
    assert removed == 1 and len(records) == 2


@pytest.mark.parametrize("status,code,expected", [(401,None,"401"), (429,"insufficient_quota","Billing"), (429,None,"429"), (404,None,"GROQ_MODEL"), (400,None,"400"), (403,None,"403"), (503,None,"временно")])
def test_error_diagnostics_do_not_expose_provider_text(status, code, expected):
    cause = RuntimeError("sensitive-provider-secret")
    cause.status_code, cause.code = status, code
    error = AIUnavailable("failed")
    error.__cause__ = cause
    assert expected in error.user_message
    assert "sensitive-provider-secret" not in error.user_message


def test_connection_diagnostic():
    error = AIUnavailable("failed")
    error.__cause__ = type("APIConnectionError", (Exception,), {})("secret")
    assert "api.groq.com" in error.user_message
    assert "secret" not in error.user_message


@pytest.mark.parametrize("body", [{"error":{"code":"insufficient_quota"}}, {"type":"insufficient_quota", "code":None}])
def test_quota_detected_in_error_body(body):
    cause = RuntimeError("private")
    cause.status_code, cause.code, cause.body = 429, None, body
    error = AIUnavailable("failed")
    error.__cause__ = cause
    assert "закончились средства" in error.user_message


def test_unknown_429_does_not_claim_only_frequency_limit():
    cause = RuntimeError("private")
    cause.status_code = 429
    error = AIUnavailable("failed")
    error.__cause__ = cause
    assert "квоты" in error.user_message
    assert "Billing" in error.user_message


@pytest.mark.parametrize("payload,finish,valid", [
    ({"categories":["cafe"], "coffee_shop_only":True, "max_average_check_kzt":None, "duration_minutes":30}, "stop", True),
    ({"categories":["invented"], "coffee_shop_only":True, "max_average_check_kzt":None, "duration_minutes":30}, "stop", False),
    ({"categories":[]}, "stop", False),
    ({"categories":[], "coffee_shop_only":False, "max_average_check_kzt":None, "duration_minutes":None}, "length", False),
])
def test_groq_http_request_and_response_validation(monkeypatch, payload, finish, valid):
    import json
    import requests
    from core.ai_search import complete
    monkeypatch.setenv("GROQ_API_KEY", "gsk-offline-test-only")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    def post(url, **kwargs):
        assert url == "https://api.groq.com/openai/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer gsk-offline-test-only"
        assert kwargs["timeout"] == (5, 30)
        body = kwargs["json"]
        assert body["model"] == "openai/gpt-oss-20b"
        assert body["response_format"]["json_schema"]["strict"] is True
        assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"choices":[{"finish_reason":finish,
            "message":{"role":"assistant", "content":json.dumps(payload)}}]}).encode()
        return response
    monkeypatch.setattr(requests, "post", post)
    if valid:
        assert complete(Plan, "Extract requirements", {"query":"coffee"}).coffee_shop_only
    else:
        with pytest.raises(AIUnavailable):
            complete(Plan, "Extract requirements", {"query":"coffee"})


def test_openai_key_is_not_used_for_groq(monkeypatch):
    from core.ai_search import complete
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-private-key")
    with pytest.raises(AIUnavailable) as caught:
        complete(Plan, "system", {})
    assert "GROQ_API_KEY" in caught.value.user_message
    assert "unrelated-private-key" not in caught.value.user_message


def test_selection_length_limits_are_preserved_locally():
    from core.ai_search import provider_schema
    from pydantic import ValidationError
    schema = provider_schema(Selection)
    assert "maxItems" not in schema["properties"]["recommendations"]
    with pytest.raises(ValidationError):
        Selection(recommendations=[Choice(description="A place for a short break.", poi_id=str(i), reason="Reason", action="Action") for i in range(4)], message="")


@pytest.mark.parametrize("status,code,expected", [(401,"invalid_api_key","401"), (429,"rate_limit_exceeded","429"), (429,"insufficient_quota","Billing")])
def test_http_errors_report_groq_without_exposing_credentials(monkeypatch, status, code, expected):
    import json
    import requests
    from core.ai_search import complete
    monkeypatch.setenv("GROQ_API_KEY", "private-test-key")
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({"error":{"code":code, "message":"private-test-key"}}).encode()
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(AIUnavailable) as caught:
        complete(Plan, "system", {})
    assert expected in caught.value.user_message
    assert "Groq" in caught.value.user_message
    assert "private-test-key" not in caught.value.user_message
