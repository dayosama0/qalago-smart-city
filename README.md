# QalaGo

**[Open the public QalaGo demo](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/)**

**Weather-aware Urban Guide for Astana**

Choose a public starting point, interests and a time budget. QalaGo retrieves
real OpenStreetMap places, checks estimated travel and supported visiting hours,
and separates direct category matches from other-category alternatives.

**199 real POIs in four demo zones · no API key required.** Climate Shield
compares two calculations with the same clock and weather. Outdoor minutes are
estimates for different options; a likely-indoor category does not confirm
shelter or safety. Cards are independent choices, not a combined itinerary.

**Reviewed application:** [`a453712`](https://github.com/dayosama0/qalago-smart-city/tree/a4537120335ce15c8b3b6c445a4f72f222b66c50).
A clean checkout passed **236 tests** and a [15-case automated evaluation](evaluation/release-a453712/report.md).
Its 9/15 category-coverage proxy is not human relevance; independent human
ratings remain blank. Optional live LLM verification is blocked by a recorded
API credit error; template mode works. No AI quality improvement is claimed.

**Demo version:** the public link above is the existing PR #1 preview, whose
source branch was checked at `348b6a4`, including 23:00. Cloud's exact build SHA
was not exposed. Google Maps walking links and the newer LLM safeguards in
`a453712` are reviewed functionality awaiting merge and a new main deployment.

[Evidence matrix](EVALUATION.md) · [Final review](docs/FINAL_RELEASE_REVIEW.md) ·
[Two-minute recording script](docs/DEMO_SCRIPT.md) · [Owner release steps](docs/RELEASE_CHECKLIST.md)

**Repository:** [dayosama0/qalago-smart-city](https://github.com/dayosama0/qalago-smart-city).

## Run locally

Tested Python versions: **3.11 and 3.13**; the clean local run used 3.13.7. All commands run from the repository root.

```bash
git clone https://github.com/dayosama0/qalago-smart-city.git
cd qalago-smart-city
git switch --detach a4537120335ce15c8b3b6c445a4f72f222b66c50
python -m venv .venv
```

The checkout above selects the exact reviewed application while the PRs remain
unmerged. After the owner completes release, use the separately verified main
SHA recorded for that deployment; cloning the current default main alone still
selects the older MVP.

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Then install and start:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open [localhost:8501](http://localhost:8501). The committed public SQLite snapshot is used immediately. No ingestion command or API key is required. Default weather is **simulated clear**, visibly labeled. The recommendations and controls work without a network connection; map tiles and external source/search links still require internet.

If PowerShell activation is disabled, run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m streamlit run app.py` directly.

## Optional settings

Copy `.env.example` to `.env` locally. Empty `OPENAI_API_KEY` keeps deterministic explanations. `OPENAI_MODEL` defaults to `gpt-4.1-mini`; any configured model must support the structured output used by the client. API errors, refusals and invalid output fall back to the same selected, source-backed places. No paid API call is required for the demo.

Source-backed descriptions (up to 480 characters) and their public attribution
URLs are supplied as untrusted factual context. The model can select a safe
phrase or one complete source sentence allowed for that exact POI; novel
paraphrases, unsupported properties and wrong IDs fail validation and use
templates. This deliberately limits generation, does not independently verify
the source, and does not change POI selection/ranking. No improvement in human
relevance has been measured. These LLM changes belong to the new review branch.

To explicitly verify one real retrieval → LLM → validation call after providing your own key, run `python -m scripts.verify_live_llm`. It records a credential-free report under ignored `artifacts/` and succeeds only when the backend returns validated `answer_mode=llm`. Without credentials it reports `not_attempted`; template fallback is not a successful live LLM check. Comparison deliberately uses templates to isolate Shield's effect.

The verification command accepts the official OpenAI endpoint only. A custom
`OPENAI_BASE_URL` is rejected without a request and is never printed; a proxy
response cannot establish a genuine OpenAI verification.

Latest credentialed check, **19 October 2026**: the official API returned
**429 / `credit_balance_exhausted`**; the app used templates and live LLM success
remains **unverified**. See the [sanitized actual report](docs/live-llm-verification.json).
The API organization owner needs to check its balance, then rerun the command;
do not interpret fallback or passing offline tests as model success. The
[official billing guide](https://help.openai.com/en/articles/8264644-what-is-prepaid-billing)
explains how to restore API credits.

`WEATHER_ENABLED=0` disables live weather requests. Otherwise, the live selector requests current Open-Meteo conditions with finite timeouts and a short memory cache. Handled request/value failures produce **unknown**, never fabricated clear weather. A known malformed-unit payload can still abort live selection; see the nonblocking weather finding in [final review](docs/FINAL_RELEASE_REVIEW.md). Use explicit simulations for the controlled demo. `OVERPASS_URL` changes the ingestion endpoint only.

On Streamlit Cloud use **Advanced settings → Secrets**, not a committed file. `.env`, `.streamlit/secrets.toml`, environments, caches, logs, original raw responses and private data are ignored by Git. No keys or private user positions belong in this repository.

## Controls and honest results

- Start at EXPO / MEGA Silk Way, Baiterek, Central Park, airport NQZ or manually entered coordinates. GPS is never requested.
- Choose 30, 60 or 120 minutes, interests, a free-text request and optional return trip. Each option must fit estimated travel + visit + a reserve.
- Confirmed outlets are a strict requirement: unknown does not mean yes. Sparse evidence can produce zero cards.
- Toggle Climate Shield, or run the comparison view, with the same simulated wind/rain/cold scenario. Comparison captures one clock instant and one weather observation for both calculations, uses deterministic explanations, and never reports an empty result as a zero-minute improvement. Weather thresholds are prototype heuristics, not official alerts.
- Simulate local time separately from weather. Clock mode and weather mode are independently labeled; current weather is not a forecast for the simulated clock.
- Airport + flight deadline returns a conservative explanation without a city-center excursion. The app does not calculate security, boarding or gate access.
- Cards show approximate distance, walking/visit estimates, uncertainty, OSM source and **Найти в 2ГИС**. That link opens a name-and-city search; it is not a guaranteed organization match. QalaGo does not scrape or retain 2GIS data.
- **Пеший путь · Google Maps** opens external walking navigation between the selected public preset and POI. A manually entered origin requires separate permission before its link is created; permission resets when the origin changes. Opening the link sends both coordinates to Google Maps. OSM points may be building centers, not entrances; QalaGo does not verify the external route or its safety. This feature is currently under review and is not part of the verified public demo.

Common listed schedules are checked against estimated arrival and the whole visit in `Asia/Almaty`. Results distinguish **listed as open** from **unknown**; listed-closed visits are excluded. The full original schedule remains visible. Unsupported expressions (including public holidays, solar times or conditions) remain unknown, and nothing is labeled live-confirmed open. See [supported grammar and limits](docs/OPENING_HOURS.md).

Indoor status distinguishes explicit OSM evidence, a category-based inference and unknown. A likely indoor category is not proof of heating, shelter, sockets, Wi-Fi or accessibility. `unusual` is a broad cultural/landmark interest, not a synonym for architecture or evidence of an unusual experience.

## Data and reproducible ingestion

Only genuine OSM records are served by the app. The bundled snapshot contains **199 named POIs, 81 listed schedules and 6 sourced descriptions**. Eight referenced field overrides enrich six existing places; they are public-source desk research, not site visits or live availability checks. Synthetic data is confined to `tests/fixtures` and test code. See [data provenance and snapshot validation](docs/DATA_PROVENANCE.md), [enrichment evidence](docs/POI_ENRICHMENT.md), and [dataset license](data/LICENSE.md).

```bash
# Refresh through two bounded Overpass queries (main Astana and NQZ).
python -m ingestion.build_database

# Rebuild from committed genuine sanitized snapshots, without network.
python -m ingestion.build_database --offline
```

The live ingestion command uses finite timeouts and limited retries. Network failure is actionable and never triggers fake data. Original successful source responses stay under ignored `data/raw/`; sanitized distributable snapshots retain provenance under `data/snapshots/`. The bundled snapshot has limited geographic coverage around four public presets because full Overpass requests were unavailable. Consult its provenance before presenting coverage claims.

The database is read-only during normal app use. Stable typed OSM IDs prevent duplicate rows on repeated ingestion. Node coordinates and approximate way/relation centers are distinguished by source; a center may not be an entrance. Field overrides require a whitelisted field, evidence URL and check date; unmatched IDs cannot silently receive overrides.

**© OpenStreetMap contributors.** The OSM database and derived snapshot are provided under [ODbL 1.0](https://www.openstreetmap.org/copyright); preserve attribution and comply with the database's share-alike requirements when redistributing derivatives. A structurally validated source record is not an on-site inspection. No government or 2GIS partnership is claimed.

## Architecture

`OSM → validation/normalization → SQLite → SQL bounding box + Haversine → time/access/feature filters → Climate Shield + ranking → optional grounded explanation → cards + map`.

This is **structured retrieval with an optional retrieval-augmented explanation path**: SQL and geometry select the POIs, and the optional LLM selects allowed phrases or source sentences for those IDs. Verified successful runs use templates; a successful live LLM response and an AI relevance gain have not been established. Embeddings and a vector index are absent. Straight-line distance is converted to estimated walking time with `distance_km × 1.3 / 4.5 × 60`; roads, barriers, crossings and access are not modeled. Cards are alternatives, so their times must not be summed as an itinerary.

```text
app.py                         Streamlit entrypoint
config.py, core/models.py      Shared public configuration and contract
core/                         Retrieval, weather, ranking, templates, optional LLM
ingestion/                    Collection, normalization and repeatable SQLite build
data/pois.db                  Genuine redistributable snapshot
data/snapshots/                Sanitized genuine source records + metadata
tests/                        Offline unit, integration and UI checks
.streamlit/config.toml        Public Cloud-compatible configuration
.github/workflows/tests.yml   Offline checks on main pushes / pull requests
docs/                         Provenance, deployment, privacy and demo material
```

## Verification

The [clean committed 15-query evaluation](evaluation/release-a453712/report.md) uses genuine
POIs, fixed clocks and simulated weather with network disabled. Its prompts
are authored representative examples, not collected user requests. Observed
direct-category coverage is **9/15** and **39/39** returned cards fit independently
recomputed estimated budgets. These are automated proxies, not human relevance
or proof of zero hallucinations; **18** cards retain unknown schedules. Two
independent human reviews are still pending. See the [protocol and blank forms](docs/EVALUATION_PROTOCOL.md).

The release run records commit `a4537120335ce15c8b3b6c445a4f72f222b66c50`
and `working_tree_dirty=false`, with dataset/code hashes in its JSON. Earlier
working-tree runs under `evaluation/results/` remain historical evidence and
their original blank human forms are preserved.

```bash
python -m pytest -q
python -m ingestion.build_database --offline
python -m streamlit run app.py --server.headless true
```

Actual execution results and manual checks are recorded in [verification report](docs/VERIFICATION.md). Tests use synthetic fixtures, mocked weather/LLM failures and real-snapshot integrity checks; they need no API key. The local startup check also requests `/_stcore/health` and exercises the UI. A running local server does not establish a public deployment.

## Publish and update

For a new deployment, choose `dayosama0/qalago-smart-city`, entrypoint **app.py**, and the reviewed branch you intend to host. Python **3.13** is locally tested; the default template app needs no secrets. Follow [deployment and verification steps](docs/DEPLOYMENT.md).

The public app's source button points to [`codex/audit-product-improvements/app.py`](https://github.com/dayosama0/qalago-smart-city/blob/codex/audit-product-improvements/app.py), identifying the deployed source branch. The audit PR is still unmerged and `main` remains at `fe40dcd`. Community Cloud updates the **configured branch**, so this deployment follows feature-branch pushes. For automatic updates from future `main` pushes, deploy an app from `main` after PR review/merge; changing the existing app's branch requires redeployment. Changes to `requirements.txt` trigger dependency installation. See [official Streamlit update behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app) and [branch migration](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app).

The exact deployed build SHA, Cloud Python setting and secrets remain uninspected. A visible template response does not establish whether Cloud secrets are configured.

GitHub Actions tests and Cloud deployment are independent. No branch-protection gate is assumed. Review a change and its passing checks before merging; never force-push existing branches. Refresh datasets locally and commit only reviewed public data, not user state or secrets. SQLite edits on Cloud are ephemeral and are not an ingestion or persistence strategy.

## Demo and limitations

See [two-minute demo and seven-slide outline](docs/DEMO_SCRIPT.md), [five acceptance scenarios](docs/TEST_SCENARIOS.md), [privacy and ethics](docs/PRIVACY_ETHICS.md), [architecture](docs/ARCHITECTURE.md), and the [original MVP specification](docs/development/CODEX_QALAGO_SPEC.md).

OSM coverage can be incomplete or stale. Quietness, unusual experiences, current opening, prices, accessibility, heating and availability are not guaranteed. Night mode adds uncertainty and caution, not invented events. Weather is contextual information, not an emergency service. No turn-by-turn route, multi-stop optimizer, GPS tracking, authentication, user history or analytics backend is included.
