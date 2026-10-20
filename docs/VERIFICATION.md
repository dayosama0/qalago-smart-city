# Executed verification — 19 October 2026

Local environment: Windows, Python 3.13.7, isolated `.venv`, dependencies installed
from the pinned root `requirements.txt`. No OpenAI API key was needed or used.

## Automated and local runtime results

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

## Live external checks

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

## Latest-main local check — 20 October 2026

The 19 October sections above are preserved as historical results. Their
199-place database, OpenAI integration and deployment-access observations do
not describe the current main revision.

| Check or observed state | Actual result |
| --- | --- |
| Source checked | Main revision `c8ac0d6`, isolated checkout on `codex/main-deployment-refresh` |
| Local runtime | Python 3.13.7; Streamlit started at `http://127.0.0.1:8503` |
| Local health | GET `http://127.0.0.1:8503/_stcore/health` returned HTTP 200 |
| Complete automated suite | **166 passed in 16.73 seconds**, including existing Streamlit AppTests; `python -m pytest -q -p no:cacheprovider` using the existing repository venv |
| SQLite snapshot | **207 POIs, 207 descriptions, 144 schedules and 5 closure markers**; 149 nonempty hours fields when markers are included |
| Database SHA-256 | `b27a70a3ffb1bbc2ddb05568e6325779355c9da9658dd1bc0f3d9176e074b49a` |
| Groq credentials/live service | No local Groq key was available. No successful live Groq request is claimed; default AI search requires a key, and rules-based reserve mode requires separate explicit opt-in |
| New manual browser smoke | Not completed: the built-in computer-use policy blocked native Chrome control because its active URL could not be determined |
| Cloud work in this session | No deployment or source-setting change performed; current authentication state was not established |
| Owner's deployment report | Owner says a teammate deployed an app. Its latest-main URL was not supplied or independently verified; the older public preview still shows 199 places |

For the automated run, `GROQ_API_KEY`, `OPENAI_API_KEY`, `OPENAI_ADMIN_KEY` and
`OPENAI_BASE_URL` were cleared; `WEATHER_ENABLED=0` and
`PYTHONDONTWRITEBYTECODE=1` were set. The worktree had no `.env` during testing.
After the tests, a blank ignored local `.env` was created from the example for
setup convenience; it contains no Groq key. App startup loads only its own
checkout's `.env`, not configuration from the older root checkout.

The local server health response and AppTests do not establish manual browser
behavior, live AI success or public deployment of main. Deployment may already
exist as the owner reports; the required next evidence is its actual URL,
source settings and signed-out smoke results. See the exact machine-readable
[dated check](deployment-check-2026-10-20.json) and
[account-owner deployment steps](DEPLOYMENT.md).


## Subsequent live Groq verification — 20 October 2026, 17:57 UTC

After the owner supplied a key in the ignored local `.env`, the port-8503
server was restarted and its health endpoint again returned `ok`. The new
local interface was opened in the browser. No key was displayed or committed.

Two searches were executed against the real fixed Groq endpoint with the
`openai/gpt-oss-20b` model and fallback disabled. The first EXPO/architecture
search received HTTP 200 for planning but had no matching candidates, so it
did not establish the selection path. A broad Baiterek search with fixed
14:00 local time and clear simulated weather then received HTTP 200 for
both planning and selection and returned **three recommendations in `llm`
mode**. There were three provider HTTP requests in total, with no automatic
retry. Snapshot membership, unique IDs, the three-card limit, estimated
budgets and absence of listed-closed returned cards passed the recorded
checks. These are bounded checks, not human relevance or generated-prose
factuality measurements. No further API requests were made for this record.

See [the credential-safe report](live-groq-verification.json), including both
attempts, exact application/checkout SHAs, dataset hash and HTTP status codes.
Raw prompts, responses, exception text, headers and credentials are excluded.
The earlier 17:49 local-test record remains historical and unchanged.

Native Chrome automation was again stopped by its policy check because it
could not determine the current browser URL confidently. No Cloud deployment
or public main verification is claimed. The published URL/source settings
and signed-out Cloud checks remain required.
