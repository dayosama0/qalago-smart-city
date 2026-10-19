# QalaGo submission checklist

Keep claims tied to the revision actually demonstrated. A passing test suite,
local screenshot or GitHub push does not prove public deployment or live LLM use.

- [x] **Public app runtime:** separate signed-out browser check on 19 October
  2026; [verified URL and evidence](VERIFICATION.md#public-community-cloud-check--19-october-2026).
  Ordinary, child, wind/comparison, strict outlets and flight scenarios checked;
  source details and generated 2GIS search checked.
- [x] **Public 23:00:** the PR #1 public preview was checked with explicit
  simulated clock, listed/unknown hours and late-time notes; see reproduction
  and actual captures in `docs/TEST_SCENARIOS.md`.
- [ ] **Reviewed main release:** follow `docs/RELEASE_CHECKLIST.md`. PR #1 is
  still open; new submission-readiness work is isolated from the public app.
- [ ] **Cloud build metadata:** the public source button identifies the feature
  branch and `app.py`; account owner still needs to record exact Cloud build SHA
  and Python selection from deployment logs/settings. Do not publish secrets.
- [x] **GitHub:** provide the repository and reviewable PR URL; check green CI
  for that PR. This audit work stays on a feature branch until reviewed.
- [x] **Evidence:** use `EVALUATION.md`, `docs/VERIFICATION.md`, provenance and
  the current manifest. Do not call 199 demo-zone records whole-city coverage.
- [x] **Screenshots:** use actual mobile/desktop captures from the demonstrated
  revision; show simulation badges, direct/alternative labels and source notes.
- [ ] **Video:** record the actual two-minute flow in `docs/DEMO_SCRIPT.md`;
  show a real Shield OFF/ON calculation, strict feature honesty and flight guard.
  Upload the recording using the team's account; no upload is claimed here.
- [x] **Data:** preserve snapshots, ODbL attribution and field-level evidence.
  Source-backed desk research is not an on-site inspection. Do not claim sockets
  or Wi-Fi unless the specific source supports them.
- [ ] **LLM:** if a real successful call is demonstrated, record the model,
  selected public IDs, `answer_mode=llm` and validation result without secrets.
  Otherwise state live LLM verification is incomplete. Templates remain usable.
  The real check returned `429 / credit_balance_exhausted`; see
  `docs/live-llm-verification.json`. Owner API billing action and a successful
  explicit recheck are still required before checking this box.
- [x] **Automated query evaluation:** 15 authored representative examples run
  against genuine POIs, with code/data fingerprints and actual results in
  `evaluation/results/`. These are not collected user queries or human scores.
- [ ] **Independent human relevance:** two raters complete the blank forms,
  then a coordinator records disagreements; use `docs/EVALUATION_PROTOCOL.md`.
- [x] **Repository secrets/privacy:** keep `.env`, Cloud secrets, keys and personal
  locations out of Git, screenshots, video and issue/PR text.
- [x] **Reproducibility:** include the five scenario settings, tested command,
  actual test count and limitations. Show estimates as estimates.

The current executed checks and incomplete account-dependent work are tracked
in `docs/VERIFICATION.md`; this checklist deliberately does not mark unexecuted
submission and recording steps complete.
