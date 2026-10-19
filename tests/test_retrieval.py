import pytest
import sqlite3

from core.retrieval import DatabaseUnavailable, get_candidates, parse_intents


def test_strict_features_and_category_intent_parser():
    assert parse_intents("Тихое кафе с розеткой", []) == {"quiet", "coffee", "power_outlets"}
    assert {"power_outlets", "wifi"} <= parse_intents("", ["power_outlets", "wifi"])


def test_retrieval_applies_distance_access_and_budget(synthetic_db):
    candidates = get_candidates((51.1, 71.4), 60, db_path=synthetic_db)
    ids = {candidate.id for candidate in candidates}
    assert ids == {"synthetic:park", "synthetic:cafe-unknown", "synthetic:cafe-confirmed", "synthetic:museum"}
    assert all(candidate.total_minutes <= 60 for candidate in candidates)


def test_return_trip_is_in_budget(synthetic_db):
    one_way = get_candidates((51.1, 71.4), 60, db_path=synthetic_db)
    return_trip = {c.id: c for c in get_candidates((51.1, 71.4), 60, True, synthetic_db)}
    for candidate in one_way:
        assert return_trip[candidate.id].total_minutes == pytest.approx(candidate.total_minutes + candidate.travel_minutes)


def test_strict_outlets_never_matches_unknown(synthetic_db):
    candidates = get_candidates((51.1, 71.4), 60, db_path=synthetic_db, intents={"power_outlets"})
    assert [candidate.id for candidate in candidates] == ["synthetic:cafe-confirmed"]
    assert all(candidate.power_outlets_status == "confirmed" for candidate in candidates)


def test_missing_database_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(DatabaseUnavailable, match="ingestion"):
        get_candidates((51.1, 71.4), 60, db_path=path)
    assert not path.exists()


@pytest.mark.parametrize("opening_hours", ["closed", "off", "  CLOSED  "])
def test_unconditional_closed_poi_never_retrieved(synthetic_db, opening_hours):
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours=? WHERE id='synthetic:cafe-unknown'", (opening_hours,))
    assert "synthetic:cafe-unknown" not in {c.id for c in get_candidates((51.1, 71.4), 60, db_path=synthetic_db)}


def test_compound_hours_remain_uninterpreted(synthetic_db):
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours='Mo-Fr off; Sa-Su 10:00-18:00' WHERE id='synthetic:cafe-unknown'")
    assert "synthetic:cafe-unknown" in {c.id for c in get_candidates((51.1, 71.4), 60, db_path=synthetic_db)}


@pytest.mark.parametrize("tag", ["disused:amenity", "abandoned:amenity", "demolished:amenity", "removed:amenity", "construction:amenity"])
def test_inactive_category_lifecycle_tags_excluded(synthetic_db, tag):
    import json
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET tags_json=? WHERE id='synthetic:cafe-unknown'", (json.dumps({tag: "cafe"}),))
    assert "synthetic:cafe-unknown" not in {c.id for c in get_candidates((51.1, 71.4), 60, db_path=synthetic_db)}
