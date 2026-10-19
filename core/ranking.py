"""Explainable initial heuristics; climate filtering happens before generation."""
from core.models import Weather
from core.retrieval import Candidate, INTENT_CATEGORIES


def estimated_outdoor_minutes(candidate: Candidate, return_to_start: bool = False) -> float:
    travel = candidate.travel_minutes * (2 if return_to_start else 1)
    # Only supported indoor classifications remove the visit from exposure.
    visit = 0 if candidate.indoor_status in {"confirmed_indoor", "likely_indoor"} else candidate.visit_minutes
    return travel + visit


def rank_candidates(candidates: list[Candidate], intents: set[str], weather: Weather,
                    climate_shield_enabled: bool, duration_minutes: int = 60,
                    return_to_start: bool = False) -> list[Candidate]:
    scored = []
    category_intents = [intent for intent in intents if intent in INTENT_CATEGORIES]
    for candidate in candidates:
        indoor = candidate.indoor_status in {"confirmed_indoor", "likely_indoor"}
        outdoor = estimated_outdoor_minutes(candidate, return_to_start)
        if climate_shield_enabled:
            if weather.status == "severe" and (not indoor or outdoor > 10):
                continue
            if weather.status == "caution" and (outdoor > 25 or (not indoor and candidate.visit_minutes >= 20)):
                continue
            if weather.status == "unknown" and outdoor > 45:
                continue
        intent_score = (sum(candidate.category in INTENT_CATEGORIES[intent] for intent in category_intents)
                        / len(category_intents)) if category_intents else 0.5
        proximity = max(0, 1 - candidate.travel_minutes / max(1, duration_minutes))
        climate = 0.5
        if climate_shield_enabled and weather.status in {"caution", "severe", "unknown"}:
            climate = 1 if indoor else 0
        quality = (bool(candidate.opening_hours) + bool(candidate.source_url)
                   + (candidate.indoor_status != "unknown") + bool(candidate.fetched_at)) / 4
        score = 0.45 * intent_score + 0.30 * proximity + 0.15 * climate + 0.10 * quality
        scored.append((score, candidate))
    scored.sort(key=lambda item: (-item[0], item[1].distance_m, item[1].id))
    return [candidate for _, candidate in scored]
