# QalaGo — submission evidence

Application reviewed: [`a4537120335ce15c8b3b6c445a4f72f222b66c50`](https://github.com/dayosama0/qalago-smart-city/tree/a4537120335ce15c8b3b6c445a4f72f222b66c50), 19 October 2026.
The final documentation/report follow-up changes no application code.

The [existing public preview](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/) demonstrates the PR #1 branch checked at `348b6a4`, including 23:00. Its exact Cloud build SHA was not exposed. PR #2 navigation/LLM safeguards are reviewed code awaiting the authorized merge/main deployment sequence.

| Claim | Verified evidence | Scope and limit |
| --- | --- | --- |
| Starts without an API key | Complete clean-checkout suite: **236 passed in 29.56s**, including Streamlit AppTest and no-key integration | Windows / Python 3.13.7; provider calls disabled. [Final review](docs/FINAL_RELEASE_REVIEW.md) |
| CI for PR #1 | [Run 39247495213](https://github.com/dayosama0/qalago-smart-city/actions/runs/39247495213), head `348b6a4`; fetched logs show **153 passed** on Python 3.11 and 3.13 | Existing `main` base; not evidence of a future retargeted PR #2 integration |
| CI for PR #2 application | [Run 39254324101](https://github.com/dayosama0/qalago-smart-city/actions/runs/39254324101), head `a453712`; fetched logs show **236 passed** on both versions | Tested against its feature-branch base. Fresh CI is required after retargeting to main |
| Genuine public data | `data/pois.db`, manifest and [provenance](docs/DATA_PROVENANCE.md): **199 named OSM POIs**, 81 schedules, six sourced descriptions | Four small demo zones; structural/source checks, not whole-city coverage or on-site/live verification. ODbL attribution retained |
| Listed-hours and time budgets | `core/opening_hours.py`, retrieval and regression tests; [supported grammar](docs/OPENING_HOURS.md) | Selected time, arrival and whole visit checked for supported schedules; unsupported/missing hours remain unknown |
| Automated evaluation | [Clean committed run](evaluation/release-a453712/report.md), [raw JSON](evaluation/release-a453712/automated_results.json): **15/15 cases**, **9/15 direct-category coverage proxy**, **39/39 estimated budgets** | Authored representative prompts, not collected user requests. Four cases have alternatives only; two safely return empty; 18 returned schedules are unknown |
| Grounding/source fidelity | Clean run: **0 snapshot-field mismatches**, 39 canonical OSM links, no returned listed-closed card or strict-feature violation | Local checks use snapshot identity and the app's hours parser. No HTTP reachability, arbitrary prose truth or zero-hallucination proof |
| Human relevance | [Protocol](docs/EVALUATION_PROTOCOL.md) and original two independent blank forms preserved | **Not measured.** No participants, ratings or agreement statistics were generated |
| Retrieval-augmented explanation path | SQL/Haversine retrieval and deterministic filters/ranking, followed by optional `core/llm.py` source-sentence/allowed-phrase selection | No embeddings/vector index; model does not rank/select POIs. Successful verified runs use templates; AI quality improvement is unmeasured |
| Live LLM check | [Safe report](docs/live-llm-verification.json), recorded 19 October at 17:42 UTC+5: official API **429 / credit_balance_exhausted**, `not_verified`, `answer_mode=template` | Billing blocker to verification; neither a successful model call nor proof the implementation fails. No new API request in this final review |
| Climate Shield | Shared clock/weather comparison code, offline regressions and recorded public wind comparison: **35.0 vs 0.7 estimated outdoor minutes** | First options differ (NU Park / Mega Silk Way). Likely-indoor classification is inferred; no observed safety benefit, verified shelter or universal reduction percentage |
| Navigation and privacy | `core/links.py`, UI consent tests, prior browser walking-mode check | Google Maps computes the external route; QalaGo only supplies points. Manual start withheld until explicit consent; changing it resets permission. OSM center may not be an entrance |
| 2GIS | Encoded name-and-Astana search, prior browser check | Search only; no guaranteed business match, scraping, retained directory data or partnership |
| Responsive UI | [Actual captures and measurements](docs/VERIFICATION.md): local 390/430/768/1440 px; PR #2 navigation card 390/390 document/body width | Browser viewport checks, not physical-device certification; existing public preview has its own version-specific captures |
| Live-weather resilience | Request/value failures have unknown-weather handling; **known P2 malformed-unit response issue** in [final review](docs/FINAL_RELEASE_REVIEW.md) | `current_units: null` can abort selection. The controlled submission demo uses labeled simulations; blanket failure-resilience claims are withheld |
| Main release | [Merge sequence](docs/RELEASE_CHECKLIST.md), [new-main smoke checklist](docs/MAIN_DEPLOY_SMOKE.md) | No merge, retarget, deletion, force-push or deployment setting change performed; new main deployment remains owner work |

Dataset SHA-256: `b7f26c59fac6ce5868e8dec1ee406d185b4a5656f20cbafaee975294066b8ab4`.
Normalized backend/config/evaluator/case fingerprint: `119b60c4496fff6c89a18a2b0bfc8336d3591cd2e3e25dec0f44a534eba1c9fa`.
The clean run records the actual full commit above and `working_tree_dirty=false`; earlier dirty runs remain historical under `evaluation/results/`.

Use [the two-minute script](docs/DEMO_SCRIPT.md) with a revision label. Do not attach new-feature claims to the older preview, infer human relevance from category coverage, or describe local tests as proof of a deployed main build.
