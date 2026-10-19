# New main app — owner smoke checklist

Prerequisite: authorize/complete the reviewed PR #1 merge, PR #2 retarget/diff/fresh-CI check, then PR #2 merge. Record the resulting main SHA. These are pending owner actions; keep the existing preview intact.

- [ ] Create a separate Community Cloud app: `dayosama0/qalago-smart-city`, `main`, `app.py`, Python **3.13**. Leave optional secrets empty for template mode; choose a new available URL.
- [ ] Open signed out: app loads, **199** POIs, OSM attribution, source freshness, no startup ingestion or API-key error. Record URL, date, Python and build SHA if actually exposed; otherwise label SHA unverified.
- [ ] **Ordinary:** EXPO / 60 min / architecture / clear simulation / fixed 19.10.2026 14:00 UTC+5. Cards fit estimated budgets; direct/alternative labels and unknown/listed hours remain explicit.
- [ ] **Wind:** nature / EXPO / 60 min / simulated wind / fixed 14:00. OFF/ON share one clock/weather. Inspect different options and likely-indoor warning; no safety or guaranteed percentage claim.
- [ ] **Night:** Baiterek / 60 min / unusual / `необычное занятие ночью` / clear simulation / **23:00**. Clock simulation and late-access warnings visible; listed hours never presented as live opening.
- [ ] **Strict/flight:** required confirmed outlet returns an honest empty result on this snapshot; NQZ / 120 min / flight constraint does not recommend leaving for the city.
- [ ] **External links/map:** source URLs, 2GIS search and public-preset Google Maps walking mode work; map attribution visible. Test manual-mode consent using public test coordinates: no directions link before opt-in, reset after changing coordinates; do not transmit private test locations.
- [ ] **Mobile:** 390 px, readable cards/actions, no horizontal page overflow; change inputs and verify old results hide until recalculated.
- [ ] Match source/behavior to reviewed main, save public screenshots and update README/video link only after the checks pass. Keep the old preview until this new URL is verified. Later main pushes update this app; CI and Cloud deployment are separate.

Live LLM is optional and currently billing-blocked in the recorded report. Resolve API credits and run the explicit verifier separately before claiming `answer_mode=llm`; never put keys in screenshots or Git. Simulated weather is the controlled demo path; the known malformed live-weather-unit issue is in [final review](FINAL_RELEASE_REVIEW.md).

[Official deployment form](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) · [Automatic update behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app).
