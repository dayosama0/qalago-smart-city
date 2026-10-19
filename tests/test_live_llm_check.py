"""The explicit verification command must never manufacture a live success."""
from types import SimpleNamespace
import os
import pytest

from scripts import verify_live_llm


def test_missing_credentials_does_not_attempt_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def must_not_run(*args, **kwargs):
        raise AssertionError("No credentials: no call")

    monkeypatch.setattr(verify_live_llm, "recommend", must_not_run)
    report, code = verify_live_llm.verify()
    assert code == 2 and report["status"] == "not_attempted"
    assert report["poi_ids"] == [] and report["answer_mode"] is None


def test_template_fallback_is_not_a_successful_live_check(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    monkeypatch.setattr(verify_live_llm, "recommend", lambda request: SimpleNamespace(
        answer_mode="template", recommendations=[SimpleNamespace(poi_id="synthetic:test")], alternatives=[]))
    report, code = verify_live_llm.verify()
    assert code == 1 and report["status"] == "not_verified"
    assert "SYNTHETIC-NONCREDENTIAL" not in str(report)


def test_llm_mode_without_description_context_is_not_new_verification_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    monkeypatch.setattr(verify_live_llm, "recommend", lambda request: SimpleNamespace(
        answer_mode="llm", recommendations=[SimpleNamespace(poi_id="synthetic:test")], alternatives=[]))
    report, code = verify_live_llm.verify()
    assert code == 1 and report["status"] == "not_verified"
    assert report["source_description_poi_ids"] == []


def test_verifier_selects_public_area_with_enriched_candidate_and_redacts_bad_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    monkeypatch.setenv("OPENAI_MODEL", "sk-SYNTHETIC-ACCIDENTAL-SECRET")
    seen = []
    def check_request(request):
        seen.append(request)
        return SimpleNamespace(answer_mode="template", recommendations=[], alternatives=[])
    monkeypatch.setattr(verify_live_llm, "recommend", check_request)
    report, _ = verify_live_llm.verify()
    assert seen[0].location_preset == "expo"
    assert seen[0].weather_mode == "clear" and seen[0].time_mode == "simulated"
    assert report["model"] == "invalid_or_redacted"
    assert "sk-SYNTHETIC-ACCIDENTAL-SECRET" not in str(report)


def test_verification_exception_report_never_contains_provider_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    def fail(request):
        raise RuntimeError("SYNTHETIC-NONCREDENTIAL PRIVATE PROMPT")
    monkeypatch.setattr(verify_live_llm, "recommend", fail)
    report, code = verify_live_llm.verify()
    assert code == 1 and report["status"] == "not_verified"
    assert "SYNTHETIC-NONCREDENTIAL" not in str(report) and "PRIVATE PROMPT" not in str(report)


@pytest.mark.parametrize("endpoint", [
    "https://user:SYNTHETIC-PASSWORD@proxy.example.org/v1?token=SYNTHETIC-QUERY-KEY",
    "https://api.openai.com/v1?token=SYNTHETIC-QUERY-KEY",
    "https://user:SYNTHETIC-PASSWORD@api.openai.com/v1",
    "https://api.openai.com/v1/extra",
    "https://api.openai.com/v1#fragment",
    "https://api.openai.com.evil.example.org/v1",
    "http://api.openai.com/v1",
    " https://api.openai.com/v1",
])
def test_non_official_endpoint_never_calls_or_leaks_configuration(monkeypatch, endpoint):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    monkeypatch.setenv("OPENAI_BASE_URL", endpoint)
    def must_not_run(request):
        raise AssertionError("Rejected endpoint must not trigger a provider call")
    monkeypatch.setattr(verify_live_llm, "recommend", must_not_run)
    report, code = verify_live_llm.verify()
    assert code == 2 and report["status"] == "not_attempted"
    assert report["reason"].startswith("non_official_endpoint")
    assert "official_endpoint" not in report
    assert endpoint not in str(report)
    assert "SYNTHETIC-PASSWORD" not in str(report) and "SYNTHETIC-QUERY-KEY" not in str(report)
    assert "SYNTHETIC-NONCREDENTIAL" not in str(report)


@pytest.mark.parametrize("endpoint", [None, "", "https://api.openai.com/v1", "https://api.openai.com/v1/"])
def test_default_or_canonical_official_endpoint_allows_verification(monkeypatch, endpoint):
    monkeypatch.setenv("OPENAI_API_KEY", "SYNTHETIC-NONCREDENTIAL")
    if endpoint is None:
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("OPENAI_BASE_URL", endpoint)
    calls = []
    def source_backed_result(request):
        assert os.environ["OPENAI_BASE_URL"] == "https://api.openai.com/v1"
        calls.append(request)
        return SimpleNamespace(answer_mode="llm", alternatives=[], recommendations=[SimpleNamespace(
            poi_id="synthetic:test", description="SYNTHETIC source-backed description.",
            description_source="https://example.org/synthetic-source")])
    monkeypatch.setattr(verify_live_llm, "recommend", source_backed_result)
    report, code = verify_live_llm.verify()
    assert code == 0 and report["status"] == "verified" and len(calls) == 1
    assert report["official_endpoint"] == "https://api.openai.com/v1"
    assert os.environ.get("OPENAI_BASE_URL") == endpoint
