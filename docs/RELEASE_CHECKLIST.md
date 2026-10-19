# Review, merge and migrate to main

This is a plan for the account owner/reviewer. No merge, Cloud source change,
app deletion or redeployment was performed for the submission-readiness work.
The existing public feature preview stays available during review.

Final application review: **a4537120335ce15c8b3b6c445a4f72f222b66c50**,
[clean-commit evidence and finding](FINAL_RELEASE_REVIEW.md). A documentation-only
follow-up may advance PR #2's head; re-read its current SHA and green checks
before merge and verify the application diff against that reviewed revision is
empty. Any new application change needs review.

## Verified starting point — 19 October 2026

- [PR #1](https://github.com/dayosama0/qalago-smart-city/pull/1) is open, unmerged,
  head `348b6a4802556f304269d5234bff3009d5bd7f83`, base `main` at
  `fe40dcd9a5d27dd1b391fbb28b988febdb7b552c`.
- [CI for that exact head](https://github.com/dayosama0/qalago-smart-city/actions/runs/39247495213)
  completed successfully; the two job logs contain 153 passing tests on Python
  3.11 and 3.13.
- PR #2 intake head: `a4537120335ce15c8b3b6c445a4f72f222b66c50`, currently
  targeting the PR #1 branch at `348b6a4`; [its CI](https://github.com/dayosama0/qalago-smart-city/actions/runs/39254324101)
  has 236 passing tests on both Python versions. No retarget/merge was done.
- [Public QalaGo](https://applago-smart-city-dwywv3hxsdtjbdhhj8qien.streamlit.app/)
  was exercised independently, including a simulated 23:00 request. Its source
  button identifies `codex/audit-product-improvements/app.py`. This public
  source corresponds to the PR #1 branch at the verified starting point;
  Cloud's exact build SHA/Python settings were not exposed to the verifier.
- New work is isolated in `codex/submission-readiness`, based on `348b6a4`.
  Its local tests and evaluation do not establish public deployment of the new
  navigation or LLM changes.

## Safe review and merge order

1. Review the exact current PR #1 head and green checks. If the head changed,
   recheck the diff and checks before merging. Use GitHub's ordinary merge
   controls; prefer a merge commit to retain the ancestry needed for the
   stacked PR. Preserve existing history and never force-push.
2. After approval, merge PR #1 into `main`. Record the resulting main commit
   from GitHub, rather than assuming it equals the PR head (merge/squash/rebase
   methods produce different identities). Keep the deployed feature branch
   while the current public preview still depends on it.
3. Review submission-readiness as a separate change. Its PR is initially
   stacked on `codex/audit-product-improvements` to show only new work. After
   PR #1 is merged, retarget that PR to `main`, inspect the resulting diff and
   require green checks against the current main. If a squash merge causes old
   commits to appear again, make a new integration branch from main and apply
   only the reviewed new commit(s); do not rewrite a deployed branch.
4. Merge submission-readiness only after review. Do not merge its stacked PR
   directly into the deployed feature branch as a shortcut. Record the final
   main SHA and its passing CI run.

After retargeting, verify a new CI run for the new base. This workflow uses
default pull_request activity types; do not assume a base edit triggers checks.
If none run, an owner-authorized ordinary empty commit can trigger synchronize.
An old run's Re-run button retains the original SHA/ref and is not evidence for
the new base. [Event defaults](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[rerun semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).

The local credentialed LLM check currently fails with **429 /
`credit_balance_exhausted`**; see the [latest safe report](live-llm-verification.json).
The API organization owner must resolve its credit balance and rerun the
explicit verifier before claiming LLM success. Passing unit tests and working
template mode are separate evidence.

## Deploy main without disturbing the working preview

Use [the compact new-main smoke checklist](MAIN_DEPLOY_SMOKE.md) to record
pass/fail evidence. The following steps describe account setup, not a completed
deployment.

1. In the owner's ordinary authenticated browser, open
   [Community Cloud](https://share.streamlit.io/) and create a separate app from
   `dayosama0/qalago-smart-city`, branch `main`, entrypoint `app.py`. Select the
   tested Python version (3.13). Leave optional secrets empty for template mode.
   A new app needs an available subdomain; do not assume the old URL is reused.
2. Wait for build/startup. Record the deployed main SHA and Python version from
   available logs/settings. If the UI does not expose an exact SHA, record it
   as unverified; a source link to a moving branch is insufficient proof of the
   exact running build.
3. Open the new URL in a separate signed-out session. Re-run the ordinary,
   family, wind OFF/ON, strict-outlet, flight and [23:00](TEST_SCENARIOS.md#public-2300-reproduction--19-october-2026)
   scenarios. Check the new walking link and custom-origin consent, source
   links, map, template mode, and a narrow viewport. Use public presets in
   shared screenshots. If credentials exist, run the explicit live LLM check;
   only `answer_mode=llm` plus successful validation counts as success.
4. Update the README's first demo link and evidence with the URL, demonstrated
   main revision, CI and verification date only after those checks pass. Add
   the same URL/QR to the title slide and record the real demo video. Uploads
   are account-owner actions; no upload is claimed by this checklist.
5. Keep the old preview until the new URL is verified. Retiring/deleting it is
   a separate deliberate owner action. To retain the exact old subdomain,
   follow Streamlit's documented delete/redeploy migration; do not delete a
   working app speculatively.

Streamlit treats owner/repository/branch/entrypoint as the app identity;
changing those coordinates requires redeployment. See the official
[migration instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app)
and [deployment form](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Automatic updates after migration

An app deployed from `main` automatically receives later commits pushed/merged
to `main`; dependency-file changes also reinstall dependencies. The existing
feature preview follows its configured feature branch instead. This behavior
is documented by [Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app).
Cloud updates and GitHub Actions are independent: this repository does not
configure a deployment gate. Review green tests before merging; configure
required checks/branch protection separately if desired.

If a new main deployment fails, keep sharing the working preview and diagnose
the failed build. An application rollback should use a reviewed revert commit
and passing tests, not a force-push of public history.
