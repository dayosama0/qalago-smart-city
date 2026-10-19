"""Diagnostic metadata must explain fallbacks without leaking provider data."""
from concurrent.futures import ThreadPoolExecutor
import json
import sys
from threading import Barrier
from types import SimpleNamespace

import httpx2
import pytest
from openai import AuthenticationError, NotFoundError, RateLimitError

from core.llm import generate_explanations, get_last_llm_diagnostic, reset_llm_diagnostic
from core.models import RecommendRequest, Weather
from core.retrieval import Candidate
from scripts import verify_live_llm

PRIVATE = "SYNTHETIC-PRIVATE-KEY-PROMPT-BODY"


def poi():
    return Candidate(id="synthetic:museum", name="SYNTHETIC museum", lat=51.1, lon=71.4, category="museum")


def install_provider(monkeypatch, handle):
    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(parse=self.parse))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def parse(self, **kwargs):
            return handle(json.loads(kwargs["messages"][1]["content"]))
    monkeypatch.setenv("OPENAI_API_KEY", PRIVATE)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=Client))


def valid_completion(payload):
    records = [{"poi_id": item["poi_id"], "reason": item["allowed_explanations"]["reasons"][0],
                "action": item["allowed_explanations"]["actions"][0], "warnings": []}
               for item in payload["candidates"]]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        refusal=None, parsed=SimpleNamespace(model_dump=lambda: {"recommendations": records})))])


def provider_error(error_type, status, code):
    request = httpx2.Request("POST", "https://example.invalid/private?token=" + PRIVATE)
    response = httpx2.Response(status, request=request, headers={"x-private": PRIVATE})
    return error_type(PRIVATE, response=response, body={"code": code, "message": PRIVATE, "private": PRIVATE})


@pytest.mark.parametrize("error_type,status,code,category", [
    (RateLimitError, 429, "insufficient_quota", "rate_limit_error"),
    (RateLimitError, 429, "credit_balance_exhausted", "rate_limit_error"),
    (AuthenticationError, 401, "invalid_api_key", "authentication_error"),
    (NotFoundError, 404, "model_not_found", "not_found"),
])
def test_known_sdk_errors_have_actionable_safe_metadata(monkeypatch, capsys, error_type, status, code, category):
    error = provider_error(error_type, status, code)
    def fail(payload):
        raise error
    install_provider(monkeypatch, fail)
    assert generate_explanations([poi()], RecommendRequest(), Weather()) is None
    diagnostic = get_last_llm_diagnostic()
    assert diagnostic == {"status": "not_verified", "stage": "provider", "category": category,
                          "http_status": status, "provider_error_code": code}
    assert PRIVATE not in json.dumps(diagnostic)
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


def test_unknown_error_code_and_private_message_are_withheld(monkeypatch):
    error = provider_error(RateLimitError, 429, PRIVATE)
    def fail(payload):
        raise error
    install_provider(monkeypatch, fail)
    generate_explanations([poi()], RecommendRequest(), Weather())
    assert get_last_llm_diagnostic()["provider_error_code"] is None
    assert PRIVATE not in json.dumps(get_last_llm_diagnostic())


@pytest.mark.parametrize("bad_status", ["401 PRIVATE", True, 999, 401.0])
def test_http_status_is_numeric_and_bounded(monkeypatch, bad_status):
    class CustomError(Exception):
        status_code = bad_status
        code = PRIVATE
    def fail(payload):
        raise CustomError(PRIVATE)
    install_provider(monkeypatch, fail)
    generate_explanations([poi()], RecommendRequest(), Weather())
    diagnostic = get_last_llm_diagnostic()
    assert diagnostic["category"] == "unexpected_error" and diagnostic["http_status"] is None
    assert PRIVATE not in json.dumps(diagnostic)


