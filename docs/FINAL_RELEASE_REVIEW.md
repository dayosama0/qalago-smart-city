# Final release readiness — 19 October 2026

**Conditional GO for a controlled template-mode MVP release after owner authorization, integration CI and new-main smoke checks.** No release-blocking code/security regression was found in the reviewed scope. One nonblocking live-weather robustness issue remains below.

**NO-GO for claiming verified live LLM generation, measured human relevance, demonstrated safety benefit or an already released main deployment.** The recorded API credit error blocks the positive LLM check; it does not establish an implementation failure. No new API request was made during this final review.

## Frozen application and PR dependency evidence

Application inspected and executed: **a4537120335ce15c8b3b6c445a4f72f222b66c50**. This final-review follow-up changes documentation and evaluation artifacts only. A later documentation commit can change the PR head without changing this application tree; check the current PR head and its CI before authorizing any merge.

| PR at review intake | Exact head | Target/base SHA | Exact-head CI and fetched log evidence |
| --- | --- | --- | --- |
| [#1](https://github.com/dayosama0/qalago-smart-city/pull/1), open/unmerged | `348b6a4802556f304269d5234bff3009d5bd7f83` | main / `fe40dcd9a5d27dd1b391fbb28b988febdb7b552c` | [39247495213](https://github.com/dayosama0/qalago-smart-city/actions/runs/39247495213): 3.11 **153 passed / 3.10s**, 3.13 **153 passed / 4.34s** |
| [#2](https://github.com/dayosama0/qalago-smart-city/pull/2), open/unmerged | `a4537120335ce15c8b3b6c445a4f72f222b66c50` | codex/audit-product-improvements / `348b6a4802556f304269d5234bff3009d5bd7f83` | [39254324101](https://github.com/dayosama0/qalago-smart-city/actions/runs/39254324101): 3.11 **236 passed / 3.83s**, 3.13 **236 passed / 6.17s** |

Both were mergeable at inspection. Git ancestry confirms main is an ancestor of PR #1 and PR #1 is an ancestor of PR #2. PR #2's application changes are commits `25b41e9` and `a453712`; it depends on PR #1. Existing Actions check the PR merge ref against the present base, not an as-yet-uncreated future main integration.

No merge, retarget, deletion, force-push or deployment setting change was performed. The functioning preview still follows the PR #1 feature branch. Its source was checked at `348b6a4`; a moving source link does not attest Cloud's exact running build SHA.

## Clean committed execution

A separate detached worktree was created from the full a453712 SHA. Git status was empty before and after execution; no local .env or Streamlit secret was added. The interpreter used was the existing pinned environment, Windows / Python **3.13.7**. Provider calls were disabled for tests; the evaluator explicitly disables LLM and blocks network connections.

- Full suite: **236 passed in 29.56s**.
- Evaluation: **15/15 automated cases**, **9/15 direct-category coverage proxy**, **39/39 estimated time budgets**, 4 alternatives-only cases, 2 expected empty cases, 18 unknown schedules.
- Zero snapshot-field mismatches, strict-feature violations or returned listed-closed cards. These are bounded automated checks, not zero-hallucination or real-world availability claims.
- Single-run recommend latency min/median/max: **0.022 / 2.301 / 9.508 ms**; no warm-up; not a general performance benchmark.
- [Readable report](../evaluation/release-a453712/report.md), [raw JSON](../evaluation/release-a453712/automated_results.json), [case CSV](../evaluation/release-a453712/case_results.csv), [execution record](../evaluation/release-a453712/execution_record.json).

Actual evaluated commit: `a4537120335ce15c8b3b6c445a4f72f222b66c50`, `working_tree_dirty=false`.

Dataset SHA-256: `b7f26c59fac6ce5868e8dec1ee406d185b4a5656f20cbafaee975294066b8ab4`.

Normalized backend/config/evaluator/case fingerprint: `119b60c4496fff6c89a18a2b0bfc8336d3591cd2e3e25dec0f44a534eba1c9fa`.

Reproduction from a fresh checkout of that exact commit:

```bash
git switch --detach a4537120335ce15c8b3b6c445a4f72f222b66c50
git status --porcelain
python -m pytest -q
python -m scripts.evaluate_queries --output-dir /path/outside/checkout/qalago-release-evidence
git status --porcelain
```

Use a clean environment with OPENAI_API_KEY empty and WEATHER_ENABLED=0 for the test command; never copy a real key into the worktree or logs. The actual final-review test invocation set those two environment values before calling pytest. Save evidence outside the checkout so both status checks remain empty.

The original `evaluation/results/rater_a_blank.csv` and `rater_b_blank.csv` were preserved unchanged. Release-run copies are also blank. No human ratings, participant identities, agreement scores or arbitrary-prose truth counts were generated. Two independent reviewers and a coordinator still need to follow [the protocol](EVALUATION_PROTOCOL.md).

## Review finding — P2, nonblocking for the controlled demo

`core/weather.py:96` assumes current_units is a dict. A mocked successful JSON response with valid current values and `current_units: null` raises **AttributeError**, which is absent from the catch list at line 105. The same shape problem can occur with a list/string. The UI's generic recommendation error then suggests rebuilding the dataset rather than showing unknown weather.

Reproduced offline from clean a453712 with requests.get mocked; observed exception: **AttributeError**. No network or provider call was used. Simulated scenarios are unaffected. This review intentionally leaves application code unchanged; owner should triage a dict-shape guard plus regression before claiming comprehensive live-weather failure resilience. README/architecture/deployment wording now discloses the limit.

## Security and regression review scope

Reviewed read-only SQLite/parameterized retrieval, supported-hours/visit checks, strict unknown features, shared-context comparison, untrusted source context, per-POI explanation validation/fallback, context-local credential-safe diagnostics, official-endpoint verification and navigation consent/reset. No blocking issue was identified in those paths. A source URL or an exact quote does not independently establish source truth/current availability.

The publishable-file credential scan and original-form preservation are checked separately; no .env, key, private user location or raw provider response is included in release evidence. New main should start with empty optional secrets for the controlled demo.

## Billing evidence

The [recorded credential-safe report](live-llm-verification.json) is `not_verified`, `answer_mode=template`, official endpoint, model gpt-4.1-mini, HTTP **429**, code **credit_balance_exhausted**, recorded **2026-10-19 17:42 UTC+5**. It contains public POI IDs and fixed diagnostic fields, not keys, prompts or raw errors. It is a historical check, not a fresh query of the account balance.

OpenAI defines that code as exhausted API credits. Owner must resolve API billing and explicitly rerun the verifier before claiming success; only a validated `answer_mode=llm` counts. [Official error guide](https://developers.openai.com/api/docs/guides/error-codes). There is no evidence here of an AI relevance gain or a failed model implementation.

## Owner release sequence and submission gates

1. Review current heads/diffs and authorize PR #1 merge into main; prefer a normal merge commit preserving ancestry. Keep the deployed feature branch.
2. After that merge, authorize retargeting PR #2 to main. Inspect the new diff, merge base and conflicts; the PR #1 work must not unexpectedly reappear. If ancestry changed through squash/rebase, stop and review an integration plan without force-pushing.
3. Require **fresh CI for the new base** before authorizing PR #2 merge. The existing workflow defaults do not include edited events. If no new run is triggered, an owner-authorized ordinary empty commit on PR #2 can trigger synchronize; simply rerunning an old run retains its old SHA/ref. See [GitHub event semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) and [rerun semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
4. Authorize PR #2 merge only after that diff and CI pass. Record the resulting main commit and passing checks.
5. Create a **new** main-connected Community Cloud app and execute [the compact smoke checklist](MAIN_DEPLOY_SMOKE.md); preserve the working preview. Record the actual new URL/revision before updating submission links.
6. Choose honest template-mode submission, or resolve API credits and obtain a successful live check before making an LLM claim. Complete the two independent human reviews if claiming evaluated usefulness.
7. Record/upload the actual [120-second video](DEMO_SCRIPT.md); add the verified deployed URL/QR and matching revision. No recording/upload is claimed by the script.

**Assessment: conditional GO for the template/simulation MVP after those owner-controlled release gates; NO-GO for unsupported live-LLM, human-quality, safety or completed-main-deployment claims.**
