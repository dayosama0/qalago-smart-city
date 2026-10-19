# QalaGo verification history

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

**Deployment remains unverified.** The user reported signing into Streamlit
through Google in another browser; the available embedded session did not gain
that session. A new embedded tab's authentication reached a GitHub HTTP 500
page, and the authentication tabs were subsequently closed. No public app URL
was opened or verified in this audit. Use `DEPLOYMENT.md` from an authenticated
ordinary browser; account access cannot be inferred from GitHub Git/MCP access.

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
