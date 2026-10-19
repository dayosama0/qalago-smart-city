"""Run one real retrieval → OpenAI → validation check, only with credentials.

Usage: python -m scripts.verify_live_llm
The report contains public POI IDs and validation status, never keys or prompts.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import tomllib

from dotenv import load_dotenv

from config import OPENAI_MODEL, ROOT, TIMEZONE
from core.models import RecommendRequest
from core.recommend import recommend


def verify() -> tuple[dict, int]:
    report = {"checked_at": datetime.now(TIMEZONE).isoformat(),
              "model": os.getenv("OPENAI_MODEL", OPENAI_MODEL),
              "status": "not_attempted", "answer_mode": None,
              "poi_ids": [], "weather_is_simulated": True,
              "clock_is_simulated": True}
    if not os.getenv("OPENAI_API_KEY", "").strip():
        report["reason"] = "credentials_missing; live LLM verification incomplete"
        return report, 2
    # A fixed public preset and non-personal request; no user location/query.
    noon = datetime.now(TIMEZONE).replace(hour=12, minute=0, second=0, microsecond=0)
    request = RecommendRequest(location_preset="baiterek", query="Короткая остановка на кофе",
                               interests=["coffee"], duration_minutes=60,
                               weather_mode="clear", time_mode="simulated",
                               simulated_datetime=noon.isoformat())
    try:
        response = recommend(request)
        report["answer_mode"] = response.answer_mode
        report["poi_ids"] = [p.poi_id for p in [*response.recommendations, *response.alternatives]]
        if response.answer_mode == "llm" and report["poi_ids"]:
            report.update(status="verified", reason="retrieval, structured output and post-validation succeeded")
            return report, 0
        report.update(status="not_verified", reason="no candidates or deterministic fallback; no successful live LLM result")
    except Exception:
        # Provider exceptions may include headers or request data; never print them.
        report.update(status="not_verified", reason="verification failed; inspect configuration without exposing secrets")
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
