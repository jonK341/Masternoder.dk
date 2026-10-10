# URL Timing – Production Results & Fixes

When you run `BASE_URL=https://masternoder.dk python scripts/test_url_timing.py`, you get timings and status for every URL used by the front page and profile page.

## If you see 404s

Nine endpoints can 404 on production if the deployed app is older than the repo:

| Endpoint (path contains) | Backend file |
|--------------------------|--------------|
| frontpage/init | `backend/routes/missing_endpoints_routes.py` |
| battle/stats | `backend/routes/battle_routes.py` |
| agent-skillset/all | `backend/routes/agent_automation_routes.py` |
| profile/aggregated | `backend/routes/user_profile_routes.py` |
| user/identity | `backend/routes/user_account_routes.py` |
| account-summary/points | `backend/routes/user_account_routes.py` |
| gallery/recent-temp | `backend/routes/gallery_routes.py` |
| trophies/list | `backend/routes/trophies_routes.py` |
| battle/pvp/trophies | `backend/routes/battle_routes.py` |

**Fix:** Deploy the repo (or at least these route files and `backend/register_blueprints.py`) so the app registers the same blueprints. After a run with 404s, the script also writes `logs/production_404_deploy_checklist.txt`.

**Code fix applied:** The front page calls `/vidgenerator/api/agent-skillset/all` (hyphen). The backend now has that path as an alias in `agent_automation_routes.py`; deploy that file so production stops 404ing on agent-skillset/all.

## If you see slow endpoints (e.g. ≥ 2s)

Typical slow ones:

- **Stats summary** (e.g. 17s) – consider caching or lighter query in `missing_endpoints_routes` stats/summary.
- **Points all** (e.g. 7s) – `points_routes` / unified points DB; consider caching or indexing.
- **Aggregator frontend** (e.g. 7s) – aggregates several sources; consider parallel backend calls or cache.
- **Profile aggregated** (when it returns 200) – single call that does profile + activity + agents + trophies; consider splitting or caching.

Run the timing script after any deploy to confirm 404s are gone and to track slow endpoints.
