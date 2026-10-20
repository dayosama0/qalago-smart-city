from dataclasses import replace
import sqlite3

import pytest

from core.models import RecommendRequest
from core.recommend import recommend
from core.result_order import sort_results


def test_more_than_three_results_and_bounded_batch(synthetic_db):
    with sqlite3.connect(synthetic_db) as connection:
        for index in range(25):
            connection.execute("""INSERT INTO pois (id,name,lat,lon,category,opening_hours,visit_minutes,fetched_at)
                VALUES (?, ?, 51.1, 71.4, 'cafe', '24/7', 10, '2026-10-20')""",
                (f"synthetic:extra:{index}", f"SYNTHETIC extra {index}"))
    result = recommend(RecommendRequest(location_preset="custom", latitude=51.1, longitude=71.4,
                       duration_minutes=120, time_mode="simulated", simulated_datetime="2026-10-20T12:00"),
                       synthetic_db, use_llm=False)
    assert len(result.recommendations) == 20
    assert len({card.poi_id for card in result.recommendations}) == 20
    assert all(card.total_minutes_estimated <= 120 for card in result.recommendations)


@pytest.mark.parametrize("order,expected", [
    ("recommended", ["b", "a", "c"]),
    ("distance", ["a", "b", "c"]),
    ("duration", ["a", "b", "c"]),
    ("name", ["a", "b", "c"]),
])
def test_sorting_preserves_closed_last_without_mutating_result(synthetic_db, order, expected):
    result = recommend(RecommendRequest(location_preset="custom", latitude=51.1, longitude=71.4,
                       duration_minutes=120), synthetic_db, use_llm=False)
    base = result.recommendations[0]
    cards = [replace(base, poi_id="b", name="B", distance_m=200, total_minutes_estimated=40, opening_status="unknown"),
             replace(base, poi_id="c", name="0", distance_m=0, total_minutes_estimated=1, opening_status="closed"),
             replace(base, poi_id="a", name="A", distance_m=100, total_minutes_estimated=30, opening_status="open")]
    assert [card.poi_id for card in sort_results(cards, order)] == expected
    assert [card.poi_id for card in cards] == ["b", "c", "a"]
