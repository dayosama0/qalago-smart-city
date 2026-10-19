# QalaGo — evidence for reviewers

This matrix links claims to inspectable code and executed checks. It does not
predict selection results. Public deployment and live OpenAI use require their
own successful checks; neither follows from the presence of integration code.

| Requirement | Implementation / evidence | What it establishes |
| --- | --- | --- |
| Runnable prototype without secrets | `app.py`, `requirements.txt`, `tests/test_cloud.py`, [verification](docs/VERIFICATION.md) | Local and automated startup, grounded template mode; public status separately recorded |
| Genuine public places | `data/pois.db`, `data/pois.manifest.json`, `data/snapshots/`, [provenance](docs/DATA_PROVENANCE.md) | 199 named OSM POIs in four small demo zones, not full-city coverage |
| Repeatable ingestion | `ingestion/`, `tests/test_ingestion.py` | Bounded collection, stable IDs, validation, offline rebuild, genuine OSM API fallback history |
| Time-aware selection | `core/opening_hours.py`, `tests/test_opening_hours.py`, [grammar](docs/OPENING_HOURS.md) | Common listed schedules checked for arrival and visit; unsupported schedules unknown; no live opening confirmation |
| Relevant recommendations | `core/retrieval.py`, `core/recommend.py`, backend regressions | Direct category matches separated from other-category alternatives; unusual has its own broad cultural taxonomy |
| Climate Shield | `core/ranking.py`, `core/comparison.py`, `tests/test_comparison.py` | Two real calculations share weather and clock; changed, unchanged and empty outcomes are handled honestly |
| Five reproducible contexts | [Scenario settings and observations](docs/TEST_SCENARIOS.md), quick buttons in `app.py` | Real engine calls for ordinary, child, weather, strict-feature and flight use cases |
| Structured RAG and optional generation | SQL/Haversine retrieval → filters → `core/llm.py` → ID/text validation | Code and offline provider-failure tests; live LLM success is only established if recorded in verification |
| Hallucination resistance | `tests/test_recommend.py` | Wrong IDs, malformed output, refusals and unsupported facts fall back to source-backed cards |
| Sourced enrichment | `data/manual_overrides.csv`, [field evidence](docs/POI_ENRICHMENT.md) | Only referenced fields are changed; no invented feature confirmations or on-site checks |
| Responsive usability | `app.py`, `tests/test_ui.py`, browser measurements in verification | Quick scenarios, readable cards, accessible uncertainty and measured viewport checks |
| Privacy | [Privacy/ethics](docs/PRIVACY_ETHICS.md), `.gitignore`, readonly DB checks | Manual origin, no GPS request or stored user history, optional third-party disclosures |
| Reliability | [GitHub Actions](https://github.com/dayosama0/qalago-smart-city/actions), `tests/` | Check the run for the PR revision; historic green main is not proof that new changes passed |
| Deployment | [Exact deployment steps and status](docs/DEPLOYMENT.md) | GitHub source, branch, entrypoint and verification requirements; no assumed public URL |

Use [the submission checklist](docs/SUBMISSION_CHECKLIST.md) before sharing.
Comparison output is a model estimate for independent alternatives, not a safe
route guarantee. Unknown schedules and missing features remain visible.
