"""Product audit regressions: hours, truthful matches, strict requirements."""
from datetime import datetime
import json
import sqlite3

from core.models import RecommendRequest, Weather
from core.recommend import recommend
from core.retrieval import parse_intents


def request(**kwargs):
    return RecommendRequest(**{**dict(location_preset="custom", latitude=51.1, longitude=71.4,
        weather_mode="clear", time_mode="simulated", simulated_datetime="2026-10-19T12:00:00+05:00"), **kwargs})


def all_cards(response):
    return response.recommendations + response.alternatives


def test_supported_hours_exclude_late_mall_style_visits(synthetic_db):
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours='Mo-Su 10:00-22:00' WHERE id='synthetic:cafe-confirmed'")
    day = recommend(request(query="coffee", interests=["power_outlets"]), synthetic_db)
    assert len(day.recommendations) == 1
    assert day.recommendations[0].opening_status == "listed_open"
    assert "Согласно указанному расписанию" in day.recommendations[0].opening_note
    assert "Доступность сейчас не проверена" in day.recommendations[0].opening_note
    night = recommend(request(query="coffee", interests=["power_outlets"], simulated_datetime="2026-10-19T23:00:00+05:00"), synthetic_db)
    assert not all_cards(night)
    near_close = recommend(request(query="coffee", interests=["power_outlets"], simulated_datetime="2026-10-19T21:45:00+05:00"), synthetic_db)
    assert not all_cards(near_close)


def test_complex_hours_unknown_remains_eligible(synthetic_db):
    response = recommend(request(query="coffee", interests=["power_outlets"], simulated_datetime="2026-10-19T23:00:00+05:00"), synthetic_db)
    assert response.recommendations[0].opening_status == "unknown"
    assert "не удалось надёжно разобрать" in response.recommendations[0].opening_note


def test_direct_matches_prioritized_and_alternatives_separate(synthetic_db):
    response = recommend(request(query="museum"), synthetic_db)
    assert [card.poi_id for card in response.recommendations] == ["synthetic:museum"]
    assert response.alternatives
    assert all(card.category != "museum" for card in response.alternatives)
    assert len(all_cards(response)) <= 3
    assert all("Альтернатива" in card.reason for card in response.alternatives)


def test_only_alternatives_explains_missing_nature_match(synthetic_db):
    response = recommend(request(query="nature", weather_mode="wind"), synthetic_db)
    assert not response.recommendations
    assert response.alternatives
    assert "прямых совпадений" in response.general_message
    assert len(all_cards(response)) <= 3


def test_alternatives_never_relax_strict_features(synthetic_db):
    response = recommend(request(query="nature", interests=["power_outlets"]), synthetic_db)
    assert not response.recommendations
    assert [card.poi_id for card in response.alternatives] == ["synthetic:cafe-confirmed"]


def test_unusual_is_independent_of_architecture(synthetic_db):
    assert parse_intents("необычное место", ["unusual"]) == {"unusual"}
    response = recommend(request(query="unusual"), synthetic_db)
    assert response.recommendations[0].poi_id == "synthetic:museum"
    assert all(card.category in {"attraction", "museum", "gallery", "arts_centre", "viewpoint"} for card in response.recommendations)


def test_wheelchair_unknown_or_limited_never_satisfies_requirement(synthetic_db):
    assert not all_cards(recommend(request(query="wheelchair accessible coffee"), synthetic_db))
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET tags_json=? WHERE id='synthetic:cafe-unknown'", (json.dumps({"wheelchair": "limited"}),))
    assert not all_cards(recommend(request(query="wheelchair accessible coffee"), synthetic_db))
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET tags_json=? WHERE id='synthetic:cafe-unknown'", (json.dumps({"wheelchair": "yes"}),))
    response = recommend(request(query="wheelchair accessible coffee"), synthetic_db)
    assert [card.poi_id for card in response.recommendations] == ["synthetic:cafe-unknown"]
    assert "wheelchair=yes" in response.recommendations[0].reason


def test_comparison_hooks_reuse_time_weather_and_skip_llm(synthetic_db, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("override comparison must not refetch weather or call LLM")
    monkeypatch.setattr("core.recommend.get_weather", unexpected)
    monkeypatch.setattr("core.recommend.generate_explanations", unexpected)
    at = datetime.fromisoformat("2026-10-19T15:30:00+05:00")
    weather = Weather(status="caution", is_simulated=True, source="test:wind")
    response = recommend(request(query="nature"), synthetic_db, evaluation_time=at, weather_override=weather, use_llm=False)
    assert response.local_datetime == at.isoformat()
    assert response.weather is weather
    assert response.answer_mode == "template"
    assert response.alternatives


def test_field_evidence_and_curated_description_reach_cards(synthetic_db):
    evidence_url = "https://example.org/synthetic-operator-hours"
    description_url = "https://example.org/synthetic-operator-description"
    provenance = {"opening_hours": {"evidence_url": evidence_url, "checked_at": "2026-10-19",
                                     "method": "manual_reference"}}
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours=?,verified_fields_json=?,description=?,description_source=? WHERE id='synthetic:cafe-confirmed'",
            ("Mo-Su 10:00-24:00", json.dumps(provenance), "SYNTHETIC operator-sourced description.", description_url))
    response = recommend(request(query="coffee", interests=["power_outlets"]), synthetic_db, use_llm=False)
    card = response.recommendations[0]
    assert card.source == "SYNTHETIC TEST FIXTURE"
    assert card.opening_status == "listed_open"
    assert card.opening_hours_source_url == evidence_url
    assert card.opening_hours_checked_at == "2026-10-19"
    assert f"Источник расписания: {evidence_url}" in card.opening_note
    assert "2026-10-19" in card.opening_note
    assert card.description == "SYNTHETIC operator-sourced description."
    assert card.description_source == description_url


def test_unoverridden_hours_keep_osm_field_source(synthetic_db):
    response = recommend(request(query="coffee", interests=["power_outlets"]), synthetic_db, use_llm=False)
    card = response.recommendations[0]
    assert card.description is None
    assert card.opening_hours_source_url == card.source_url
    assert card.opening_hours_checked_at == "2026-01-01T00:00:00+05:00"
