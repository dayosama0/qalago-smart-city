# QalaGo verification history

## Submission-readiness review branch — 19 October 2026

Base: `348b6a4`; branch: `codex/submission-readiness`. This work is separate from
the unchanged public deployment. Original 153 tests remain present; the expanded
suite executed locally with provider calls disabled: **219 passed in 26.90s**.
The isolated local server on port 8503 started; `/_stcore/health` returned
**HTTP 200 / ok**. Data, source snapshots, pinned requirements and workflow
remain unchanged.

The new card was also exercised in a browser with the provider key disabled.
At 390 px, document/body scroll widths were **390/390**; both external links
wrapped/read correctly with the center/entrance and external-route warning.
[Actual local capture](images/readiness-navigation-390.jpg). This is evidence
for the review branch, not the current public preview. Viewport overrides were
reset afterward.

New checks cover per-POI source-sentence grounding, wrong IDs/reassigned facts,
prompt-injection fallback, untrusted-context bounds, missing/invalid provenance,
coordinate redaction, credential-free verifier reporting, navigation privacy
and consent reset, walking URL validation, and independent evaluation arithmetic.
Independent review also found that SDK endpoint overrides could make a proxy
response look like a genuine OpenAI verification. The verifier now rejects
noncanonical endpoints before any call, pins accepted calls to
`https://api.openai.com/v1`, restores the environment afterward, and never prints
rejected URLs. Twelve additional endpoint regressions passed in the full suite.

Google Maps' [documented universal directions URL](https://developers.google.com/maps/documentation/urls/get-started#directions)
was opened in a browser with two public example coordinates. Its route panel
showed **Пешком** alternatives, validating the external link/mode. This is not a
walk-through, entrance check or independent validation of QalaGo's geometric
time estimates. No manually entered private origin was sent during verification.

The actual [15-query deterministic run](../evaluation/results/report.md) records
dataset and normalized backend/script hashes, a dirty working-tree marker, exact
parameters, measured timings and case-level caveats. **9/15** direct-category
coverage is a proxy; **39/39** cards fit independently recomputed estimated
budgets. Four cases produce alternatives only, two safely return empty, and
18 cards have unknown schedules. There are zero snapshot-field mismatches and
automated constraint failures, not a claim of zero hallucinations. Human
relevance and arbitrary free-text claims remain unreviewed; the two rater forms
are blank. See [the protocol](EVALUATION_PROTOCOL.md).

LLM descriptions are bounded, attributed untrusted data. Runtime permits only
per-POI safe phrases or exact complete source sentences and conservative actions;
novel factual prose fails closed to the existing templates. This sacrifices
paraphrase flexibility and can increase fallback. It does not independently
establish that a source is true/current, and no AI quality improvement is measured.
The explicit live verifier initially returned `not_attempted / credentials_missing`;
no paid request was made at that checkpoint. Any subsequent real-call result
must be recorded separately rather than inferred from offline tests.

Merge/main deployment is a [review checklist](RELEASE_CHECKLIST.md), not an
executed release. Two-stop itineraries, full localization, independent human
ratings, demo video/upload and an attested main Cloud build remain outside the
executed checks.

## Public 23:00 follow-up — 19 October 2026

The existing public app was exercised in a separate signed-out session with
Baiterek / 60 minutes / unusual / `необычное занятие ночью` / simulated clear
weather / simulated `2026-10-19T23:00:00+05:00` / Shield on. It showed Bәйтерек,
CrepeCafe and Degirmen (approximately 25, 28 and 29 minutes including reserve),
template mode, explicit clock simulation and late-time warnings. Baiterek's
availability remained unknown; the cafes only fit their listed schedules.

