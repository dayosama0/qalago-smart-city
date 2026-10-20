"""Import reviewed public venue facts without pretending they are OSM records."""
from datetime import date
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from ingestion.normalize import DEFAULT_VISIT_MINUTES, INDOOR_CATEGORIES, OUTDOOR_CATEGORIES


class Place(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^2gis:[0-9]+$")
    name: str = Field(min_length=1)
    lat: float = Field(ge=50.8, le=51.4)
    lon: float = Field(ge=71.0, le=71.8)
    category: str
    address: str = Field(min_length=1)
    checked_at: date
    description: str = Field(min_length=40, max_length=320)
    opening_hours: str | None = None
    coffee_shop: bool = False
    average_check_kzt: int | None = Field(default=None, gt=0, strict=True)
    wifi_status: Literal["confirmed", "no", "unknown"] = "unknown"
    evidence: dict[str, HttpUrl]
    review_note: str = ""

    @model_validator(mode="after")
    def check_evidence(self):
        if self.category not in DEFAULT_VISIT_MINUTES:
            raise ValueError("Unsupported venue category")
        required = {"name", "coordinates", "category", "address", "description"}
        for field in ("opening_hours", "average_check_kzt"):
            if getattr(self, field) is not None:
                required.add(field)
        if self.wifi_status != "unknown":
            required.add("wifi_status")
        if self.coffee_shop:
            if self.category != "cafe":
                raise ValueError("Coffee shops must have cafe category")
            required.add("coffee_shop")
        if not required <= self.evidence.keys():
            raise ValueError(f"Missing field evidence: {sorted(required - self.evidence.keys())}")
        return self


def load_curated(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Curated dataset must be a nonempty list")
    places = [Place.model_validate(row) for row in payload]
    if len({place.id for place in places}) != len(places):
        raise ValueError("Duplicate curated venue ID")
    records = []
    for place in places:
        tags = {"addr:full": place.address}
        if place.coffee_shop:
            tags["cuisine"] = "coffee_shop"
        if place.average_check_kzt is not None:
            tags["average_check:kzt"] = str(place.average_check_kzt)
        provenance = {
            key: {"evidence_url": str(url), "checked_at": place.checked_at.isoformat(),
                  "method": "manual_reference"}
            for key, url in place.evidence.items()
        }
        records.append({
            "id": place.id, "name": place.name, "lat": place.lat, "lon": place.lon,
            "category": place.category, "tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
            "description": place.description, "description_source": str(place.evidence["description"]),
            "opening_hours": place.opening_hours,
            "indoor_status": "likely_indoor" if place.category in INDOOR_CATEGORIES else
                             "outdoor" if place.category in OUTDOOR_CATEGORIES else "unknown",
            "power_outlets_status": "unknown", "wifi_status": place.wifi_status,
            "visit_minutes": DEFAULT_VISIT_MINUTES[place.category],
            "verified_fields_json": json.dumps(provenance, ensure_ascii=False, sort_keys=True),
            "source": "2GIS", "source_url": "https://2gis.kz/astana/firm/" + place.id.split(":")[1],
            "fetched_at": place.checked_at.isoformat(),
        })
    return records
