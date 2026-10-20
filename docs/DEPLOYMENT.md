# Latest-main deployment and verification

Repository: [dayosama0/qalago-smart-city](https://github.com/dayosama0/qalago-smart-city).

## Current status — 20 October 2026

The owner reports that a teammate has deployed an app. Its current URL was not supplied or found in the repository metadata/public profile checked during this session. The previously known preview still displays 199 places; it does not verify the current main version with 207 places. This is an **unverified latest-main deployment**, not a claim that no deployment has ever happened.

Latest main checked locally: **`c8ac0d6`**, isolated checkout on `codex/main-deployment-refresh`. Local Streamlit started on [127.0.0.1:8503](http://127.0.0.1:8503), and `/_stcore/health` returned HTTP 200. The full automated suite passed **166 tests** on Python **3.13.7**. After the owner added a local key, an explicit live Groq check succeeded: planning and selection returned HTTP 200 and three `llm` recommendations without fallback. The [safe live report](live-groq-verification.json) records both search attempts; generated prose quality was not independently established. The latest local interface was opened at port 8503. Native Chrome automation was again blocked by a built-in policy because its active URL could not be determined. Cloud authentication state was not established; no Cloud deployment, source change or public UI smoke test was completed in this session. See the [dated record](deployment-check-2026-10-20.json) and [verification history](VERIFICATION.md).

The 19 October verification report remains historical evidence for its original code and 199-place snapshot. It does not establish the current provider, dataset or hosted build.

## Account-owner setup or existing-app check

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) in your own browser. Locate the app your teammate deployed, if present. Copy its actual `streamlit.app` URL and inspect its source settings before creating another deployment. Review any GitHub permissions requested in your own account.
2. For the intended latest-main app use these exact source coordinates:

   | Setting | Value |
   |---|---|
   | Repository | `dayosama0/qalago-smart-city` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | Python version | `3.13` — locally tested with 3.13.7 |

   If no matching app exists, choose **Create app → Yup, I have an app** and enter these values. Missing picker suggestions can be entered manually. Keep any working older preview while the new app is checked. A link to a moving branch identifies source configuration, not an exact running commit.
3. In **Advanced settings → Secrets** set your own Groq key for the default AI search. An existing app's secrets can be updated in its settings. The following is a placeholder, not a usable key:

   ```toml
   GROQ_API_KEY = "replace-with-your-own-groq-key"
   GROQ_MODEL = "openai/gpt-oss-20b"
   WEATHER_ENABLED = "1"
   ```

   `GROQ_MODEL` is optional because the shown model is the default. The `openai/` prefix names a model hosted by Groq; this app does not call the OpenAI API. `OPENAI_API_KEY` does not enable this version's AI search. Store real credentials only in Cloud secrets or ignored local configuration, never in Git or shared screenshots.
4. **If no Groq key is available:** the interface can start with empty secrets, but default search will display a key error. In **Дополнительные условия**, deliberately enable **Разрешить резервный режим без ИИ (не рекомендуется)** to obtain the labeled rules-based fallback. This is an individual UI choice, off by default. For an offline scenario choose simulated weather, or set `WEATHER_ENABLED = "0"` to make live weather unavailable; that variable does not turn on reserve mode.
5. Deploy or allow the existing matching app to finish its update. Read build logs for dependency/startup problems. Copy the generated URL rather than guessing its subdomain. Record repository, source branch, deployed commit and Python version from available settings/logs; leave any field unverified if Cloud does not expose it.
6. Run the signed-out smoke checks below, then share the actual URL and observed source revision with the team. The assistant can verify the current deployment only after that URL is available. An owner's deployment report, local HTTP 200 and an older preview are distinct pieces of evidence.

The setup fields and secrets flow follow the official [deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [Cloud secrets guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Manual public smoke test

These are pending owner checks, not claimed results of the 20 October session.

1. Open the actual URL in a separate signed-out browser. Confirm that **Куда пойти в свободное время?** loads and the source points to `main/app.py` in this repository. Record the exact build SHA if available. A functioning page alone does not identify the build.
2. Open the sidebar → **О данных и приватности**. Expect **207 places and 207 descriptions**. The sidebar can show **149 nonempty hours fields**: **144 schedules plus 5 explicit closure markers**. This distinction prevents treating a closure marker as an operating schedule. Check freshness and attribution. A page showing 199 places is the older preview.
3. Select EXPO / MEGA Silk Way, 60 minutes and a short coffee request. With a configured Groq key, run AI search and inspect up to three actual cards, source links, estimated time and schedule status. Record provider errors honestly. No successful live Groq response has been established by local automated tests.
4. Without a key, confirm the clear key error first; then enable the reserve checkbox, select **Ясно · симуляция** and run again. Reserve mode can return up to 20 results, uses rules rather than AI selection and does not perform AI group-preference reconciliation. Results and simulations must remain labeled.
5. Test **Только открытые по расписанию**, including a simulated 23:00 scenario. Unknown hours and visits that exceed a listed closing time must be excluded while that filter is enabled. With the filter off, reserve mode can retain clearly labeled closed options at the end; do not describe them as currently usable.
6. Test airport NQZ with 120 minutes and **Время ограничено вылетом**. Expect a conservative explanation without an excursion. A confirmed-outlet request must not treat unknown as confirmed. Sparse evidence can correctly give no cards.
7. Expand a real card's source details and map. Check one **Найти в 2ГИС** link as a name-and-city search, not a guaranteed matched organization. Inspect a narrow screen for readable controls and cards. These tests do not verify a pedestrian route, an entrance or on-site access.
8. Save the URL, date, source/build evidence, provider or reserve mode, screenshots and failures. Update README/verification only with these actual observations; keep keys and private coordinates out of shared evidence.

## Automatic updates from main

Community Cloud watches the repository and branch configured for that app. An app configured to **main** automatically receives later commits pushed or merged into **main**; changes to dependency files trigger installation and can take longer. A deployment configured to an older feature branch follows that branch instead. Local edits, a different feature branch or a successful test run do not by themselves update the main app. See [official update behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app).

Review a change, run `python -m pytest -q`, and merge only the reviewed commit after its checks pass. The included Actions workflow tests Python 3.11 and 3.13; it does not itself gate Cloud deployment, and branch protection is not configured by this project. Never force-push existing branches.

Refresh public POIs locally, inspect provenance and dataset changes, then commit the reviewed public snapshot. Cloud startup reads `data/pois.db` and never ingests Overpass data. Cloud local writes are ephemeral and are not a database-refresh strategy.

## Troubleshooting

- **Old 199-place screen:** verify the actual URL, repository and configured branch. Do not replace or delete a working preview merely because another URL is missing.
- **Missing repository:** inspect the account's GitHub access and enter the source coordinates manually if necessary.
- **Build failure:** inspect Cloud logs, root `requirements.txt`, `app.py` and Python selection. Do not paste secrets into logs or support messages.
- **Groq key or quota error:** inspect `GROQ_API_KEY`, model availability and account quota in your own settings. Reserve mode requires explicit UI opt-in; errors do not silently become AI success.
- **No results:** review time, strict features and schedule filters; do not add synthetic data to make a deployment check pass.
- **Live weather unavailable:** expect `unknown`. A weather simulation is a separate, labeled choice.
- **Missing SQLite:** verify `data/pois.db` is in the deployed revision. Locally rebuild with `python -m ingestion.build_database --offline`, review the output and push the tested public snapshot.
