"""Comparison uses the real engine and isolates Shield from time/API changes."""
from dataclasses import asdict
from unittest.mock import Mock

from core.comparison import compare_climate_shield
from core.models import RecommendRequest, Weather


def request(**changes):
    values = dict(location_preset="custom", latitude=51.1, longitude=71.4,
                  query="park", weather_mode="wind", time_mode="simulated",
                  simulated_datetime="2026-01-05T12:00:00+05:00")
    return RecommendRequest(**(values | changes))


def test_real_comparison_separates_direct_matches_and_alternatives(synthetic_db):
    original = request()
    before = asdict(original)
    result = compare_climate_shield(original, synthetic_db)
    assert result.off.recommendations[0].poi_id == "synthetic:park"
    assert not result.on.recommendations
    assert result.on.alternatives
    assert result.outdoor_difference_minutes > 0
    assert "альтернатив" in result.explanation
    assert asdict(original) == before
    assert result.off.local_datetime == result.on.local_datetime == result.evaluated_at
    assert asdict(result.off.weather) == asdict(result.on.weather)


def test_comparison_fetches_live_weather_once_and_never_calls_llm(synthetic_db, monkeypatch):
    import core.comparison as comparison
    import core.recommend as recommendations

    observation = Weather(status="caution", source="SYNTHETIC WEATHER", observed_at="2026-01-05T12:00:00+05:00")
    fetch = Mock(return_value=observation)
    monkeypatch.setattr(comparison, "get_weather", fetch)

    def unexpected(*args, **kwargs):
        raise AssertionError("Comparison must reuse weather and skip optional LLM")

    monkeypatch.setattr(recommendations, "get_weather", unexpected)
    monkeypatch.setattr(recommendations, "generate_explanations", unexpected)
    result = compare_climate_shield(request(weather_mode="live", time_mode="live", simulated_datetime=None), synthetic_db)
    assert fetch.call_count == 1
    assert not result.off.time_is_simulated and not result.on.time_is_simulated
    assert not result.off.weather.is_simulated and not result.on.weather.is_simulated
    assert result.off.weather.observed_at == result.on.weather.observed_at


def test_empty_comparison_has_no_manufactured_zero_minute_improvement(synthetic_db):
    result = compare_climate_shield(request(duration_minutes=5), synthetic_db)
    assert result.outdoor_difference_minutes is None
    assert not result.off.recommendations and not result.off.alternatives
    assert not result.on.recommendations and not result.on.alternatives
    assert "нельзя" in result.explanation


def test_normal_weather_can_legitimately_leave_results_unchanged(synthetic_db):
    result = compare_climate_shield(request(weather_mode="clear"), synthetic_db)
    assert [p.poi_id for p in result.off.recommendations] == [p.poi_id for p in result.on.recommendations]
    assert result.outdoor_difference_minutes == 0
    assert "совпали" in result.explanation
