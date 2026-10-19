"""Run one real retrieval → OpenAI → validation check, only with credentials.

Usage: python -m scripts.verify_live_llm
The report contains public POI IDs and validation status, never keys or prompts.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import tomllib

from dotenv import load_dotenv

from config import OPENAI_MODEL, ROOT, TIMEZONE
from core.models import RecommendRequest
from core.llm import source_description_context
from core.recommend import recommend

OFFICIAL_OPENAI_ENDPOINT = "https://api.openai.com/v1"


def verify() -> tuple[dict, int]:
    configured_model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    safe_model = (configured_model if re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", configured_model)
                  and not configured_model.startswith("sk-") else "invalid_or_redacted")
    report = {"checked_at": datetime.now(TIMEZONE).isoformat(),
              "model": safe_model,
              "status": "not_attempted", "answer_mode": None,
              "poi_ids": [], "weather_is_simulated": True,
              "clock_is_simulated": True, "source_description_poi_ids": [],
              "grounding_mode": "bounded_source_sentence_selection"}
    # The installed SDK honors OPENAI_BASE_URL. A successful response through a
    # custom service cannot establish a genuine request to the OpenAI endpoint.
    # Compare exact strings: never echo a rejected URL, which may contain keys.
    configured_endpoint = os.getenv("OPENAI_BASE_URL", "")
    if configured_endpoint not in {"", OFFICIAL_OPENAI_ENDPOINT, OFFICIAL_OPENAI_ENDPOINT + "/"}:
        report["reason"] = "non_official_endpoint; live OpenAI verification not attempted"
        return report, 2
    report["official_endpoint"] = OFFICIAL_OPENAI_ENDPOINT
    if not os.getenv("OPENAI_API_KEY", "").strip():
        report["reason"] = "credentials_missing; live LLM verification incomplete"
        return report, 2
    # A fixed public preset and non-personal request; no user location/query.
    noon = datetime.now(TIMEZONE).replace(hour=12, minute=0, second=0, microsecond=0)
    request = RecommendRequest(location_preset="expo", query="Короткий визит рядом с EXPO",
                               interests=[], duration_minutes=60,
                               weather_mode="clear", time_mode="simulated",
                               simulated_datetime=noon.isoformat())
    previous_endpoint = os.environ.get("OPENAI_BASE_URL")
    try:
        # Empty OPENAI_BASE_URL is not a default in every SDK version. Pin the
        # accepted invocation to the canonical endpoint, then restore the env.
        os.environ["OPENAI_BASE_URL"] = OFFICIAL_OPENAI_ENDPOINT
        response = recommend(request)
        report["answer_mode"] = response.answer_mode
        cards = [*response.recommendations, *response.alternatives]
        report["poi_ids"] = [p.poi_id for p in cards]
        report["source_description_poi_ids"] = [p.poi_id for p in cards if source_description_context(p)["description"]]
        if response.answer_mode == "llm" and report["poi_ids"] and report["source_description_poi_ids"]:
            report.update(status="verified", reason="retrieval, source-description context, structured output and bounded post-validation succeeded; no AI quality improvement measured")
            return report, 0
        report.update(status="not_verified", reason="no candidates, no sourced description context, or deterministic fallback; no successful live LLM result")
    except Exception:
        # Provider exceptions may include headers or request data; never print them.
        report.update(status="not_verified", reason="verification failed; inspect configuration without exposing secrets")
    finally:
        if previous_endpoint is None:
            os.environ.pop("OPENAI_BASE_URL", None)
        else:
            os.environ["OPENAI_BASE_URL"] = previous_endpoint
    return report, 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "live-llm-verification.json")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.is_file():
        values = tomllib.loads(secrets.read_text(encoding="utf-8"))
        for name in ("OPENAI_API_KEY", "OPENAI_MODEL"):
            if not os.getenv(name) and isinstance(values.get(name), str):
                os.environ[name] = values[name]
    report, code = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
