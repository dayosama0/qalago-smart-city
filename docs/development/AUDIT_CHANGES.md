# Audit changes

Audit snapshot: `d6611be`, base `fe40dcd`. Proposed on `codex/audit-product-improvements`; main is preserved and the PR remains unmerged. The original file-change list below describes that audit snapshot.

Implemented: common listed-hours filtering, relevance/alternative separation, real Shield comparison, responsive quick scenarios, six sourced POI enrichments and reviewer evidence. No new runtime dependencies or commercial directory data were added.

Executed audit checks: 153 offline tests; local startup and health200; browser widths390/430/768/1440 without horizontal overflow. See [verification](../VERIFICATION.md) for measurements, screenshots and account-dependent limitations. Live OpenAI was not attempted because credentials were missing. At the original audit, Streamlit public deployment was unverified after embedded authentication failed; the later public check is recorded below.

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

At the audit snapshot, public account actions, recording/upload of a demo video, and actual live LLM verification remained separate from the executed checks.

## Public deployment follow-up — 19 October 2026

The [hosted QalaGo app](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/) was subsequently opened independently in a signed-out browser. It returned HTTP 200, displayed 199 POIs and produced three default cards in **Без LLM** template mode.

The public simulated-wind comparison used the same clock, `2026-10-19T16:45:16+05:00`: OFF first NU Park, estimated 35.0 minutes outdoors; ON first Mega Silk Way, estimated 0.7 minutes. These are model estimates for different options. Public viewport checks measured document/body widths of 390/390 at 390 px and 1440/1440 at 1440 px.

This documentation follow-up records the public URL, runtime checks and actual [desktop capture](../images/public-desktop-1440.jpg) and [mobile capture](../images/public-mobile-390.jpg). It supplements the original 40-file audit list; no application code changed for this follow-up. See the current [verification report](../VERIFICATION.md) and [deployment guidance](../DEPLOYMENT.md).

Follow-up files: `README.md`, `EVALUATION.md`, `docs/DEPLOYMENT.md`,
`docs/VERIFICATION.md`, `docs/SUBMISSION_CHECKLIST.md`, this report, and
`docs/images/public-desktop-1440.jpg`, `docs/images/public-mobile-390.jpg`.

The public source button opened [`codex/audit-product-improvements/app.py`](https://github.com/dayosama0/qalago-smart-city/blob/codex/audit-product-improvements/app.py), identifying the configured feature branch. The exact build SHA, Cloud Python setting and secrets were not inspected. Template output does not prove secrets are absent. The audit PR is still unmerged and `main` remains at `fe40dcd`; pushes to `main` do not update this feature-branch deployment. Live OpenAI verification and demo recording/upload remain incomplete.
