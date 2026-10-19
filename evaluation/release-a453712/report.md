# Automated representative-query evaluation

Executed: 2026-10-19T13:35:27+00:00.

**These 15 prompts are authored synthetic examples. No human participants or relevance ratings have been collected.**

Dataset SHA-256: `b7f26c59fac6ce5868e8dec1ee406d185b4a5656f20cbafaee975294066b8ab4`. Backend/script fingerprint: `119b60c4496fff6c89a18a2b0bfc8336d3591cd2e3e25dec0f44a534eba1c9fa`.

Base HEAD: `a4537120335ce15c8b3b6c445a4f72f222b66c50`; working tree dirty at run: `False`. A dirty run is not a claim that HEAD contains the evaluated changes.

Automated checks: **15/15 cases**. Direct-category-match proxy: **9/15** (60.0%); this is not a human relevance score.

Cards within the independently recomputed estimated budget: **39/39**. Source-field mismatches: **0**. Strict-feature violations: **0**. Listed-closed returned cards: **0**. Unknown schedules: **18**.

Recommendation-only latency min / median / max: **0.022 / 2.301 / 9.508 ms**; no warm-up, single run on Windows / Python 3.13.7. This is not a performance benchmark.

Source links were checked locally for canonical OSM format and matching snapshot objects; no HTTP reachability or current opening was verified.

| Case | Direct | Other-category alternatives | ms | Automated assertions |
| --- | ---: | ---: | ---: | --- |
| architecture_baiterek | 2 | 1 | 9.508 | PASS |
| architecture_expo_short | 0 | 3 | 1.998 | PASS |
| nature_park | 1 | 2 | 4.501 | PASS |
| quiet_break | 3 | 0 | 8.665 | PASS |
| family_park | 3 | 0 | 4.587 | PASS |
| family_expo | 3 | 0 | 2.851 | PASS |
| coffee_expo | 3 | 0 | 1.243 | PASS |
| quiet_confirmed_outlet | 0 | 0 | 1.554 | PASS |
| coffee_wifi | 2 | 1 | 1.588 | PASS |
| wind_nature_off | 3 | 0 | 1.558 | PASS |
| wind_nature_on | 0 | 3 | 1.521 | PASS |
| rain_park | 0 | 3 | 5.993 | PASS |
| cold_architecture | 0 | 3 | 2.705 | PASS |
| night_2300 | 3 | 0 | 2.301 | PASS |
| airport_before_flight | 0 | 0 | 0.022 | PASS |

## Empty, alternative-only and failed cases

- **architecture_expo_short**: После ограничений времени, расписания и погоды прямых совпадений по категории нет. Ниже отдельно показаны альтернативы в других категориях с сохранением обязательных удобств. Automated errors: none.
- **quiet_confirmed_outlet**: The committed snapshot has no confirmed power outlets; unknown is insufficient. Automated errors: none.
- **wind_nature_on**: После ограничений времени, расписания и погоды прямых совпадений по категории нет. Ниже отдельно показаны альтернативы в других категориях с сохранением обязательных удобств. Automated errors: none.
- **rain_park**: После ограничений времени, расписания и погоды прямых совпадений по категории нет. Ниже отдельно показаны альтернативы в других категориях с сохранением обязательных удобств. Automated errors: none.
- **cold_architecture**: После ограничений времени, расписания и погоды прямых совпадений по категории нет. Ниже отдельно показаны альтернативы в других категориях с сохранением обязательных удобств. Automated errors: none.
- **airport_before_flight**: A flight deadline must not produce an excursion away from the airport. Automated errors: none.

## Mechanical caveats for human review

- **architecture_baiterek**: At least one returned option has unknown or unsupported hours; its availability is unverified. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.
- **architecture_expo_short**: At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified. No direct category match remains; only explicitly separate other-category alternatives are returned.
- **nature_park**: At least one returned option has unknown or unsupported hours; its availability is unverified. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.
- **quiet_break**: Quietness is inferred from broad categories; noise was not measured or confirmed. At least one returned option has unknown or unsupported hours; its availability is unverified. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.
- **family_park**: A child-oriented category match does not verify age suitability, facilities or access. Multiple category intents use OR matching; a card can match one requested category without matching all. At least one returned option has unknown or unsupported hours; its availability is unverified.
- **family_expo**: A child-oriented category match does not verify age suitability, facilities or access. Multiple category intents use OR matching; a card can match one requested category without matching all. At least one returned option has unknown or unsupported hours; its availability is unverified.
- **coffee_expo**: At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.
- **quiet_confirmed_outlet**: Quietness is inferred from broad categories; noise was not measured or confirmed. Multiple category intents use OR matching; a card can match one requested category without matching all.
- **coffee_wifi**: At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.
- **wind_nature_off**: At least one returned option has unknown or unsupported hours; its availability is unverified.
- **wind_nature_on**: At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified. No direct category match remains; only explicitly separate other-category alternatives are returned.
- **rain_park**: At least one returned option has unknown or unsupported hours; its availability is unverified. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified. No direct category match remains; only explicitly separate other-category alternatives are returned.
- **cold_architecture**: Multiple category intents use OR matching; a card can match one requested category without matching all. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified. No direct category match remains; only explicitly separate other-category alternatives are returned.
- **night_2300**: Unusual is a broad cultural taxonomy, not evidence of a distinctive experience. Multiple category intents use OR matching; a card can match one requested category without matching all. At least one returned option has unknown or unsupported hours; its availability is unverified. At least one indoor classification is category-based likely_indoor; actual shelter/heating is unverified.

## Recorded wind comparison

- Shield OFF: NU Park; first-option estimated outdoor minutes 35.0; direct matches 3.
- Shield ON: Mega Silk Way; first-option estimated outdoor minutes 0.7; direct matches 0.
These are different independent options. Category-based likely-indoor status is uncertain; no measured safety improvement is claimed.

## Human review is pending

`rater_a_blank.csv` and `rater_b_blank.csv` contain empty rating cells. Use [the protocol](../../docs/EVALUATION_PROTOCOL.md); keep the two reviews independent before adjudication. The automated run did not count unsupported claims in free text.
