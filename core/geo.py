"""Small, explicitly approximate geometry helpers; no routing service involved."""
import math

from config import PRESETS


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        raise ValueError("Coordinates must be numbers")
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("Coordinates must be numbers") from exc
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordinates are outside valid ranges")
    return lat, lon


def resolve_origin(request) -> tuple[float, float]:
    if request.location_preset == "custom":
        return validate_coordinates(request.latitude, request.longitude)
    if request.location_preset not in PRESETS:
        raise ValueError("Unknown origin preset")
    preset = PRESETS[request.location_preset]
    return validate_coordinates(preset["lat"], preset["lon"])


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1 = validate_coordinates(lat1, lon1)
    lat2, lon2 = validate_coordinates(lat2, lon2)
    a_lat, b_lat = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b_lat - a_lat, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(a_lat) * math.cos(b_lat) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def walking_minutes(distance_m: float) -> float:
    if not math.isfinite(distance_m) or distance_m < 0:
        raise ValueError("Distance must be finite and non-negative")
    return distance_m / 1000 * 1.3 / 4.5 * 60


# Clear aliases for callers using the terminology in the specification.
haversine = haversine_m
estimate_walking_minutes = walking_minutes
