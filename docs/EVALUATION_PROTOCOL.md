# Reproducible representative-query evaluation

This protocol separates automated constraint checks from independent human
judgment. The 15 prompts in `evaluation/representative_queries.json` are
**synthetic representative examples written for evaluation**. They were not
collected from users. No human participants, relevance ratings or inter-rater
agreement results have been recorded. Do not present this as a user study.

## Reproduce the automated run

From the repository root with dependencies installed:

```bash
python -m scripts.evaluate_queries
python -m pytest tests/test_evaluation.py -q
```

The command reads the genuine committed SQLite database in read-only mode. It
does not ingest or modify POIs, load secrets, call an LLM or request weather.
The evaluator explicitly passes `use_llm=False`; a network guard rejects any
unexpected outbound socket connection. Weather is a labeled deterministic
scenario. The clock is fixed to **19 October 2026, 14:00 Asia/Almaty (UTC+05)**,
except the nighttime case at **23:00**. Origins are public presets, never user
GPS. Parameters cover architecture, nature, quietness, families, cafes, strict
outlets, Wi-Fi, wind, rain, severe cold, nighttime and a flight deadline.

Use `--output-dir PATH` to write another run to a separate directory. The default
`evaluation/results/` files are explicitly generated public artifacts; rerunning
updates them and recreates the two **blank** rater templates. Save any completed
human forms under different filenames before rerunning. Do not commit personal
rater identifiers or participant data without consent.

Generated artifacts:

- `automated_results.json`: exact authored prompts/parameters, returned public
  POI cards, per-card checks, metrics, measured latencies and caveats.
- `case_results.csv`: compact automated case table.
- `report.md`: readable results, empty/alternative cases and the actual wind
  OFF/ON comparison.
- `rater_a_blank.csv`, `rater_b_blank.csv`: independent, **unfilled** review forms.

JSON records the database SHA-256, backend/config/case/evaluator code fingerprint,
Git HEAD, dirty-working-tree flag, Python version and execution time. If the tree
was dirty, HEAD is the base commit, **not** proof that the measured changes are
already in that commit or deployed. The code fingerprint normalizes text line
endings, so LF/CRLF checkout differences do not masquerade as algorithm changes.
Latency is measured around `recommend()` only, excluding independent validation,
file output and network. There are no warm-up calls. Fifteen timings on one
machine are observations, not a general performance benchmark.

## What automated assertions establish

The runner checks at most three distinct cards, deterministic answer mode,
explicit simulation labels, original snapshot identity and factual fields,
canonical OSM links, time-budget arithmetic, strict requested features, schedule
status and separation of direct category matches from alternatives. Walking
distance/time and each independent option's travel + visit + five-minute reserve
(plus return travel when selected) are independently recomputed. Listed-closed
visits must not be returned. Source URLs are validated **locally** for object
identity and format; no HTTP reachability or present-day availability is tested.

Hours validation uses the same conservative parser as the app. Its syntax
correctness is covered by the separate opening-hours regression suite; this
evaluation is not an independent certification of OSM grammar. Unsupported or
missing hours remain `unknown`. The strict outlet and flight-deadline cases
expect honest empty results, which are not automatically relevance failures.

The **direct-category-match coverage proxy** is the fraction of all 15 authored
cases with at least one card under `recommendations`. It uses the app's explicit
taxonomy; it is **not human-rated relevance**. A cafe can match a quiet-category
rule without being quiet. Family suitability and an unusual experience are not
verified by category membership. Multiple category intents use OR matching.
Every case with such limitations has mechanical notes for reviewers. Wind ON
can yield only indoor-category alternatives and this does not establish a
successful nature recommendation.

`source_field_mismatch_cards=0` means no returned identity/coordinate/category/
description/source field differed from SQLite. It does **not** mean zero
hallucinations or that every free-text assertion was verified. The runner does
not grade the truth of arbitrary prose. It explicitly reports human relevance
as `not_measured` and unsupported free-text claims as `not_human_reviewed`.
Time and exposure are model estimates; likely-indoor categories do not prove
heating, shelter or safe travel. Original OSM coverage remains four small demo
zones as recorded in `docs/DATA_PROVENANCE.md`.

## Independent two-rater procedure — pending

1. Freeze one generated JSON/report and its hashes before review. Give the same
   requests, responses, caveats and rubric to two independent reviewers.
2. Assign the anonymous roles `rater_a` and `rater_b`. Each fills their own copy
   without seeing the other's scores. Existing blank forms are not ratings.
3. Review each direct match and separate alternative against the actual prompt.
   For an empty response, assess whether the explanation and refusal respect
   the request and source limitations. Do not give a low score merely because a
   prudent flight constraint or unsupported outlet requirement produced zero.
4. Inspect the linked OSM/evidence records and the selected clock, hours and
   arithmetic. Mark `unknown` where verification is unavailable; do not invent
   observations. Count and quote any unsupported factual assertion in comments.
5. A third coordinator compares the completed forms only after both are saved.
   Preserve the original scores, record disagreements and any adjudicated
   outcome separately. Report the number actually reviewed and agreement method
   before publishing aggregate human metrics. No such scores exist yet.

## Rubric

| Field | Allowed values and anchors |
| --- | --- |
| `intent_relevance_1_5` | 1: request contradicted; 2: weak fit; 3: partial fit or honestly labeled broad alternative; 4: good fit with minor uncertainty; 5: strong supported fit, including an appropriate evidence-based refusal |
| `reason_quality_1_5` | 1: absent/misleading; 2: generic or poorly explained; 3: understandable but limited; 4: clear and tied to constraints; 5: concise, grounded explanation with material uncertainty |
| `time_correct_yes_no_unknown` | `yes`: arrival/visit/reserve and supported hours fit; `no`: demonstrable contradiction; `unknown`: evidence/grammar insufficient. Do not treat unknown availability as verified open. |
| `source_correct_yes_no_unknown` | `yes`: returned facts have matching source records; `no`: wrong object or unsupported claim; `unknown`: source cannot be checked. HTTP failure alone is not proof of wrong identity. |
| `unsupported_claim_count` | Nonnegative integer only after human review; leave blank beforehand. Count assertions about unverified facts, not explicitly estimated actions or clearly disclosed unknowns. Record the assertion and evidence gap in comments. |
| `comments` | Explain the score, material mismatch, uncertainty or unsupported statement. Do not add private locations or personal identifiers. |

Do not infer real-world safety, a product-market claim, causal climate benefit
or LLM quality from these automated results. This run uses deterministic
templates; live LLM verification has its own report and criteria.