@pytest.mark.parametrize("response_kind,category,stage", [
    ("refusal", "refusal", "response"),
    ("no_parsed", "no_parsed_output", "response"),
    ("invalid_prose", "post_validation_failed", "post_validation"),
    ("valid", "validated", "complete"),
])
def test_response_outcomes_distinguished_without_recording_text(monkeypatch, response_kind, category, stage):
    def handle(payload):
        completion = valid_completion(payload)
        message = completion.choices[0].message
        if response_kind == "refusal":
            message.refusal = PRIVATE
        elif response_kind == "no_parsed":
            message.parsed = None
        elif response_kind == "invalid_prose":
            message.parsed = SimpleNamespace(model_dump=lambda: {"recommendations": [
                {"poi_id": "synthetic:museum", "reason": PRIVATE, "action": "invented", "warnings": []}]})
        return completion
    install_provider(monkeypatch, handle)
    result = generate_explanations([poi()], RecommendRequest(), Weather())
    diagnostic = get_last_llm_diagnostic()
    assert (result is not None) == (response_kind == "valid")
    assert diagnostic["category"] == category and diagnostic["stage"] == stage
    assert diagnostic["status"] == ("verified" if response_kind == "valid" else "not_verified")
    assert PRIVATE not in json.dumps(diagnostic)


def test_sequential_attempts_clear_codes_and_missing_key_state(monkeypatch):
    error = provider_error(RateLimitError, 429, "insufficient_quota")
    def handle(payload):
        if payload["query"] == "fail":
            raise error
        return valid_completion(payload)
    install_provider(monkeypatch, handle)
    generate_explanations([poi()], RecommendRequest(query="fail"), Weather())
    assert get_last_llm_diagnostic()["provider_error_code"] == "insufficient_quota"
    generate_explanations([poi()], RecommendRequest(query="ok"), Weather())
    assert get_last_llm_diagnostic()["status"] == "verified"
    assert get_last_llm_diagnostic()["http_status"] is None
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert generate_explanations([poi()], RecommendRequest(), Weather()) is None
    assert get_last_llm_diagnostic() == {"status": "not_attempted", "stage": "preflight", "category": "missing_key",
                                         "http_status": None, "provider_error_code": None}


def test_concurrent_calls_have_isolated_diagnostics(monkeypatch):
    gate = Barrier(2)
    error = provider_error(AuthenticationError, 401, "invalid_api_key")
    def handle(payload):
        gate.wait(timeout=5)
        if payload["query"] == "fail":
            raise error
        return valid_completion(payload)
    install_provider(monkeypatch, handle)
    reset_llm_diagnostic()
    main_before = get_last_llm_diagnostic()
    def attempt(query):
        result = generate_explanations([poi()], RecommendRequest(query=query), Weather())
        return result, get_last_llm_diagnostic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        failed, passed = list(pool.map(attempt, ["fail", "ok"]))
    assert failed[0] is None and failed[1]["provider_error_code"] == "invalid_api_key"
    assert passed[0] is not None and passed[1]["status"] == "verified"
    assert passed[1]["provider_error_code"] is None
    assert get_last_llm_diagnostic() == main_before


def test_verifier_clears_stale_success_when_provider_not_called(monkeypatch):
    install_provider(monkeypatch, valid_completion)
    generate_explanations([poi()], RecommendRequest(), Weather())
    assert get_last_llm_diagnostic()["status"] == "verified"
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(verify_live_llm, "recommend", lambda request: SimpleNamespace(
        answer_mode="empty", recommendations=[], alternatives=[]))
    report, code = verify_live_llm.verify()
    assert code == 1 and report["status"] == "not_verified"
    assert report["llm_diagnostic"]["category"] == "not_called"
    assert report["llm_diagnostic"]["status"] == "not_attempted"


def test_verifier_reports_safe_provider_failure_with_fallback(monkeypatch):
    error = provider_error(RateLimitError, 429, "insufficient_quota")
    def fail(payload):
        raise error
    install_provider(monkeypatch, fail)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    report, code = verify_live_llm.verify()
    assert code == 1 and report["answer_mode"] == "template" and report["status"] == "not_verified"
    assert report["llm_diagnostic"]["http_status"] == 429
    assert report["llm_diagnostic"]["provider_error_code"] == "insufficient_quota"
    assert PRIVATE not in json.dumps(report)
