"""Supported OSM syntax is evaluated completely; unsupported syntax is unknown."""
from datetime import datetime

import pytest

from core.opening_hours import evaluate_opening_hours, parse_weekly_schedule


@pytest.mark.parametrize("raw,at,status", [
    ("Mo-Su 10:00-22:00", "2026-10-19T15:00:00+05:00", "listed_open"),
    ("Mo-Su 10:00-22:00", "2026-10-19T23:00:00+05:00", "listed_closed"),
    ("Mo-Fr 09:00-18:00", "2026-10-25T12:00:00+05:00", "listed_closed"),
    ("Mo,We-Fr 09:00-18:00", "2026-10-20T12:00:00+05:00", "listed_closed"),
    ("Mo,We-Fr 09:00-18:00", "2026-10-21T12:00:00+05:00", "listed_open"),
    ("Fr-Mo 09:00-18:00", "2026-10-19T12:00:00+05:00", "listed_open"),
    ("09:00-12:00,13:00-18:00", "2026-10-19T12:30:00+05:00", "listed_closed"),
    ("09:00-12:00,13:00-18:00", "2026-10-19T13:00:00+05:00", "listed_open"),
    ("Mo-Su 09:00-12:00; We 15:00-18:00", "2026-10-21T10:00:00+05:00", "listed_closed"),
    ("Mo-Su 09:00-18:00; We off", "2026-10-21T10:00:00+05:00", "listed_closed"),
    ("Mo-Su 09:00-18:00; We 12:00-13:00 off", "2026-10-21T10:00:00+05:00", "listed_open"),
    ("Mo-Su 09:00-18:00; We 12:00-13:00 off", "2026-10-21T12:00:00+05:00", "listed_closed"),
    ("24/7; Su off", "2026-10-25T10:00:00+05:00", "listed_closed"),
    ("24/7; Su off", "2026-10-19T10:00:00+05:00", "listed_open"),
    ("24/7", "2026-10-25T23:59:00+05:00", "listed_open"),
    ("Fr 22:00-02:00", "2026-10-24T01:00:00+05:00", "listed_open"),
    ("Fr 22:00-02:00", "2026-10-24T02:00:00+05:00", "listed_closed"),
    ("Su 22:00-02:00", "2026-10-19T01:00:00+05:00", "listed_open"),
    ("Mo-Fr 22:00-02:00", "2026-10-20T01:00:00+05:00", "listed_open"),
    ("Sa 16:00-03:00; Su 16:00-23:00", "2026-10-25T01:00:00+05:00", "listed_closed"),
    ("00:00-24:00", "2026-10-19T23:59:00+05:00", "listed_open"),
    ("  CLOSED  ", "2026-10-19T12:00:00+05:00", "listed_closed"),
    ("off", "2026-10-19T12:00:00+05:00", "listed_closed"),
])
def test_supported_weekly_schedules(raw, at, status):
    assert evaluate_opening_hours(raw, datetime.fromisoformat(at)).status == status


@pytest.mark.parametrize("raw", [
    None, "", "Mo-Fr 09:00-18:00; PH off", "Mo-Su 10:00-22:00; SH off",
    "sunrise-sunset", "Apr-Oct 10:00-18:00", 'Mo-Fr 10:00-18:00 "appointment"',
    'Mo-Fr 10:00-18:00 || "call first"', "Mo[1] 10:00-18:00", "10:00+",
    "10:00-24:30", "25:00-26:00", "10:00-10:00", "10:00-18:00;",
    "Sa 16:00-03:00, Su 16:00-23:00", "Mo-Su 10:00-18:00; nonsense",
])
def test_unsupported_entire_expression_stays_unknown(raw):
    assert parse_weekly_schedule(raw) is None
    assert evaluate_opening_hours(raw, datetime.fromisoformat("2026-10-19T23:00:00+05:00")).status == "unknown"


@pytest.mark.parametrize("at,travel,visit,status,reason", [
    ("2026-10-19T21:40:00+05:00", 5, 20, "listed_closed", "visit_exceeds_hours"),
    ("2026-10-19T21:40:00+05:00", 20, 5, "listed_closed", "closed_at_arrival"),
    ("2026-10-19T09:55:00+05:00", 10, 20, "listed_closed", "closed_at_requested_time"),
    ("2026-10-19T21:35:00+05:00", 5, 20, "listed_open", "listed_window_fits"),
    ("2026-10-19T21:59:30+05:00", 0, 0.5, "listed_open", "listed_window_fits"),
    ("2026-10-19T21:59:30+05:00", 0, 0.51, "listed_closed", "visit_exceeds_hours"),
])
def test_requested_time_arrival_and_whole_visit(at, travel, visit, status, reason):
    result = evaluate_opening_hours("Mo-Su 10:00-22:00", datetime.fromisoformat(at), travel, visit)
    assert result.status == status
    assert result.reason == reason


def test_visit_cannot_bridge_a_listed_lunch_closure():
    result = evaluate_opening_hours("09:00-12:00,13:00-18:00", datetime.fromisoformat("2026-10-19T11:50:00+05:00"), 0, 80)
    assert result.status == "listed_closed"
    assert result.reason == "visit_exceeds_hours"


def test_timezone_conversion_and_midnight_continuity():
    utc = datetime.fromisoformat("2026-10-19T05:00:00+00:00")
    assert evaluate_opening_hours("Mo 10:00-11:00", utc, 1, 20).status == "listed_open"
    sunday = datetime.fromisoformat("2026-10-25T23:55:00+05:00")
    assert evaluate_opening_hours("24/7", sunday, 5, 30).status == "listed_open"


@pytest.mark.parametrize("travel,visit", [(float("nan"), 20), (-1, 20), (5, float("inf"))])
def test_invalid_estimates_rejected(travel, visit):
    with pytest.raises(ValueError):
        evaluate_opening_hours("24/7", datetime.fromisoformat("2026-10-19T12:00:00+05:00"), travel, visit)
