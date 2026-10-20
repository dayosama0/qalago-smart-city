# QalaGo — Умные прогулки по Астане

Weather-aware urban guide for Astana: choose a public starting point, interests and available time, then receive up to three AI-selected places from the local database. Climate Shield changes filtering and ranking in adverse weather. Each card is an independent option, not a combined route.

**Repository:** [dayosama0/qalago-smart-city](https://github.com/dayosama0/qalago-smart-city).
**Public deployment:** https://applago-smart-city-zqz3zanh7aq62duqh6wezj.streamlit.app/.
**Video Demonstration** https://github.com/dayosama0/qalago-smart-city/releases/tag/demonstration.

## Run locally

Python 3.11+; local verification uses Python 3.13. All commands run from the repository root.

```bash
git clone https://github.com/dayosama0/qalago-smart-city.git
cd qalago-smart-city
python -m venv .venv
```

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

Open [localhost:8501](http://localhost:8501). The committed public SQLite snapshot is used immediately. No ingestion command is required. Set GROQ_API_KEY in your local .env or Streamlit secrets to use the main AI search. Default weather is **current Open-Meteo conditions**, falling back to unknown when unavailable. The explicitly enabled reserve mode and controls also work offline; map tiles and external source/search links require internet. Weather simulations are optional advanced controls, visibly labeled when selected.

If PowerShell activation is disabled, run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m streamlit run app.py` directly.

## Groq API settings

The search supports **groups of up to five people**, with individual preferences balanced against shared requirements. AI descriptions can use **Russian, Kazakh or English**, with automatic language selection from the query. The **Только открытые по расписанию** filter excludes unknown hours and places that will close before the visit ends, including in reserve mode. See [three demo scenarios and the incomplete-data policy](docs/USER_SCENARIOS.md). Interface labels and reserve-mode editorial descriptions are not translated.

Create a local `.env` containing `GROQ_API_KEY=your-key`. `GROQ_MODEL` defaults to `openai/gpt-oss-20b`; any configured model must support strict JSON-schema structured outputs on Groq. Requests use HTTPS via the existing `requests` dependency with a fixed Groq endpoint (`https://api.groq.com/openai/v1`); no requests are sent to OpenAI. The Groq model first interprets the request (mandatory category, coffee shop requirement, maximum average check, available time). Python enforces those requirements together with distance, travel time and weather. The Groq model then selects up to three candidates from a bounded shortlist of at most 12 candidates and writes individual explanations. Unknown or repeated IDs are rejected.

API failures show an explicit error. The advanced **Разрешить резервный режим без ИИ (не рекомендуется)** checkbox is off by default; enabling it permits a clearly labeled rules-based fallback with up to 20 results. Search text, interests and candidate information are sent to Groq; origin coordinates are not included as separate fields. Do not enter private information in the search text.

Coffee-shop filtering requires an explicit `cuisine=coffee_shop` or `cafe=coffee_shop` tag and excludes generic cafes and restaurants. A maximum average check requires numeric KZT evidence in `average_check:kzt` or `average_check_kzt`. Five reviewed coffee-shop branches now have directory-listed average checks; missing prices remain unknown. These are average bills, not guaranteed prices for a particular order.

Create a key at [Groq Console](https://console.groq.com/keys), add it to the local `.env`, and restart Streamlit:

```dotenv
GROQ_API_KEY=your-groq-key
GROQ_MODEL=openai/gpt-oss-20b
```

The previous `OPENAI_API_KEY` and `OPENAI_MODEL` are ignored. The `openai/` prefix in the model ID names an open-weight model served by Groq. Free-plan quotas still apply; see [Groq limits](https://console.groq.com/docs/rate-limits). Automatic retries are disabled to avoid repeating failed requests automatically. Responses are validated locally after strict schema generation, including selected IDs and length limits. No live API calls run in tests.

`WEATHER_ENABLED=0` disables live weather requests. Otherwise, the live selector requests current Open-Meteo conditions with finite timeouts and a short memory cache. An unavailable or invalid response is labeled **unknown**, never silently replaced by clear weather. `OVERPASS_URL` changes the ingestion endpoint only.

On Streamlit Cloud use **Advanced settings → Secrets**, not a committed file. `.env`, `.streamlit/secrets.toml`, environments, caches, logs, original raw responses and private data are ignored by Git. No keys or private user positions belong in this repository.

## Controls and honest results

- Start at EXPO / MEGA Silk Way, Baiterek, Central Park, airport NQZ or manually entered coordinates. GPS is never requested.
- Choose 15, 30, 45, 60, 90 or 120 minutes, or enter a custom 1–480 minute budget, interests, a free-text request and optional return trip. Each option must fit estimated travel + visit + a reserve.
- Confirmed outlets are a strict requirement: unknown does not mean yes. Sparse evidence can produce zero cards.
- Toggle Climate Shield with the same simulated wind/rain/cold scenario to compare actual ranking/filtering. Weather thresholds are prototype heuristics, not official alerts.
- Simulate local time separately from weather. Clock mode and weather mode are independently labeled; current weather is not a forecast for the simulated clock.
- Airport + flight deadline returns a conservative explanation without a city-center excursion. The app does not calculate security, boarding or gate access.
- Cards show approximate distance, walking/visit estimates, uncertainty, OSM source and **Найти в 2ГИС**. That link opens a name-and-city search; it is not a guaranteed organization match. Some hours were manually checked against public references, including official venue sites and directories; these sources are linked separately in card details.

Cards highlight opening hours and a schedule-based status at estimated arrival, including the full visit duration. Simple weekly schedules, breaks, overnight hours and 24/7 are supported; holiday, seasonal and other unsupported expressions remain unknown. AI search excludes places closed at arrival or closing during the visit; reserve mode marks them and places them last. Availability is not live-verified. AI explanations appear directly in the cards; source details are collapsed. Indoor status distinguishes explicit OSM evidence, a category-based inference and unknown. A likely indoor category is not proof of heating, shelter, sockets, Wi-Fi or accessibility.

The main search includes starting point, available time, interests and a visible free-text request. Advanced controls contain return trip, outlets, flight constraints, weather/time scenarios and the optional reserve mode. AI results show up to three cards with individual reasons and suggested actions. A collapsed map and card details provide source information. On small screens, card rows stack vertically.

Live clock mode refreshes schedule status every minute while preserving the AI explanations without new API calls; newly closed AI options are removed. Simulated clock mode remains fixed. Background photos of Astana appear in the side margins and fade to the page background toward the bottom; narrow screens hide them. Photo attribution and license links are available in the sidebar. Photos load from Wikimedia Commons and require internet.

## Data and reproducible ingestion

The bundled snapshot contains **207 unique named POIs, 144 listed schedules and 5 closure markers**: 197 deduplicated OSM places plus 10 reviewed additions from 2GIS and official venue pages. Sources and check dates are stored per field in `data/curated_places.json` and `data/manual_overrides.csv` and survive both offline and online rebuilds. Synthetic data is confined to tests. See [data provenance](docs/DATA_PROVENANCE.md), [the new places review](docs/DATA_EXPANSION_2026-10-20.md), [the hours review and remaining gaps](docs/OPENING_HOURS_REVIEW.md), and [source attribution](data/LICENSE.md).

Each POI also has a distinct short Russian editorial description, stored in `data/manual_overrides.csv` with an evidence URL and review date. 29 descriptions use additional web references; 170 use the existing OSM snapshot and geographic context. Texts appear below the card heading, with sources in collapsed details, and survive offline database rebuilds. They are not live availability checks or reviews.

```bash
# Refresh through two bounded Overpass queries (main Astana and NQZ).
python -m ingestion.build_database

# Rebuild from committed genuine sanitized snapshots, without network.
python -m ingestion.build_database --offline
```

The live ingestion command uses finite timeouts and limited retries. Network failure is actionable and never triggers fake data. Original successful source responses stay under ignored `data/raw/`; sanitized distributable snapshots retain provenance under `data/snapshots/`. The bundled snapshot has limited geographic coverage around four public presets because full Overpass requests were unavailable. Consult its provenance before presenting coverage claims.

The database is read-only during normal app use. Stable typed OSM IDs prevent duplicate rows on repeated ingestion. After field overrides, nearby same-category records with matching normalized names or language aliases are merged, including node/polygon duplicates such as MEGA Silk Way. Distinct distant branches are preserved. Node coordinates and approximate way/relation centers are distinguished by source; a center may not be an entrance. Field overrides require a whitelisted field, evidence URL and check date; unmatched IDs cannot silently receive overrides.

**© OpenStreetMap contributors.** The OSM database and derived snapshot are provided under [ODbL 1.0](https://www.openstreetmap.org/copyright); preserve attribution and comply with the database's share-alike requirements when redistributing derivatives. A structurally validated source record is not an on-site inspection. No government or 2GIS partnership is claimed.

## Architecture

`OSM → validation/normalization → SQLite → SQL bounding box + Haversine → time/access/feature filters → Climate Shield + ranking → AI selection + grounded explanations → cards + map`.

This is **structured RAG**, using SQL and deterministic geometry rather than embeddings or a vector database. Facts come from SQLite and calculations. LLM output is limited to database candidate IDs and explanatory text, then validated. Straight-line distance is converted to estimated walking time with `distance_km × 1.3 / 4.5 × 60`; roads, barriers, crossings and access are not modeled. Cards are alternatives, so their times must not be summed as an itinerary.

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

```bash
python -m pytest -q
python -m ingestion.build_database --offline
python -m streamlit run app.py --server.headless true
```

Actual execution results and manual checks are recorded in [verification report](docs/VERIFICATION.md). Tests use synthetic fixtures, mocked weather/LLM failures and real-snapshot integrity checks; they need no API key. The local startup check also requests `/_stcore/health` and exercises the UI. A running local server does not establish a public deployment.

## Publish and update

Deploy from `dayosama0/qalago-smart-city`, branch **main**, entrypoint **app.py**, Python **3.13**, with empty secrets for the default no-key app. Follow [deployment and verification steps](docs/DEPLOYMENT.md). After the first successful Cloud setup, future pushes to the configured `main` branch update the app automatically; dependency edits trigger installation. [Official Streamlit documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app) explains this behavior.

GitHub Actions tests and Cloud deployment are independent. No branch-protection gate is assumed. Review a change and its passing checks before merging; never force-push existing branches. Refresh datasets locally and commit only reviewed public data, not user state or secrets. SQLite edits on Cloud are ephemeral and are not an ingestion or persistence strategy.

## Demo and limitations

See [two-minute demo and seven-slide outline](docs/DEMO_SCRIPT.md), [five acceptance scenarios](docs/TEST_SCENARIOS.md), [privacy and ethics](docs/PRIVACY_ETHICS.md), [architecture](docs/ARCHITECTURE.md), and the [extended MVP specification](CODEX_QALAGO_SPEC.md).

OSM coverage can be incomplete or stale. Quietness, unusual experiences, current opening, prices, accessibility, heating and availability are not guaranteed. Night mode adds uncertainty and caution, not invented events. Weather is contextual information, not an emergency service. No turn-by-turn route, multi-stop optimizer, GPS tracking, authentication, user history or analytics backend is included.

Results can be sorted by recommendation, distance, total estimated time or name without repeating the search. Places closed at arrival or closing during the visit stay last in every order. Map numbering follows the displayed order.


## Recommendation writing style

The selection prompt lives in `core/prompts/place_selection.txt`. AI cards contain a newly written description, a separate reason tied to the user's situation, and a suggested activity. Stable general knowledge can supplement supplied facts; current prices, schedules, facilities and ambience must not be invented. Missing optional attributes are omitted rather than discussed. Text uses a neutral voice without first-person references or database/provider terminology. Distances remain separate UI metrics. Database attribution stays in the sidebar; generated descriptions have no editorial-source attribution attached.
