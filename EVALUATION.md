# QalaGo — evidence for reviewers

This matrix links claims to inspectable code and executed checks. It does not
predict selection results. Public deployment and live OpenAI use require their
own successful checks; neither follows from the presence of integration code.

The [public QalaGo app](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/) was independently exercised in a signed-out browser on **19 October 2026**. Runtime observations and public screenshots are recorded in [verification](docs/VERIFICATION.md). A credentialed official OpenAI check returned HTTP 429 / `credit_balance_exhausted`; [actual report](docs/live-llm-verification.json). Live LLM success remains unverified; template fallback worked.

Public evidence demonstrates the PR #1 branch at
[`348b6a4`](https://github.com/dayosama0/qalago-smart-city/tree/348b6a4802556f304269d5234bff3009d5bd7f83),
including 23:00; Cloud's exact build SHA was not exposed. Navigation and tighter
LLM context/validation in `codex/submission-readiness` are local review work,
not yet public features. The [release checklist](docs/RELEASE_CHECKLIST.md)
separates review, merging and deployment.

[Actual automated results for 15 authored representative queries](evaluation/results/report.md):
9/15 direct-category coverage proxy, 39/39 cards within independently recomputed
estimated budgets, 0 snapshot-field mismatches and 18 unknown schedules. Four
cases have only alternatives; two correctly return empty. These measurements
do not establish human relevance or count unsupported prose assertions.
[Two independent human ratings](docs/EVALUATION_PROTOCOL.md) remain uncollected;
their provided forms are blank.

| Requirement | Implementation / evidence | What it establishes |
| --- | --- | --- |
| Runnable prototype without secrets | `app.py`, `requirements.txt`, `tests/test_cloud.py`, [public runtime evidence](docs/VERIFICATION.md) | Local no-key tests; public HTTP 200, 199 POIs and three default template cards. Cloud secrets configuration was not inspected |
| Genuine public places | `data/pois.db`, `data/pois.manifest.json`, `data/snapshots/`, [provenance](docs/DATA_PROVENANCE.md) | 199 named OSM POIs in four small demo zones, not full-city coverage |
| Repeatable ingestion | `ingestion/`, `tests/test_ingestion.py` | Bounded collection, stable IDs, validation, offline rebuild, genuine OSM API fallback history |
| Time-aware selection | `core/opening_hours.py`, `tests/test_opening_hours.py`, [grammar](docs/OPENING_HOURS.md) | Common listed schedules checked for arrival and visit; unsupported schedules unknown; no live opening confirmation |
| Relevant recommendations | `core/retrieval.py`, `core/recommend.py`, backend regressions | Direct category matches separated from other-category alternatives; unusual has its own broad cultural taxonomy |
| Climate Shield | `core/ranking.py`, `core/comparison.py`, `tests/test_comparison.py`, public comparison in verification | Shared weather/clock; public wind run showed first-option estimates of 35.0 minutes OFF and 0.7 ON. These are estimates for different alternatives, not a guaranteed improvement |
| Five reproducible contexts | [Scenario settings and observations](docs/TEST_SCENARIOS.md), quick buttons in `app.py` | Real engine calls for ordinary, child, weather, strict-feature and flight use cases |
| Structured RAG and optional generation | SQL/Haversine retrieval → filters → `core/llm.py` → ID/text validation | Code and offline provider-failure tests; live LLM success is only established if recorded in verification |
| Hallucination resistance | `tests/test_recommend.py` | Wrong IDs, malformed output, refusals and unsupported facts fall back to source-backed cards |
| Sourced enrichment | `data/manual_overrides.csv`, [field evidence](docs/POI_ENRICHMENT.md) | Only referenced fields are changed; no invented feature confirmations or on-site checks |
| Responsive usability | `app.py`, `tests/test_ui.py`, browser measurements and captures in verification | Local 390/430/768/1440 px checks; public 390/1440 px checks with document/body width matching the viewport |
| Privacy | [Privacy/ethics](docs/PRIVACY_ETHICS.md), `.gitignore`, readonly DB checks | Manual origin, no GPS request or stored user history, optional third-party disclosures |
| Reliability | [GitHub Actions](https://github.com/dayosama0/qalago-smart-city/actions), `tests/` | Check the run for the PR revision; historic green main is not proof that new changes passed |
| Deployment | [Verified public app](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/), [public source link](https://github.com/dayosama0/qalago-smart-city/blob/codex/audit-product-improvements/app.py), [evidence](docs/VERIFICATION.md) | Public runtime verified; source button identifies `codex/audit-product-improvements`. The PR is unmerged; exact build SHA, Cloud Python setting and secrets remain uninspected |
| Walking navigation (review branch) | `core/links.py`, `tests/test_navigation.py`, UI consent regressions | Google Maps URL format and browser walking mode checked between public points; custom precise origin withheld until explicit consent; route/entrance access is not verified |
| Source-aware LLM context (review branch) | `core/llm.py`, `tests/test_llm_grounding.py` | Bounded attributed description supplied as untrusted data; per-POI allowed text prevents novel prose/reassigned facts; benign paraphrases can also fall back |

Use [the submission checklist](docs/SUBMISSION_CHECKLIST.md) before sharing.
Comparison output is a model estimate for independent alternatives, not a safe
route guarantee. Unknown schedules and missing features remain visible.
