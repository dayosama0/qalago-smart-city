# Listed hours: supported grammar and limits

`core/opening_hours.py` implements a deliberately limited weekly subset of the
[OSM opening_hours specification](https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification).
It evaluates the **whole expression**, in `Asia/Almaty`, rather than extracting
the first recognizable time range. It does not infer a missing schedule.

## Supported

- `24/7`, unconditional `off` / `closed`.
- Weekday names, ranges and lists: `Mo-Fr`, `Sa,Su`, `Fr-Mo`.
- One or more numeric spans: `Mo-Fr 09:00-12:00,13:00-18:00`.
- Overnight spans: `Fr-Sa 22:00-02:00`, including Sunday-to-Monday rollover.
- `24:00` as the end of a span, for example `Mo-Su 10:00-24:00`.
- Semicolon weekly rules: later ordinary rules replace the hours on the days
  they select; `off` rules subtract the specified intervals. Regression cases
  cover the specification's overnight and replacement examples.

Examples such as `Mo-Su 10:00-22:00`, `Mo-Fr 09:00-18:00; Sa 10:00-14:00`,
and `24/7; Tu 12:00-14:00 off` are interpreted.

## Unknown, never guessed

An unsupported component makes the full expression unknown: `PH`, `SH`,
season/date selectors, solar times, comments, conditional rules, fallbacks,
additional-rule comma syntax, `10:00+`, or extended hours beyond `24:00`.
`Mo-Fr 09:00-18:00; PH off`, for instance, is unknown in full; the app does not
pretend to have a Kazakhstan holiday calendar. Equal start/end spans are also
unknown; use the unambiguous `24/7` form for continuous availability.

## Selection and wording

The selected clock instant, estimated arrival, and the **entire estimated
visit** must fit the listed schedule. No waiting for a later opening is offered.
A visit may end exactly at closing, but arriving at the listed closing time
does not qualify. Fractional walking/visit minutes are handled conservatively.
Return travel and the time reserve are part of the time budget, not the venue's
visit window.

- `listed_open`: a supported schedule fits those checks. The card says
  **«Согласно указанному расписанию…»** and that current access is unverified.
- `listed_closed`: at least one required part of that window is outside the
  schedule; the candidate is excluded before ranking and optional generation.
- `unknown`: hours are absent or the expression is unsupported. The place can
  remain eligible with explicit uncertainty; unknown never becomes open.

The status is calculated per request, not stored in SQLite. Original listed
hours remain visible. Source URL and retrieval/check date are field-specific:
an evidenced operator override is attributed to that operator; base OSM facts
keep their OSM attribution.

This is a weekly schedule model, not live verification. Closures, booking,
cash-desk deadlines, last admission, special events and holiday exceptions can
still differ. Known seasonal or partial-feature evidence was not simplified
into unsupported venue-wide claims; see `POI_ENRICHMENT.md`.
