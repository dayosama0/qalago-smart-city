"""Offline evaluation of 15 authored representative prompts against public OSM.

Run: python -m scripts.evaluate_queries
No model/provider calls or human relevance scores are part of this evaluation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import sqlite3
import statistics
import subprocess
from time import perf_counter
from unittest.mock import patch

from config import DB_PATH, PRESETS, ROOT, TIMEZONE
from core.models import RecommendRequest, RecommendResponse
from core.opening_hours import evaluate_opening_hours
from core.recommend import recommend
from core.retrieval import INTENT_CATEGORIES, parse_intents

CASES_PATH = ROOT / "evaluation" / "representative_queries.json"
DEFAULT_OUTPUT = ROOT / "evaluation" / "results"


def load_cases(path: Path = CASES_PATH) -> tuple[dict, list[dict]]:
    body = json.loads(path.read_text(encoding="utf-8"))
    cases = body["cases"]
    if len(cases) != 15 or len({case["id"] for case in cases}) != 15:
        raise ValueError("Evaluation requires exactly 15 uniquely identified representative cases")
    if "SYNTHETIC" not in body.get("prompt_provenance", ""):
        raise ValueError("Prompt provenance must explicitly identify synthetic authorship")
    for case in cases:
        if case["location_preset"] not in PRESETS or case.get("weather_mode") not in {"clear", "wind", "rain", "cold"}:
            raise ValueError("Evaluation only accepts public presets and deterministic weather scenarios")
        instant = datetime.fromisoformat(case.get("local_datetime", body["fixed_local_datetime"]))
        if instant.utcoffset() is None:
            raise ValueError("Evaluation times require an explicit offset")
    return body, cases


def make_request(case: dict, default_instant: str) -> RecommendRequest:
    return RecommendRequest(
        location_preset=case["location_preset"], query=case["query"],
        interests=case["interests"], duration_minutes=case["duration_minutes"],
        return_to_start=case.get("return_to_start", False),
        climate_shield_enabled=case.get("climate_shield_enabled", True),
        weather_mode=case["weather_mode"], time_mode="simulated",
        simulated_datetime=case.get("local_datetime", default_instant),
        flight_constraint=case.get("flight_constraint", False), language="ru",
    )


@contextmanager
def prohibit_network():
    """Fail closed if future code unexpectedly tries a network connection."""
    with patch("socket.socket.connect", side_effect=RuntimeError("Offline evaluation forbids network")), \
         patch("socket.socket.connect_ex", side_effect=RuntimeError("Offline evaluation forbids network")):
        yield


def read_records(path: Path) -> dict[str, dict]:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in connection.execute("SELECT * FROM pois")}


def distance_and_walk(origin: tuple[float, float], point: tuple[float, float]) -> tuple[float, float]:
    """Independent spherical-distance check using the documented 6371 km model."""
    lat1, lon1, lat2, lon2 = map(math.radians, [*origin, *point])
    chord = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    distance = 12_742_000 * math.asin(math.sqrt(max(0.0, min(1.0, chord))))
    return distance, distance * 1.3 / 4500 * 60


def validate_response(case: dict, request: RecommendRequest, response: RecommendResponse,
                      records: dict[str, dict]) -> dict:
    """Check source-backed fields and constraints; do not grade prose relevance."""
    cards = [*response.recommendations, *response.alternatives]
    errors: list[str] = []
    card_checks = []
    if len(cards) > 3 or len({card.poi_id for card in cards}) != len(cards):
        errors.append("result_count_or_duplicate_ids")
    if response.answer_mode not in {"template", "empty"}:
        errors.append("non_deterministic_answer_mode")
    if not response.weather.is_simulated or not response.time_is_simulated:
        errors.append("simulation_not_explicit")
    if case.get("expected_empty") and cards:
        errors.append("expected_safe_empty_result_not_observed")
    if not cards and not (response.general_message or "").strip():
        errors.append("empty_result_without_explanation")
    instant = datetime.fromisoformat(request.simulated_datetime).astimezone(TIMEZONE)
    preset = PRESETS[request.location_preset]
    origin = (preset["lat"], preset["lon"])
    intents = parse_intents(request.query, request.interests)
    category_intents = [intent for intent in intents if intent in INTENT_CATEGORIES]
    direct_ids = {card.poi_id for card in response.recommendations}
    for card in cards:
        check = {"poi_id": card.poi_id, "source_fields": False, "time_budget": False,
                 "strict_features": False, "schedule": False, "schedule_status": "unknown",
                 "direct_category_label": False, "source_link": False}
        record = records.get(card.poi_id)
        if record is None:
            errors.append("poi_outside_snapshot")
            card_checks.append(check)
            continue
        check["source_fields"] = all(getattr(card, field) == record[field] for field in (
            "name", "lat", "lon", "category", "indoor_status", "source", "source_url", "description", "description_source"))
        try:
            osm_kind, osm_number = card.poi_id.removeprefix("osm:").split(":")
            check["source_link"] = (osm_kind in {"node", "way", "relation"} and int(osm_number) > 0
                                     and card.source_url == f"https://www.openstreetmap.org/{osm_kind}/{osm_number}")
        except (ValueError, AttributeError):
            check["source_link"] = False
        distance, walk = distance_and_walk(origin, (record["lat"], record["lon"]))
        total = walk * (2 if request.return_to_start else 1) + record["visit_minutes"] + 5
        check["time_budget"] = (
            abs(card.distance_m - distance) <= 0.11 and abs(card.travel_minutes_estimated - walk) <= 0.11
            and card.visit_minutes_estimated == record["visit_minutes"]
            and abs(card.total_minutes_estimated - total) <= 0.11
            and total <= request.duration_minutes + 1e-8)
        check["strict_features"] = all(record.get(field) == "confirmed" for field in case.get("required_features", []))
        opening = evaluate_opening_hours(record.get("opening_hours"), instant, walk, record["visit_minutes"])
        check["schedule_status"] = opening.status
        check["schedule"] = opening.status != "listed_closed" and card.opening_status == opening.status
        matches = not category_intents or any(record["category"] in INTENT_CATEGORIES[intent] for intent in category_intents)
        check["direct_category_label"] = matches == (card.poi_id in direct_ids)
        if not card.reason.strip() or not card.action.strip() or not card.opening_note.strip():
            errors.append("missing_reason_action_or_uncertainty")
        for field in ("source_fields", "time_budget", "strict_features", "schedule", "direct_category_label", "source_link"):
            if not check[field]:
                errors.append(f"{field}:{card.poi_id}")
        card_checks.append(check)
    return {"passed": not errors, "errors": errors, "cards": card_checks}


def _code_fingerprint() -> str:
    digest = sha256()
    files = [ROOT / "config.py", Path(__file__), CASES_PATH, *sorted((ROOT / "core").glob("*.py"))]
    for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        # Git may normalize source text line endings on clean checkout.
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _git_state() -> dict:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
        return {"head_commit": head, "working_tree_dirty": dirty,
                "note": "HEAD identifies the base when dirty; code_sha256 identifies evaluated backend/config/script text."}
    except (OSError, subprocess.CalledProcessError):
        return {"head_commit": None, "working_tree_dirty": None, "note": "Git metadata unavailable."}


def mechanical_caveats(case: dict, response: RecommendResponse) -> list[str]:
    """Observable limitations for raters, not invented opinions about usefulness."""
    cards = [*response.recommendations, *response.alternatives]
    notes = []
    intents = parse_intents(case["query"], case["interests"])
    if "quiet" in intents:
        notes.append("Quietness is inferred from broad categories; noise was not measured or confirmed.")
    if "children" in intents:
        notes.append("A child-oriented category match does not verify age suitability, facilities or access.")
    if "unusual" in intents:
        notes.append("Unusual is a broad cultural taxonomy, not evidence of a distinctive experience.")
    if sum(intent in INTENT_CATEGORIES for intent in intents) > 1:
        notes.append("Multiple category intents use OR matching; a card can match one requested category without matching all.")
    if any(card.opening_status == "unknown" for card in cards):
        notes.append("At least one returned option has unknown or unsupported hours; its availability is unverified.")
    if any(card.indoor_status == "likely_indoor" for card in cards):
        notes.append("At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.")
    if not response.recommendations and response.alternatives:
        notes.append("No direct category match remains; only explicitly separate other-category alternatives are returned.")
    return notes


def run_evaluation(db_path: Path = DB_PATH, cases_path: Path = CASES_PATH) -> dict:
    body, cases = load_cases(cases_path)
    before_hash = sha256(db_path.read_bytes()).hexdigest()
    records = read_records(db_path)
    results = []
    with prohibit_network():
        for case in cases:
            request = make_request(case, body["fixed_local_datetime"])
            started = perf_counter()
            response = recommend(request, db_path=db_path, use_llm=False)
            elapsed_ms = (perf_counter() - started) * 1000
            checks = validate_response(case, request, response, records)
            results.append({"case_id": case["id"], "topic": case["topic"], "request": asdict(request),
                            "latency_ms": round(elapsed_ms, 3), "expected_empty": case.get("expected_empty", False),
                            "expected_empty_reason": case.get("expected_empty_reason"),
                            "comparison_group": case.get("comparison_group"),
                            "mechanical_caveats": mechanical_caveats(case, response),
                            "response": asdict(response), "checks": checks})
    unchanged = sha256(db_path.read_bytes()).hexdigest() == before_hash
    cards = [check for result in results for check in result["checks"]["cards"]]
    direct = sum(bool(result["response"]["recommendations"]) for result in results)
    latencies = [result["latency_ms"] for result in results]
    metrics = {
        "cases": len(results), "cases_passing_automated_checks": sum(result["checks"]["passed"] for result in results),
        "direct_category_match_cases": direct, "direct_category_match_coverage_proxy": round(direct / len(results), 4),
        "nonempty_cases": sum(bool(result["checks"]["cards"]) for result in results),
        "alternatives_only_cases": sum(not result["response"]["recommendations"] and bool(result["response"]["alternatives"]) for result in results),
        "empty_cases": sum(not result["checks"]["cards"] for result in results),
        "expected_empty_cases": sum(result["expected_empty"] for result in results),
        "expected_empty_cases_satisfied": sum(result["expected_empty"] and not result["checks"]["cards"] for result in results),
        "returned_cards": len(cards), "time_budget_compliant_cards": sum(card["time_budget"] for card in cards),
        "source_field_mismatch_cards": sum(not card["source_fields"] for card in cards),
        "canonical_osm_source_links": sum(card["source_link"] for card in cards),
        "strict_feature_violation_cards": sum(not card["strict_features"] for card in cards),
        "strict_feature_returned_cards": sum(len(result["checks"]["cards"]) for result, case in zip(results, cases) if case.get("required_features")),
        "listed_closed_cards": sum(card["schedule_status"] == "listed_closed" for card in cards),
        "unknown_schedule_cards": sum(card["schedule_status"] == "unknown" for card in cards),
        "latency_ms_min": min(latencies), "latency_ms_median": round(statistics.median(latencies), 3),
        "latency_ms_max": max(latencies), "database_unchanged": unchanged,
        "human_relevance": "not_measured", "unsupported_free_text_claims": "not_human_reviewed",
    }
    return {"schema_version": 1, "evaluated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prompt_provenance": body["prompt_provenance"], "dataset_sha256": before_hash,
            "code_sha256": _code_fingerprint(), "git": _git_state(),
            "environment": {"python": platform.python_version(), "os": platform.system()},
            "mode": "offline_templates_simulated_weather_and_clock", "warm_up_calls": 0,
            "latency_scope": "recommend() only; excludes validation, output and network; single-machine observations, not a benchmark",
            "source_link_validation": "Local canonical OSM URLs and snapshot identity only; HTTP availability not tested",
            "metrics": metrics, "results": results,
            "limitations": ["Authored representative prompts; no human participants or collected user data.",
                            "Direct category match is a taxonomy proxy, not human relevance, quietness or family suitability.",
                            "Source-field checks do not establish that all explanation prose is factual; independent human review remains blank.",
                            "Shared opening-hours parser is checked against returned visits; grammar correctness is covered by its separate regression suite.",
                            "Small four-zone OSM coverage; no new data or live availability verification.",
                            "Outdoor exposure uses assumed category-based indoor status and is not observed safety."]}


def write_outputs(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "automated_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    fields = ["case_id", "topic", "query", "direct_count", "alternative_count", "latency_ms", "automated_pass", "errors", "expected_empty", "mechanical_caveats"]
    with (output_dir / "case_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for result in report["results"]:
            writer.writerow({"case_id": result["case_id"], "topic": result["topic"], "query": result["request"]["query"],
                             "direct_count": len(result["response"]["recommendations"]),
                             "alternative_count": len(result["response"]["alternatives"]), "latency_ms": result["latency_ms"],
                             "automated_pass": result["checks"]["passed"], "errors": ";".join(result["checks"]["errors"]),
                             "expected_empty": result["expected_empty"], "mechanical_caveats": " ".join(result["mechanical_caveats"])})
    for label in ("rater_a", "rater_b"):
        fields = ["case_id", "rater_role", "intent_relevance_1_5", "reason_quality_1_5", "time_correct_yes_no_unknown",
                  "source_correct_yes_no_unknown", "unsupported_claim_count", "comments"]
        with (output_dir / f"{label}_blank.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for result in report["results"]:
                writer.writerow({"case_id": result["case_id"], "rater_role": label})
    metrics = report["metrics"]
    lines = ["# Automated representative-query evaluation", "", f"Executed: {report['evaluated_at_utc']}.", "",
             "**These 15 prompts are authored synthetic examples. No human participants or relevance ratings have been collected.**", "",
             f"Dataset SHA-256: `{report['dataset_sha256']}`. Backend/script fingerprint: `{report['code_sha256']}`.", "",
             f"Base HEAD: `{report['git']['head_commit']}`; working tree dirty at run: `{report['git']['working_tree_dirty']}`. A dirty run is not a claim that HEAD contains the evaluated changes.", "",
             f"Automated checks: **{metrics['cases_passing_automated_checks']}/{metrics['cases']} cases**. Direct-category-match proxy: **{metrics['direct_category_match_cases']}/{metrics['cases']}** ({metrics['direct_category_match_coverage_proxy']:.1%}); this is not a human relevance score.", "",
             f"Cards within the independently recomputed estimated budget: **{metrics['time_budget_compliant_cards']}/{metrics['returned_cards']}**. Source-field mismatches: **{metrics['source_field_mismatch_cards']}**. Strict-feature violations: **{metrics['strict_feature_violation_cards']}**. Listed-closed returned cards: **{metrics['listed_closed_cards']}**. Unknown schedules: **{metrics['unknown_schedule_cards']}**.", "",
             f"Recommendation-only latency min / median / max: **{metrics['latency_ms_min']} / {metrics['latency_ms_median']} / {metrics['latency_ms_max']} ms**; no warm-up, single run on {report['environment']['os']} / Python {report['environment']['python']}. This is not a performance benchmark.", "",
             "Source links were checked locally for canonical OSM format and matching snapshot objects; no HTTP reachability or current opening was verified.", "",
             "| Case | Direct | Other-category alternatives | ms | Automated assertions |", "| --- | ---: | ---: | ---: | --- |"]
    for result in report["results"]:
        lines.append(f"| {result['case_id']} | {len(result['response']['recommendations'])} | {len(result['response']['alternatives'])} | {result['latency_ms']} | {'PASS' if result['checks']['passed'] else 'FAIL'} |")
    lines.extend(["", "## Empty, alternative-only and failed cases", ""])
    for result in report["results"]:
        if not result["response"]["recommendations"] or not result["checks"]["passed"]:
            note = result["expected_empty_reason"] or result["response"]["general_message"] or "No direct category match; inspect alternatives."
            lines.append(f"- **{result['case_id']}**: {note} Automated errors: {', '.join(result['checks']['errors']) or 'none'}.")
    lines.extend(["", "## Mechanical caveats for human review", ""])
    for result in report["results"]:
        if result["mechanical_caveats"]:
            lines.append(f"- **{result['case_id']}**: {' '.join(result['mechanical_caveats'])}")
    paired = {result["request"]["climate_shield_enabled"]: result for result in report["results"] if result["comparison_group"] == "wind_nature_expo"}
    if len(paired) == 2:
        off, on = paired[False], paired[True]
        first = lambda result: next(iter([*result["response"]["recommendations"], *result["response"]["alternatives"]]), None)
        lines.extend(["", "## Recorded wind comparison", ""])
        for label, result in (("OFF", off), ("ON", on)):
            card = first(result)
            lines.append(f"- Shield {label}: {card['name'] if card else 'no valid option'}; first-option estimated outdoor minutes {result['response']['estimated_outdoor_minutes'] if card else 'not comparable'}; direct matches {len(result['response']['recommendations'])}.")
        lines.append("These are different independent options. Category-based likely-indoor status is uncertain; no measured safety improvement is claimed.")
    lines.extend(["", "## Human review is pending", "", "`rater_a_blank.csv` and `rater_b_blank.csv` contain empty rating cells. Use [the protocol](../../docs/EVALUATION_PROTOCOL.md); keep the two reviews independent before adjudication. The automated run did not count unsupported claims in free text.", ""])
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_evaluation(args.db)
    write_outputs(report, args.output_dir)
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    return 0 if report["metrics"]["cases_passing_automated_checks"] == 15 and report["metrics"]["database_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
