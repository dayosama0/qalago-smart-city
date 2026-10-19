"""Finite-timeout Open-Meteo current weather and clearly simulated scenarios."""
from copy import deepcopy
from datetime import datetime
import math
import os
import threading
import time

import requests

from config import TIMEZONE
from core.models import Weather

CACHE_SECONDS = 12 * 60
_cache: dict[tuple[float, float], tuple[float, Weather]] = {}
_cache_lock = threading.Lock()

# Prototype thresholds, not official emergency warnings. Units: m/s, mm, Celsius.
CAUTION_WIND = 10
SEVERE_WIND = 18
CAUTION_GUST = 15
SEVERE_GUST = 25
CAUTION_RAIN = 0.5
SEVERE_RAIN = 4
CAUTION_COLD = -10
SEVERE_COLD = -25


def classify_weather(apparent_temperature: float, wind_speed: float, wind_gusts: float, precipitation: float) -> str:
    if (apparent_temperature <= SEVERE_COLD or wind_speed >= SEVERE_WIND
            or wind_gusts >= SEVERE_GUST or precipitation >= SEVERE_RAIN):
        return "severe"
    if (apparent_temperature <= CAUTION_COLD or wind_speed >= CAUTION_WIND
            or wind_gusts >= CAUTION_GUST or precipitation >= CAUTION_RAIN):
        return "caution"
    return "normal"


def clear_weather_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _unknown() -> Weather:
    return Weather(status="unknown", note="Текущая погода недоступна. Проверьте условия перед выходом; ясная погода не предполагается.")


def _number(value) -> float:
    if isinstance(value, bool):
        raise ValueError("Invalid weather value")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Invalid weather value")
    return number


def get_weather(mode: str, latitude: float, longitude: float) -> Weather:
    scenarios = {
        "clear": (18, 18, 2, 4, 0),
        "wind": (7, 2, 14, 20, 0),
        "rain": (10, 7, 5, 8, 2),
        "cold": (-22, -30, 7, 12, 0),
    }
    if mode in scenarios:
        temperature, apparent, wind, gusts, rain = scenarios[mode]
        return Weather(status=classify_weather(apparent, wind, gusts, rain), is_simulated=True,
                       source=f"scenario:{mode}", temperature=temperature, apparent_temperature=apparent,
                       wind_speed=wind, wind_gusts=gusts, precipitation=rain,
                       note="СИМУЛЯЦИЯ погоды. Пороговые значения — эвристики прототипа, не официальное предупреждение.")
    if mode != "live":
        raise ValueError("Unknown weather mode")
    if os.getenv("WEATHER_ENABLED", "1").casefold() in {"0", "false", "no"}:
        return _unknown()
    # Only coarse coordinates are sent to the weather provider; never logged.
    cache_key = (round(latitude, 2), round(longitude, 2))
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < CACHE_SECONDS:
            return deepcopy(cached[1])
    try:
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": cache_key[0], "longitude": cache_key[1],
            "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,weather_code",
            "wind_speed_unit": "ms", "timezone": "Asia/Almaty",
        }, timeout=(3, 6))
        response.raise_for_status()
        body = response.json()
        current = body["current"]
        temperature, apparent, wind, gusts, rain = (
            _number(current[key]) for key in ("temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_gusts_10m", "precipitation")
        )
        if wind < 0 or gusts < 0 or rain < 0:
            raise ValueError("Negative wind or precipitation")
        _number(current["weather_code"])
        if body.get("current_units", {}).get("wind_speed_10m") not in {None, "m/s"}:
            raise ValueError("Unexpected wind unit")
        observed = datetime.fromisoformat(current["time"])
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=TIMEZONE)
        weather = Weather(status=classify_weather(apparent, wind, gusts, rain), source="Open-Meteo",
                          observed_at=observed.isoformat(), temperature=temperature, apparent_temperature=apparent,
                          wind_speed=wind, wind_gusts=gusts, precipitation=rain,
                          note="Текущие данные Open-Meteo; пороги прототипа не являются официальными предупреждениями.")
    except (requests.RequestException, KeyError, TypeError, ValueError, OverflowError):
        # Error results are not cached as a fabricated weather observation.
        return _unknown()
    with _cache_lock:
        if len(_cache) >= 32:
            _cache.pop(next(iter(_cache)))
        _cache[cache_key] = (now, deepcopy(weather))
    return weather
