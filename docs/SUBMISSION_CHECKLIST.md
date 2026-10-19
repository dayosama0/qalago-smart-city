# QalaGo submission checklist

Keep claims tied to the revision actually demonstrated. A passing test suite,
local screenshot or GitHub push does not prove public deployment or live LLM use.

- [ ] **Public app:** open the deployed URL in a separate signed-out browser;
  record URL, branch/commit and date. Run one ordinary scenario and an empty
  airport/outlets scenario. Check the comparison and source links.
- [ ] **GitHub:** provide the repository and reviewable PR URL; check green CI
  for that PR. This audit work stays on a feature branch until reviewed.
- [ ] **Evidence:** use `EVALUATION.md`, `docs/VERIFICATION.md`, provenance and
  the current manifest. Do not call 199 demo-zone records whole-city coverage.
- [ ] **Screenshots:** use actual mobile/desktop captures from the demonstrated
  revision; show simulation badges, direct/alternative labels and source notes.
- [ ] **Video:** record the actual two-minute flow in `docs/DEMO_SCRIPT.md`;
  show a real Shield OFF/ON calculation, strict feature honesty and flight guard.
  Upload the recording using the team's account; no upload is claimed here.
- [ ] **Data:** preserve snapshots, ODbL attribution and field-level evidence.
  Source-backed desk research is not an on-site inspection. Do not claim sockets
  or Wi-Fi unless the specific source supports them.
- [ ] **LLM:** if a real successful call is demonstrated, record the model,
  selected public IDs, `answer_mode=llm` and validation result without secrets.
  Otherwise state live LLM verification is incomplete. Templates remain usable.
- [ ] **Secrets/privacy:** keep `.env`, Cloud secrets, keys and personal
  locations out of Git, screenshots, video and issue/PR text.
- [ ] **Reproducibility:** include the five scenario settings, tested command,
  actual test count and limitations. Show estimates as estimates.

The current executed checks and incomplete account-dependent work are tracked
in `docs/VERIFICATION.md`; this checklist deliberately does not mark unexecuted
submission and recording steps complete.
