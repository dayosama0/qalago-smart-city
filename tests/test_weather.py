import requests

from core.weather import clear_weather_cache, get_weather


def test_weather_scenarios_are_deterministic_and_labeled():
    assert get_weather("clear", 51, 71).status == "normal"
    assert get_weather("wind", 51, 71).status == "caution"
    assert get_weather("rain", 51, 71).status == "caution"
    assert get_weather("cold", 51, 71).status == "severe"
    assert get_weather("wind", 51, 71).is_simulated
    assert get_weather("wind", 51, 71).observed_at is None


def test_live_weather_timeout_is_unknown(monkeypatch):
    clear_weather_cache()
    monkeypatch.setenv("WEATHER_ENABLED", "1")
    def failed_request(*args, **kwargs):
        assert kwargs["timeout"] == (3, 6)
        raise requests.Timeout("offline test")
    monkeypatch.setattr("core.weather.requests.get", failed_request)
    result = get_weather("live", 51.100123, 71.400123)
    assert result.status == "unknown"
    assert result.temperature is None
    assert not result.is_simulated


def test_live_weather_correct_units_timestamp_and_cache(monkeypatch):
    clear_weather_cache()
    monkeypatch.setenv("WEATHER_ENABLED", "1")
    calls = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"current_units": {"wind_speed_10m": "m/s"}, "current": {
                "temperature_2m": 9, "apparent_temperature": 4, "precipitation": 0,
                "wind_speed_10m": 12, "wind_gusts_10m": 18, "weather_code": 3,
                "time": "2026-10-19T12:00",
            }}
    def fake_request(*args, **kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr("core.weather.requests.get", fake_request)
    first = get_weather("live", 51.100123, 71.400123)
    first.note = "mutated copy"
    second = get_weather("live", 51.100123, 71.400123)
    assert len(calls) == 1
    assert calls[0]["params"]["wind_speed_unit"] == "ms"
    assert calls[0]["params"]["latitude"] == 51.1
    assert second.status == "caution"
    assert second.observed_at.endswith("+05:00")
    assert second.note != "mutated copy"


def test_malformed_weather_never_assumed_clear(monkeypatch):
    clear_weather_cache()
    monkeypatch.setenv("WEATHER_ENABLED", "1")
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"current": {"temperature_2m": "NaN"}}
    monkeypatch.setattr("core.weather.requests.get", lambda *args, **kwargs: Response())
    assert get_weather("live", 51, 71).status == "unknown"
