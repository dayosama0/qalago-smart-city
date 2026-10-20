# GitHub and Streamlit Community Cloud

Repository: [dayosama0/qalago-smart-city](https://github.com/dayosama0/qalago-smart-city).

Deployment is **not yet verified**. The available browser session opens the Streamlit sign-in page, rather than an authenticated deployment workspace. No public URL has been claimed.

## First deployment: account owner actions

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with the GitHub account that can access this repository. If the service requests new GitHub permissions, review and grant them yourself.
2. Select **Create app → Yup, I have an app**.
3. Set **Repository** to `dayosama0/qalago-smart-city`, **Branch** to `main`, and **Main file path** to `app.py`. Enter the values manually if the repository picker has not refreshed.
4. In **Advanced settings**, choose **Python 3.13** (the local verification version). Set the Groq credentials in that UI for AI search (without a key, only the explicitly enabled reserve mode works):

   ```toml
   GROQ_API_KEY = "your-own-key"
   GROQ_MODEL = "openai/gpt-oss-20b"
   WEATHER_ENABLED = "1"
   ```

   Never put a real key in GitHub, README, `.env.example`, issues or deployment screenshots. `WEATHER_ENABLED = "0"` disables live weather calls; simulated weather still works.
5. Optionally choose an available subdomain. Click **Deploy** and wait for dependency installation and app startup. Use the generated URL; do not assume `qalago-smart-city.streamlit.app` is available.
6. Open the URL in a separate signed-out browser. Confirm the real POI count appears, use EXPO / 60 minutes / simulated clear weather, and click **Подобрать прогулку**. Confirm cards and source links work with a Groq secret, or explicitly enable reserve mode when testing offline.
7. Compare simulated wind with Climate Shield off/on; test confirmed outlets and the airport flight checkbox. Confirm simulations and unknown hours are labeled. Open one **Найти в 2ГИС** link and check the search text.
8. Copy the tested public URL into the README and record the deployed commit and verification date. Until this check succeeds, deployment remains unverified.

These fields and the deploy flow follow the [official deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). Manage optional keys through [Cloud secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Future updates

Community Cloud monitors the selected repository and branch. After the first deployment, each successful push to `main` is copied to the app automatically; changes to `requirements.txt` trigger dependency installation. See [Streamlit's update behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app).

Recommended workflow:

```bash
git switch -c codex/your-change
# edit the application; keep secrets untracked
python -m pytest -q
git add <specific-reviewed-files>
git commit -m "Describe the change"
git push -u origin codex/your-change
# Open a pull request, review the diff and green checks, then merge to main.
```

The included GitHub Actions workflow runs offline tests on pushes to `main` and pull requests using Python 3.11 and 3.13. **It does not gate Streamlit deployment.** Branch protection and required checks have not been configured by this project. Wait for green checks before merging; configure branch protection separately if you require enforced checks.

To refresh public POIs, run `python -m ingestion.build_database` locally, review the dataset changes and provenance, test, then commit the updated public snapshot. Cloud startup never runs ingestion. Cloud local files are ephemeral; this MVP does not persist user inputs or write back to SQLite.

## Troubleshooting

- Missing repository: check the signed-in account and GitHub app access; enter `dayosama0/qalago-smart-city` manually.
- Missing module/build failure: inspect Cloud logs, confirm `requirements.txt` is at the root, Python 3.13 is selected, and entrypoint is `app.py`.
- Missing data: confirm `data/pois.db` is in the deployed commit. Rebuild from committed sanitized snapshots with `python -m ingestion.build_database --offline` locally and push the reviewed snapshot.
- No results: try 60 or 120 minutes, remove strict feature requirements or use another origin. Real OSM coverage may be sparse. Do not add synthetic places to the deployed database.
- Live weather unavailable: use an explicitly labeled simulated scenario. Weather failures must display `unknown`, never simulated sunny weather disguised as live.
- Optional LLM errors: the app displays a Groq error unless reserve mode is explicitly enabled. Validate GROQ_API_KEY and strict JSON-schema model access; free-plan quotas apply.
