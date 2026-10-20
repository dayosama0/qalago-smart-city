from datetime import datetime
import sqlite3

import pytest

from core.hours import format_hours, visit_status
from core.models import RecommendRequest
from core.recommend import recommend as _recommend
from functools import partial
recommend = partial(_recommend, use_llm=False)


@pytest.mark.parametrize("hours,when,minutes,status", [
    ("24/7", "2026-10-19T23:55", 30, "open"),
    ("Mo-Fr 09:00-18:00", "2026-10-19T10:00", 20, "open"),
    ("Mo-Fr 09:00-18:00", "2026-10-18T10:00", 20, "closed"),
    ("Mo-Fr 09:00-18:00", "2026-10-19T18:00", 20, "closed"),
    ("Mo-Fr 09:00-18:00", "2026-10-19T17:50", 20, "closes_during_visit"),
    ("Mo-Fr 09:00-18:00", "2026-10-19T17:40", 20, "open"),
    ("Fr-Mo 22:00-02:00", "2026-10-20T01:00", 20, "open"),
    ("09:00-12:00,13:00-18:00", "2026-10-19T11:50", 30, "closes_during_visit"),
    ("Mo-Su 09:00-18:00; Su off", "2026-10-18T10:00", 20, "closed"),
    ("Mo,We,Fr 09:00-18:00", "2026-10-20T10:00", 20, "closed"),
    ("Mo-Fr 09:00-18:00; PH off", "2026-10-19T10:00", 20, "unknown"),
    ("sunrise-sunset", "2026-10-19T10:00", 20, "unknown"),
    ("09:99-18:00", "2026-10-19T10:00", 20, "unknown"),
    (None, "2026-10-19T10:00", 20, "unknown"),
    ("Mo-Su 10:00-22:00", "2026-10-20T00:00", 20, "closed"),
    ("Mo-Su 10:00-22:00", "2026-10-20T00:30", 20, "closed"),
    ("10:00-22:00", "2026-10-20T09:59", 20, "closed"),
    ("10:00-22:00", "2026-10-20T10:00", 20, "open"),
    ("10:00-22:00", "2026-10-20T22:00", 20, "closed"),
])
def test_visit_hours(hours, when, minutes, status):
    assert visit_status(hours, datetime.fromisoformat(when), minutes) == status


def test_readable_hours():
    assert format_hours("Mo-Fr 09:00-18:00; Sa-Su off") == "Пн-Пт 09:00-18:00 · Сб-Вс выходной"
    assert "Круглосуточно" in format_hours("24/7")


def test_closed_candidates_are_last_before_top_three(synthetic_db):
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours = '00:00-00:01'")
        poi_id = connection.execute("SELECT id FROM pois WHERE category = 'cafe' LIMIT 1").fetchone()[0]
        connection.execute("UPDATE pois SET opening_hours = '24/7' WHERE id = ?", (poi_id,))
    response = recommend(RecommendRequest(duration_minutes=120, climate_shield_enabled=False,
                         time_mode="simulated", simulated_datetime="2026-10-19T12:00:00"), synthetic_db)
    assert response.recommendations[0].poi_id == poi_id
    assert response.recommendations[0].opening_status == "open"
    assert all(card.opening_status == "closed" for card in response.recommendations[1:])
    assert response.recommendations[0].arrival_datetime


@pytest.mark.parametrize("hour,status", [(0, "closed"), (12, "open"), (22, "closed")])
def test_live_mode_checks_actual_local_clock(synthetic_db, monkeypatch, hour, status):
    from config import TIMEZONE
    import core.recommend as backend

    now = datetime(2026, 10, 20, hour, 0, tzinfo=TIMEZONE)
    monkeypatch.setattr(backend, "local_now", lambda: now)
    with sqlite3.connect(synthetic_db) as connection:
        connection.execute("UPDATE pois SET opening_hours = 'Mo-Su 10:00-22:00'")
    result = recommend(RecommendRequest(duration_minutes=120, climate_shield_enabled=False,
                       time_mode="live", simulated_datetime="2026-10-20T12:00:00"), synthetic_db)
    assert result.local_datetime == now.isoformat()
    assert result.recommendations
    assert all(card.opening_status_now == card.opening_status == status for card in result.recommendations)
