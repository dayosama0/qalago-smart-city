# Audit changes

Base: `fe40dcd`. Proposed on `codex/audit-product-improvements`; main is preserved.

Implemented: common listed-hours filtering, relevance/alternative separation, real Shield comparison, responsive quick scenarios, six sourced POI enrichments and reviewer evidence. No new runtime dependencies or commercial directory data were added.

Executed checks: 153 offline tests; local startup and health200; browser widths390/430/768/1440 without horizontal overflow. See [verification](../VERIFICATION.md) for measurements, screenshots and account-dependent limitations. Live OpenAI was not attempted because credentials were missing. Streamlit public deployment remains unverified after embedded authentication failed.

## Exact file changes

| Change | File |
| --- | --- |
| Added | `EVALUATION.md` |
| Updated | `README.md` |
| Updated | `app.py` |
| Added | `core/comparison.py` |
| Updated | `core/models.py` |
| Added | `core/opening_hours.py` |
| Updated | `core/recommend.py` |
| Updated | `core/retrieval.py` |
| Updated | `data/manual_overrides.csv` |
| Updated | `data/pois.db` |
| Updated | `data/pois.manifest.json` |
| Updated | `docs/ARCHITECTURE.md` |
| Updated | `docs/DATA_PROVENANCE.md` |
| Updated | `docs/DEMO_SCRIPT.md` |
| Updated | `docs/DEPLOYMENT.md` |
| Added | `docs/OPENING_HOURS.md` |
| Added | `docs/POI_ENRICHMENT.md` |
| Updated | `docs/PRIVACY_ETHICS.md` |
| Added | `docs/SUBMISSION_CHECKLIST.md` |
| Updated | `docs/TEST_SCENARIOS.md` |
| Updated | `docs/VERIFICATION.md` |
| Moved unchanged | `CODEX_QALAGO_SPEC.md` → `docs/development/CODEX_QALAGO_SPEC.md` |
| Added | `docs/images/desktop-1440.jpg` |
| Added | `docs/images/mobile-390.jpg` |
| Added | `docs/images/mobile-430.jpg` |
| Added | `docs/images/mobile-sources-390.jpg` |
| Added | `docs/images/tablet-768.jpg` |
| Added | `scripts/__init__.py` |
| Added | `scripts/verify_live_llm.py` |
| Updated | `tests/test_cloud.py` |
| Added | `tests/test_comparison.py` |
| Added | `tests/test_enrichment.py` |
| Added | `tests/test_live_llm_check.py` |
| Added | `tests/test_opening_hours.py` |
| Updated | `tests/test_recommend.py` |
| Added | `tests/test_recommend_audit.py` |
| Added | `tests/test_ui.py` |
| Added | `ui/__init__.py` |
| Added | `ui/interface.py` |
| Added | `docs/development/AUDIT_CHANGES.md` (this report) |

The source snapshots and their metadata, dataset license, pinned requirements and GitHub Actions workflow are preserved. New tests extend the baseline; no test was removed. Expected assertions changed only for the intended direct/alternative response split.

Public account actions, recording/upload of a demo video, and actual live LLM verification remain separate from these executed checks.
