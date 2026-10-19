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
