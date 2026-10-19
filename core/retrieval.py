"""Read-only, structured retrieval from the genuine local POI snapshot."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sqlite3
from datetime import datetime

from config import DB_PATH
from core.geo import haversine_m, validate_coordinates, walking_minutes
from core.opening_hours import evaluate_opening_hours


class DatabaseUnavailable(RuntimeError):
    pass


@dataclass
class Candidate:
    id: str
    name: str
    lat: float
    lon: float
    category: str
    opening_hours: str | None = None
    indoor_status: str = "unknown"
    power_outlets_status: str = "unknown"
    wifi_status: str = "unknown"
    visit_minutes: int = 20
    source: str = "OpenStreetMap"
    source_url: str = ""
    fetched_at: str = ""
    tags: dict = field(default_factory=dict)
    distance_m: float = 0
    travel_minutes: float = 0
    total_minutes: float = 0
    opening_status: str = "unknown"
    description: str | None = None
    description_source: str | None = None
    opening_hours_source_url: str | None = None
    opening_hours_checked_at: str | None = None


KEYWORDS = {
    "architecture": ("architecture", "architect", "архитект", "сәулет", "байтерек"),
    "unusual": ("unusual", "необыч", "ерекше"),
    "museum": ("museum", "музе", "мұражай", "выстав", "gallery", "галере"),
    "coffee": ("coffee", "cafe", "cafes", "кафе", "кофе", "кофей", "кафехана"),
    "quiet": ("quiet", "calm", "тих", "спокой", "тыныш"),
    "children": ("children", "child", "kids", "ребен", "ребён", "дет", "бала"),
    "nature": ("nature", "park", "garden", "парк", "природ", "сад", "табиғат"),
    "night": ("night", "ноч", "вечер", "түн"),
    "power_outlets": ("power_outlets", "power outlet", "socket", "розет", "электр розетка"),
    "wifi": ("wifi", "wi-fi", "вайфай", "вай-фай"),
    "accessibility": ("accessibility", "wheelchair", "accessible", "barrier-free", "безбарьер", "инвалид", "коляс", "мүгедек"),
}

INTENT_CATEGORIES = {
    "architecture": {"attraction", "viewpoint", "museum", "arts_centre", "gallery"},
    "museum": {"museum", "gallery", "arts_centre"},
    "coffee": {"cafe", "restaurant"},
    "quiet": {"library", "garden", "park", "cafe"},
    "children": {"playground", "park", "museum", "garden"},
    "nature": {"park", "garden", "viewpoint"},
    "night": {"attraction", "viewpoint", "cafe", "restaurant"},
    "unusual": {"attraction", "museum", "gallery", "arts_centre", "viewpoint"},
}


def parse_intents(query: str, interests: list[str]) -> set[str]:
    text = " ".join([query, *interests]).casefold()
    return {intent for intent, words in KEYWORDS.items() if any(word in text for word in words)}


def is_direct_match(candidate: Candidate, intents: set[str]) -> bool:
    category_intents = [intent for intent in intents if intent in INTENT_CATEGORIES]
    return not category_intents or any(candidate.category in INTENT_CATEGORIES[intent] for intent in category_intents)


def has_flight_deadline(request) -> bool:
    text = request.query.casefold()
    return request.flight_constraint or any(term in text for term in (
        "рейс", "вылет", "самолет", "самолёт", "takeoff", "take off", "flight", "boarding", "ұшу", "ұшақ"
    ))


def _json_object(value: str | None) -> dict:
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def get_candidates(origin: tuple[float, float], duration_minutes: int, return_to_start: bool = False,
                   db_path: str | Path | None = None, intents: set[str] | None = None,
                   reserve_minutes: int = 5, *, evaluation_time: datetime | None = None) -> list[Candidate]:
    """Every returned option fits travel + visit + reserve, independently.

    The SQL bounding box is an inexpensive prefilter; Haversine is authoritative.
    Unknown features are excluded only when explicitly required.
    """
    path = Path(db_path) if db_path is not None else DB_PATH
    if not path.is_file():
        raise DatabaseUnavailable("POI database missing. Run: python -m ingestion.build_database")
    lat, lon = validate_coordinates(*origin)
    trip_factor = 2 if return_to_start else 1
    radius_m = min(5000.0, max(0.0, (duration_minutes - reserve_minutes) / trip_factor / 60 * 4.5 / 1.3 * 1000))
    delta_lat = radius_m / 110_574
    delta_lon = radius_m / (111_320 * max(0.01, abs(math.cos(math.radians(lat)))))
    try:
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM pois WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND trim(name) <> ''",
                (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
            ).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseUnavailable("POI database cannot be read. Rebuild with python -m ingestion.build_database") from exc
    candidates = []
    intents = intents or set()
    for row in rows:
        record = dict(row)
        try:
            point = validate_coordinates(record["lat"], record["lon"])
            visit = int(record.get("visit_minutes", 20))
            if visit <= 0 or visit > 480 or not isinstance(record["name"], str) or not record["name"].strip():
                continue
            tags = _json_object(record.get("tags_json"))
            field_provenance = _json_object(record.get("verified_fields_json"))
            hours_provenance = field_provenance.get("opening_hours", {})
            if not isinstance(hours_provenance, dict):
                hours_provenance = {}
            if str(tags.get("access", "")).casefold() in {"private", "no"}:
                continue
            # Exact unconditional OSM values are known closure evidence. Do not
            # interpret any compound/conditional opening_hours expression.
            if str(record.get("opening_hours") or "").strip().casefold() in {"closed", "off"}:
                continue
            lifecycle_prefixes = ("disused", "abandoned", "demolished", "removed", "construction")
            if any(str(tags.get(key, "")).strip().casefold() == "yes" for key in lifecycle_prefixes):
                continue
            if any(
                str(tags.get(f"{prefix}:{category_key}", "")).strip().casefold() not in {"", "no"}
                for prefix in lifecycle_prefixes
                for category_key in ("amenity", "tourism", "leisure", "shop", "historic")
            ):
                continue
            if "power_outlets" in intents and record.get("power_outlets_status") != "confirmed":
                continue
            if "wifi" in intents and record.get("wifi_status") != "confirmed":
                continue
            if "accessibility" in intents and str(tags.get("wheelchair", "")).strip().casefold() != "yes":
                continue
            distance = haversine_m(lat, lon, *point)
            travel = walking_minutes(distance)
            total = travel * trip_factor + visit + reserve_minutes
            if distance > radius_m or total > duration_minutes + 1e-9:
                continue
            opening_status = "unknown"
            if evaluation_time is not None:
                opening = evaluate_opening_hours(record.get("opening_hours"), evaluation_time, travel, visit)
                if opening.status == "listed_closed":
                    continue
                opening_status = opening.status
            indoor = record.get("indoor_status", "unknown")
            if indoor not in {"confirmed_indoor", "likely_indoor", "outdoor", "unknown"}:
                indoor = "unknown"
            candidates.append(Candidate(
                id=record["id"], name=record["name"].strip(), lat=point[0], lon=point[1],
                category=record["category"], opening_hours=record.get("opening_hours"),
                indoor_status=indoor, power_outlets_status=record.get("power_outlets_status", "unknown"),
                wifi_status=record.get("wifi_status", "unknown"), visit_minutes=visit,
                source=record.get("source") or "OpenStreetMap", source_url=record.get("source_url") or "",
                fetched_at=record.get("fetched_at") or "", tags=tags,
                distance_m=distance, travel_minutes=travel, total_minutes=total,
                opening_status=opening_status,
                description=record.get("description"), description_source=record.get("description_source"),
                opening_hours_source_url=hours_provenance.get("evidence_url") or record.get("source_url") or None,
                opening_hours_checked_at=hours_provenance.get("checked_at") or record.get("fetched_at") or None,
            ))
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
    return candidates
