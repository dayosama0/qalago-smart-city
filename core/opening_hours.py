"""Conservative weekly subset of the OSM opening_hours grammar.

Reference: https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification
The WHOLE expression must match the supported grammar. Holidays, date/season
selectors, solar times, comments, conditional rules and fallbacks are unknown.
Normal semicolon open rules replace earlier hours on their selected days; off
rules subtract only their selected intervals. No claim of live availability.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
import math
import re

from config import TIMEZONE

_WEEK_MINUTES = 7 * 24 * 60
_DAYS = {day.casefold(): index for index, day in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"))}
_DAY = r"(?:Mo|Tu|We|Th|Fr|Sa|Su)"
_DAY_PART = rf"{_DAY}(?:\s*-\s*{_DAY})?"
_DAY_LIST = rf"{_DAY_PART}(?:\s*,\s*{_DAY_PART})*"
_RULE = re.compile(rf"(?:(?P<days>{_DAY_LIST})\s+)?(?P<body>.+)", re.IGNORECASE)
_SPAN = re.compile(r"([0-2][0-9]):([0-5][0-9])\s*-\s*([0-2][0-9]):([0-5][0-9])")


@dataclass(frozen=True)
class OpeningEvaluation:
    status: str  # listed_open, listed_closed, unknown; calculated per request only
    reason: str


def _selected_days(value: str | None) -> set[int]:
    if value is None:
        return set(range(7))
    result = set()
    for part in value.split(","):
        bounds = [item.strip().casefold() for item in part.split("-")]
        start, end = _DAYS[bounds[0]], _DAYS[bounds[-1]]
        for offset in range((end - start) % 7 + 1):
            result.add((start + offset) % 7)
    return result


@lru_cache(maxsize=128)
def parse_weekly_schedule(raw: str | None) -> bytes | None:
    """A repeating minute grid, or None if any part is unsupported/ambiguous.

    Hours use [start,end) intervals. 24:00 is accepted only as an end;
    same-time endpoints and extended hours beyond 24:00 remain unknown.
    """
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 1000:
        return None
    rules = raw.strip().split(";")
    if len(rules) > 32 or any(not rule.strip() for rule in rules):
        return None
    schedule = bytearray(_WEEK_MINUTES)
    for raw_rule in rules:
        rule = raw_rule.strip()
        if rule == "24/7":
            schedule[:] = b"\x01" * _WEEK_MINUTES
            continue
        match = _RULE.fullmatch(rule)
        if match is None:
            return None
        days = _selected_days(match.group("days"))
        body = match.group("body").strip()
        state_match = re.search(r"(?:^|\s)(open|off|closed)$", body, re.IGNORECASE)
        is_closed = bool(state_match and state_match.group(1).casefold() in {"off", "closed"})
        if state_match:
            body = body[:state_match.start()].strip()
        if not body:
            if not is_closed:
                return None
            spans = [(0, 1440)]
        else:
            spans = []
            for text in body.split(","):
                span = _SPAN.fullmatch(text.strip())
                if span is None:
                    return None
                h1, m1, h2, m2 = map(int, span.groups())
                if h1 > 23 or h2 > 24 or (h2 == 24 and m2 != 0):
                    return None
                start, end = h1 * 60 + m1, h2 * 60 + m2
                if end == start:
                    return None
                if end < start:
                    end += 1440
                spans.append((start, end))
        # Clear every affected day before adding spans, so a single Mo-Fr
        # overnight rule preserves its own spill into the next selected day.
        if not is_closed:
            for day in days:
                schedule[day * 1440:(day + 1) * 1440] = b"\x00" * 1440
        for day in days:
            for start, end in spans:
                for minute in range(day * 1440 + start, day * 1440 + end):
                    schedule[minute % _WEEK_MINUTES] = 0 if is_closed else 1
    return bytes(schedule)


def evaluate_opening_hours(raw: str | None, requested_at: datetime,
                           travel_minutes: float = 0, visit_minutes: float = 0) -> OpeningEvaluation:
    """Require listed availability now AND throughout estimated arrival/visit.

    Arrival and visit completion are estimates; no waiting for a later opening
    is offered. The visit may end exactly at listed closing time, but arrival
    at closing is excluded. Fractional minutes are checked conservatively.
    """
    schedule = parse_weekly_schedule(raw)
    if schedule is None:
        return OpeningEvaluation("unknown", "missing" if not raw else "unsupported")
    if not isinstance(requested_at, datetime):
        raise ValueError("Opening hours require a datetime")
    if any(isinstance(value, bool) or not math.isfinite(value) or value < 0 or value > 480
           for value in (travel_minutes, visit_minutes)):
        raise ValueError("Travel and visit minutes must be finite and between zero and 480")
    local = requested_at.replace(tzinfo=TIMEZONE) if requested_at.tzinfo is None else requested_at.astimezone(TIMEZONE)

    def minute_index(value: datetime) -> int:
        return value.weekday() * 1440 + value.hour * 60 + value.minute

    if not schedule[minute_index(local)]:
        return OpeningEvaluation("listed_closed", "closed_at_requested_time")
    arrival = local + timedelta(minutes=travel_minutes)
    if not schedule[minute_index(arrival)]:
        return OpeningEvaluation("listed_closed", "closed_at_arrival")
    finish = arrival + timedelta(minutes=visit_minutes)
    cursor = arrival.replace(second=0, microsecond=0)
    while cursor < finish:
        if not schedule[minute_index(cursor)]:
            return OpeningEvaluation("listed_closed", "visit_exceeds_hours")
        cursor += timedelta(minutes=1)
    return OpeningEvaluation("listed_open", "listed_window_fits")
