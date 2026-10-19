"""Stable request/response contract shared by UI, retrieval and tests."""
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class RecommendRequest:
    location_preset: str = "expo"
    latitude: float | None = None
    longitude: float | None = None
    query: str = ""
    interests: list[str] = field(default_factory=list)
    duration_minutes: int = 60
    walking_only: bool = True
    return_to_start: bool = False
    climate_shield_enabled: bool = True
    weather_mode: str = "clear"
    time_mode: str = "live"
    simulated_datetime: str | None = None
    flight_constraint: bool = False
    language: str = "ru"

@dataclass
class Weather:
    status: str = "unknown"
    is_simulated: bool = False
    source: str = "Open-Meteo"
    observed_at: str | None = None
    temperature: float | None = None
    apparent_temperature: float | None = None
    wind_speed: float | None = None
    wind_gusts: float | None = None
    precipitation: float | None = None
    note: str = ""

@dataclass
class Recommendation:
    poi_id: str
    name: str
    category: str
    lat: float
    lon: float
    distance_m: float
    travel_minutes_estimated: float
    visit_minutes_estimated: int
    reason: str
    action: str
    opening_note: str
    indoor_status: str
    source: str
    source_url: str
    warnings: list[str] = field(default_factory=list)
    total_minutes_estimated: float = 0

@dataclass
class RecommendResponse:
    recommendations: list[Recommendation] = field(default_factory=list)
    general_message: str | None = None
    weather: Weather = field(default_factory=Weather)
    time_is_simulated: bool = False
    answer_mode: str = "empty"
    estimated_outdoor_minutes: float = 0
    limitations: list[str] = field(default_factory=list)
    local_datetime: str = ""
