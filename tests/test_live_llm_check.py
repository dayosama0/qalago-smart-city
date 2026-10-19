"""The explicit verification command must never manufacture a live success."""
from types import SimpleNamespace

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
