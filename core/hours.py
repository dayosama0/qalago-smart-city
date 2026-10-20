"""Conservative weekly OSM hours: unsupported expressions stay unknown."""
from datetime import datetime, timedelta
import re

DAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
DAY_LABELS = dict(zip(DAYS, ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")))


def format_hours(value: str | None) -> str:
    if not value or not value.strip():
        return "Расписание не указано"
    if value.strip() == "24/7":
        return "Круглосуточно · каждый день"
    text = re.sub(r"\b(Mo|Tu|We|Th|Fr|Sa|Su)\b", lambda m: DAY_LABELS[m[0]], value)
    text = re.sub(r"\b(off|closed)\b", "выходной", text)
    return re.sub(r";\s*", " · ", text)


def _parse(value: str):
    rules = []
    for part in value.split(";"):
        match = re.fullmatch(r"\s*(?:(Mo|Tu|We|Th|Fr|Sa|Su)([A-Za-z,\-]*)\s+)?(off|closed|\d{2}:\d{2}-\d{2}:\d{2}(?:\s*,\s*\d{2}:\d{2}-\d{2}:\d{2})*)\s*", part)
        if not match:
            return None
        day_text = (match[1] or "") + (match[2] or "")
        days = set(range(7)) if not day_text else set()
        for token in day_text.split(",") if day_text else []:
            ends = token.split("-")
            if len(ends) > 2 or any(day not in DAYS for day in ends):
                return None
            start, end = DAYS.index(ends[0]), DAYS.index(ends[-1])
            days.update((start + step) % 7 for step in range((end - start) % 7 + 1))
        intervals = []
        if match[3] not in {"off", "closed"}:
            for span in match[3].split(","):
                times = []
                for time in span.strip().split("-"):
                    hour, minute = map(int, time.split(":"))
                    if minute > 59 or hour > 24 or (hour == 24 and minute):
                        return None
                    times.append(hour * 60 + minute)
                if times[0] >= 1440 or times[0] == times[1]:
                    return None
                intervals.append(tuple(times))
        rules.append((days, intervals))
    return rules


def visit_status(value: str | None, arrival: datetime, visit_minutes: int) -> str:
    """Check the whole visit, including overnight hours and closing boundaries.

    No holiday/calendar/solar-time inference: those schedules return unknown.
    """
    if not value or not value.strip():
        return "unknown"
    value = value.strip()
    if value == "24/7":
        return "open"
    rules = _parse(value)
    if rules is None:
        return "unknown"
    windows = []
    for offset in (-1, 0, 1):
        midnight = (arrival + timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        intervals = []
        for days, spans in rules:
            if midnight.weekday() in days:
                if not spans:
                    intervals = []
                else:
                    intervals.extend(spans)
        for start, end in intervals:
            if end <= start:
                end += 1440
            windows.append((midnight + timedelta(minutes=start), midnight + timedelta(minutes=end)))
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    for start, end in merged:
        if start <= arrival < end:
            return "open" if arrival + timedelta(minutes=visit_minutes) <= end else "closes_during_visit"
    return "closed"
