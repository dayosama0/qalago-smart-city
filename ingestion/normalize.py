"""Normalize source tags conservatively without inventing POI attributes."""

from __future__ import annotations

import json
import math
from typing import Any

DEFAULT_VISIT_MINUTES = {
    "cafe": 20, "restaurant": 30, "library": 25, "arts_centre": 25,
    "museum": 35, "attraction": 20, "viewpoint": 15, "gallery": 25,
    "park": 25, "garden": 20, "playground": 20, "mall": 30,
}
INDOOR_CATEGORIES = {"cafe", "restaurant", "library", "arts_centre", "museum", "gallery", "mall"}
OUTDOOR_CATEGORIES = {"park", "garden", "playground", "viewpoint"}


def category_from_tags(tags: dict[str, Any]) -> str | None:
    for key in ("amenity", "tourism", "leisure", "shop"):
        category = tags.get(key)
        if category in DEFAULT_VISIT_MINUTES:
            return str(category)
    if tags.get("historic") in {"monument", "memorial"}:
        return "attraction"
    return None


def retained_tags(tags: dict[str, Any]) -> dict[str, str]:
    """Retain OSM evidence, omitting public contact/person identifiers from exports.

    Original raw Overpass responses remain local (gitignored). The distributable
    normalized DB does not need telephone/email/contact/social media data.
    """
    omitted = {"phone", "fax", "email", "website", "url", "operator:phone", "operator:email",
               "contact", "image", "wikimedia_commons", "check_date:phone", "check_date:email"}
    return {
        str(key): str(value) for key, value in tags.items()
        if key not in omitted and not str(key).startswith(("contact:", "addr:flats", "person:"))
    }


def normalize_element(element: Any, fetched_at: str) -> dict[str, Any] | None:
    if not isinstance(element, dict):
        return None
    osm_type = element.get("type")
    osm_id = element.get("id")
    if osm_type not in {"node", "way", "relation"} or isinstance(osm_id, bool):
        return None
    if not isinstance(osm_id, int) or osm_id <= 0:
        return None
    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None
    name = next((str(tags[k]).strip() for k in ("name", "name:ru", "name:kk", "name:en")
                 if tags.get(k) and str(tags[k]).strip()), "")
    category = category_from_tags(tags)
    if not name or category is None:
        return None
    coordinates = element if osm_type == "node" else element.get("center", {})
    if not isinstance(coordinates, dict):
        return None
    try:
        if isinstance(coordinates.get("lat"), bool) or isinstance(coordinates.get("lon"), bool):
            return None
        latitude, longitude = float(coordinates["lat"]), float(coordinates["lon"])
    except (TypeError, ValueError, KeyError):
        return None
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    safe_tags = retained_tags(tags)
    indoor_tag = str(tags.get("indoor", "")).lower()
    if indoor_tag == "yes":
        indoor_status = "confirmed_indoor"
    elif indoor_tag == "no":
        indoor_status = "outdoor"
    elif category in INDOOR_CATEGORIES:
        indoor_status = "likely_indoor"
    elif category in OUTDOOR_CATEGORIES:
        indoor_status = "outdoor"
    else:
        indoor_status = "unknown"
    power = str(tags.get("socket", tags.get("power_supply", ""))).lower()
    power_status = "confirmed" if power in {"yes", "schuko", "type_c", "type_f"} else "no" if power == "no" else "unknown"
    internet = str(tags.get("internet_access", "")).lower()
    wifi_status = "confirmed" if internet == "wlan" else "no" if internet == "no" else "unknown"
    description = tags.get("description:ru") or tags.get("description") or tags.get("description:en")
    if description is not None:
        description = str(description).strip() or None
    return {
        "id": f"osm:{osm_type}:{osm_id}",
        "name": name,
        "lat": latitude,
        "lon": longitude,
        "category": category,
        "tags_json": json.dumps(safe_tags, ensure_ascii=False, sort_keys=True),
        "description": description,
        "description_source": "OpenStreetMap" if description else None,
        "opening_hours": str(tags["opening_hours"]) if tags.get("opening_hours") else None,
        "indoor_status": indoor_status,
        "power_outlets_status": power_status,
        "wifi_status": wifi_status,
        "visit_minutes": DEFAULT_VISIT_MINUTES[category],
        "verified_fields_json": "{}",
        "source": "OpenStreetMap",
        "source_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        "fetched_at": fetched_at,
    }


def normalize_elements(elements: list[Any], fetched_at: str) -> tuple[list[dict[str, Any]], int, int]:
    records: dict[str, dict[str, Any]] = {}
    invalid = duplicates = 0
    for element in elements:
        record = normalize_element(element, fetched_at)
        if record is None:
            invalid += 1
        else:
            duplicates += int(record["id"] in records)
            records[record["id"]] = record
    return list(records.values()), invalid, duplicates