See [exact reproduction and limitations](TEST_SCENARIOS.md#public-2300-reproduction--19-october-2026)
and actual public captures: [settings](images/public-night-settings-1440.jpg),
[result](images/public-night-result-1440.jpg),
[schedule evidence](images/public-night-hours-1440.jpg). The broad night category
can admit cafes alongside an unusual request; no human relevance score or live
opening confirmation is inferred from those three direct category matches.

PR #1 head `348b6a4802556f304269d5234bff3009d5bd7f83`, base main `fe40dcd`,
open/unmerged and [successful exact-head CI](https://github.com/dayosama0/qalago-smart-city/actions/runs/39247495213)
were rechecked before this follow-up. New code is isolated on
`codex/submission-readiness`; no public deployment or merge was performed for it.
The public source link identifies the PR #1 branch, not an attested Cloud build
SHA. [Migration/release checklist](RELEASE_CHECKLIST.md) preserves that distinction.

## Public Community Cloud check — 19 October 2026

Verified public URL:
[QalaGo](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/).
The account owner completed deployment in an ordinary browser. Verification
used a separate signed-out embedded session, not the owner's screenshot.

| Executed public check | Observed result |
| --- | --- |
| Root URL request and browser startup | HTTP 200; QalaGo form and 199 POIs rendered without sign-in |
| EXPO / 60 minutes / architecture / simulated clear | Three independent cards; direct monument match, separately labeled Mega Silk Way and Luckee Yu alternatives; **Без LLM** |
| Quick **Гуляю час** | Actual calculation; first direct option Тәуелсіздіктің 25 жылдығы, approximately 40 of 60 minutes including reserve |
| Quick **С ребёнком** | Central Park origin / 120 minutes; three category matches, first Астана саябағы; unknown availability labeled |
| Quick **Сильный ветер**, then comparison | OFF first NU Park: 35.0 estimated minutes outdoors; ON first alternative Mega Silk Way: 0.7. Shared calculation time `2026-10-19T16:45:16.124962+05:00`; simulated weather explicit |
| Strict confirmed-outlet requirement | Zero results; unknown features are not treated as confirmed |
| Quick **Перед вылетом** | NQZ / 120 minutes; no city excursion; conservative flight explanation |
| Mega source details | OSM way `499328514`, operator description/schedule URLs and `2026-10-19` source/check date displayed; listed hours are not live access confirmation |
| Map expander | Folium component rendered origin plus three POI markers, zoom controls, OSM attribution and center/entrance uncertainty note |
| Generated 2GIS search | `Mega Silk Way Астана` opened as a search with results; no guaranteed organization identity or directory import claimed |
| Public source toolbar button | Opens `dayosama0/qalago-smart-city/blob/codex/audit-product-improvements/app.py`; GitHub displayed the feature branch and file commit `d6611be` |
| 390 px viewport width | App document/body scroll widths 390/390; stacked comparison, readable wrapping; [actual public capture](images/public-mobile-390.jpg) |
| 1440 px viewport width | App document/body scroll widths 1440/1440; two-column comparison; [actual public capture](images/public-desktop-1440.jpg) |

These measurements concern the rendered Streamlit app iframe, not just its
outer Cloud wrapper. Viewport overrides were reset after testing. Captures
contain public app content; the owner's browser screenshot was not committed.

At verification, the feature branch head was
`d6611beb739e00bd094de3589ad47dcd2e6e7923`; its
[CI run](https://github.com/dayosama0/qalago-smart-city/actions/runs/39243890123)
passed with 153 tests on each of Python 3.11 and 3.13. The source link identifies
the deployed branch/entrypoint, but does not expose Cloud's exact build SHA,
selected Python version or secret settings. Those admin details remain
uninspected. Public template responses prove template mode worked; they do not
prove Cloud has no configured key. No successful live OpenAI call is claimed.

The public URL follows the feature branch. `main` was still `fe40dcd` and
[PR #1](https://github.com/dayosama0/qalago-smart-city/pull/1) remained unmerged.
See [deployment guidance](DEPLOYMENT.md) for future branch updates and a stable
`main` deployment after review. This follow-up changes documentation and public
captures only; application code and data remain at the tested audit revision.
The unchanged application suite was rerun for this follow-up: **153 passed in
10.63s**; the running local app's health endpoint returned **HTTP 200 / ok**.

## Audit improvements — 19 October 2026

Branch: `codex/audit-product-improvements`; base: `fe40dcd`. The baseline below
is preserved as history, not used as evidence that the new revision passed.

| Executed check | Actual result |
| --- | --- |
| Baseline suite before edits | 74 passed |
| Current `python -m pytest -q` | 153 passed; offline backend, parser, data, comparison and Streamlit interaction tests |
| `python -m pip check` | No broken requirements |
| Feature app on `127.0.0.1:8502` | Started with no OpenAI key; real recommendations and comparison rendered |
| Browser quick scenario: simulated wind / EXPO / 60 minutes | Real calls; OFF first NU Park, estimated 35.0 minutes outdoors; ON first Mega Silk Way, estimated 0.7 minutes outdoors |
| Comparison honesty | Shared clock/weather, direct matches versus other-category alternatives explicit; the 34.3-minute difference is an estimate for different independent options |
| Mobile source expander and map | Operator description/hours references and check date visible; three alternative markers plus origin rendered in Folium |
| Snapshot preservation | Both source JSONs and both metadata files byte-identical to the baseline |
| Enrichment | 8 evidenced field overrides on 6 existing POIs; 199 POIs, 81 hours fields, 6 descriptions; no new feature confirmations |
| `python -m scripts.verify_live_llm` | `not_attempted`, reason `credentials_missing`; no live OpenAI success claimed |

Real viewport checks used the running feature app, including the comparison
view. DOM measurements and visual inspection found no horizontal page overflow:

| Viewport (width × height) | Document/body scroll width | Layout and actual capture |
| --- | --- | --- |
| 390 × 844 | 390 / 390 | Stacked OFF/ON, full-width main actions, two-column quick buttons; [capture](images/mobile-390.jpg) |
| 430 × 932 | 430 / 430 | Stacked comparison and wrapped text; [capture](images/mobile-430.jpg) |
| 768 × 1024 | 768 / 768 | Two comparison columns; [capture](images/tablet-768.jpg) |
| 1440 × 1000 | 1440 / 1440 | Two comparison columns and readable cards; [capture](images/desktop-1440.jpg) |

Expanded source details also measured 390/390 at a 390 px viewport. These are
actual local-browser JPEGs, not mockups, public-deployment captures, or native
device tests. Browser viewport overrides were reset after checking.

The weekly parser has regression coverage for days/ranges/lists, semicolon
replacement, multiple spans, overnight/week rollover, partial `off` subtraction,
arrival, full visit, exact closing boundaries, unsupported whole expressions,
source evidence and timezone conversion. Unknown schedules stay unknown. No
live opening or safe route is asserted.

GitHub Actions remains unchanged and checks Python 3.11 and 3.13 on the PR.
Consult the PR's checks for its exact published revision; successful historical
main checks do not prove the feature revision passed.

**Deployment was unverified at the original audit checkpoint.** The user reported signing into Streamlit
through Google in another browser; the available embedded session did not gain
that session. A new embedded tab's authentication reached a GitHub HTTP 500
page, and the authentication tabs were subsequently closed. No public app URL
was opened or verified at that checkpoint. The later successful public check
above supersedes this status; the authentication failure remains historical.

## Original MVP baseline — commit `fe40dcd`

The following results were executed for the original MVP on 19 October 2026.

Local environment: Windows, Python 3.13.7, isolated `.venv`, dependencies installed
from the pinned root `requirements.txt`. No OpenAI API key was needed or used.

### Automated and local runtime results

| Check actually executed | Result |
| --- | --- |
| `python -m pytest -q` | 74 passed; offline unit, integration and Streamlit AppTest checks |
| `python -m pip check` | No broken requirements |
| `python -m compileall -q app.py config.py core ingestion` | Passed |
| `python -m ingestion.build_database --offline` | Successful genuine snapshot rebuild (data pipeline verification) |
| `python -m ingestion.build_database --offline --db artifacts/offline-check.db` | 199 usable records; SQLite integrity `ok`; no HTTP |
| `python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501` | Server started successfully |
| GET `http://127.0.0.1:8501/_stcore/health` | HTTP 200, body `ok` |
| Browser: local startup and recommendation button | Real counts, three grounded cards, no-key mode, independent simulation labels, source/search links and Folium map rendered |
| Default UI startup and recommendation with network functions blocked | Passed; deterministic cards; SQLite bytes unchanged |
| UI control change | Previous cards hidden until recomputed |
| Airport flight UI | No excursion recommended |
| Snapshot/manifest integrity | 199 unique genuine OSM records; source links and coordinates valid; hashes matched |
| Credential pattern scan of publishable source/docs/snapshots | No key/token/private-key pattern findings; scan reports filenames only |
| Git ignore probes | `.env` variants, Streamlit secrets, venv, caches, private data, exact raw sources and artifacts excluded |

Tests cover typed OSM keys and geometry validation; duplicate-free rebuilds;
evidenced overrides; finite retry behavior; time budgets; strict unknown outlet
handling; raw/unknown hours; unconditional `closed`/`off` and inactive lifecycle
exclusion; weather failure and cache; actual Shield behavior; clock simulation;
airport deadline; no-key/provider-timeout/malformed-output fallbacks; LLM ID
and unsupported-fact validation; and application/database integration.

The app's displayed times are estimates for independent options. Climate
comparison tests demonstrate changed ranking/filtering on suitable data, not a
guaranteed reduction for every request. All genuine records currently have
unknown outlet availability, so strict outlet requests correctly return empty.

### Live external checks

- **OSM:** four official map API requests succeeded, yielding the documented
  sanitized small-area snapshot. Full bounded Overpass attempts failed; no
  successful full-city ingestion is claimed. See `DATA_PROVENANCE.md`.
- **Open-Meteo:** a real current-weather request succeeded during local
  verification. Returned observation time: `2026-10-19T15:30:00+05:00`, source
  `Open-Meteo`, prototype classification `normal`. This historical test result
  is not a claim about future/current conditions when you read this document.
- **2GIS:** the generated encoded search for `Байтерек Астана` opened in a
  browser with that search heading and multiple results. This validates search
  URL format, not identity of a particular business. No directory data was
  copied into the project.
- **OpenAI:** no live paid request was made. Timeout, malformed output, refusal,
  invalid IDs and unsupported assertions are covered with offline mocks;
  missing key uses templates.
- **GitHub:** authenticated repository write permissions were available. The
  original README-only history was preserved; changes use normal commits and
  fast-forward pushes. See the repository commit history and Actions for the
  published revision and its remote checks.
- **Streamlit Cloud:** the available session shows a sign-in page. Deployment
  has not been performed or verified, and there is no verified public URL.
  Account-owner actions are listed in `DEPLOYMENT.md`.

Browser evidence is saved locally as ignored `artifacts/local-smoke.jpg`; it is
not a public deployment screenshot. The five real-snapshot demonstration cases
and their measured observations appear in `TEST_SCENARIOS.md`.
