"""Download two bounded Overpass snapshots; never called during app startup."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from typing import Any

import requests

AREAS = {
    "astana": (51.06, 71.31, 51.20, 71.54),
    "airport": (50.99, 71.43, 51.05, 71.52),
}
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RETRYABLE_STATUS = {429, 502, 503, 504}


class DownloadError(RuntimeError):
    """A snapshot could not be downloaded completely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_query(bbox: tuple[float, float, float, float]) -> str:
    if len(bbox) != 4 or not all(math.isfinite(float(v)) for v in bbox):
        raise ValueError("Bounding box must contain four finite numbers")
    south, west, north, east = map(float, bbox)
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Invalid bounding box")
    bounds = ",".join(f"{v:.6f}" for v in bbox)
    return (
        "[out:json][timeout:50];\n(\n"
        f'  nwr["amenity"~"^(cafe|restaurant|library|arts_centre)$"]({bounds});\n'
        f'  nwr["tourism"~"^(museum|attraction|viewpoint|gallery)$"]({bounds});\n'
        f'  nwr["leisure"~"^(park|garden|playground)$"]({bounds});\n'
        f'  nwr["shop"="mall"]({bounds});\n'
        f'  nwr["historic"~"^(monument|memorial)$"]({bounds});\n'
        ");\nout center tags;\n"
    )


def download_area(
    area: str,
    raw_dir: Path,
    *,
    endpoint: str | None = None,
    attempts: int = 3,
    session: Any = requests,
) -> Path:
    """Save the exact successful public response; fail after at most 3 tries."""
    if area not in AREAS:
        raise ValueError(f"Unknown download area: {area}")
    if not 1 <= attempts <= 3:
        raise ValueError("attempts must be between 1 and 3")
    endpoint = endpoint or os.environ.get("OVERPASS_URL", DEFAULT_OVERPASS_URL)
    query = build_query(AREAS[area])
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": "QalaGo-MVP/1.0 (bounded educational OSM snapshot)"},
                timeout=(10, 65),
            )
            if response.status_code in RETRYABLE_STATUS:
                raise DownloadError(f"Overpass returned HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                raise DownloadError("Overpass response has no elements array")
            if payload.get("remark"):
                raise DownloadError(f"Overpass reports an incomplete response: {payload['remark']}")
            raw_dir.mkdir(parents=True, exist_ok=True)
            destination = raw_dir / f"{area}.json"
            temporary = destination.with_suffix(".json.tmp")
            temporary.write_bytes(response.content)
            temporary.replace(destination)
            metadata = {
                "area": area,
                "bbox_south_west_north_east": list(AREAS[area]),
                "endpoint": endpoint,
                "fetched_at": utc_now(),
                "query": query,
                "raw_elements": len(payload["elements"]),
                "osm_timestamp": payload.get("osm3s", {}).get("timestamp_osm_base"),
                "source": "OpenStreetMap via Overpass API",
                "license": "ODbL 1.0",
            }
            destination.with_suffix(".metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
            )
            return destination
        except requests.HTTPError as error:
            # Errors such as malformed query/authentication should not be retried.
            raise DownloadError(f"Overpass HTTP request failed: {error}") from error
        except (requests.RequestException, DownloadError, ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 * (attempt + 1))
    raise DownloadError(f"Could not fetch {area} after {attempts} attempts: {last_error}")


def cached_snapshots(raw_dir: Path) -> list[Path]:
    """Require both known areas: avoid silently incomplete offline rebuilds."""
    paths = [raw_dir / f"{area}.json" for area in AREAS]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise DownloadError("Missing cached snapshots: " + ", ".join(missing) + ". Run live ingestion first.")
    return paths
