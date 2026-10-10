# Test All Buttons / API Endpoints

Many buttons in the debugger and other pages call backend APIs. This doc describes how to test them all and what was verified.

## URL timing test (front page & profile)

To find slow endpoints that make the front page or profile load slowly, run:

```bash
python scripts/test_url_timing.py
# Production:
BASE_URL=https://masternoder.dk python scripts/test_url_timing.py
```

Results are printed with per-URL duration and saved to `logs/url_timing_results.json`. Fix or optimize any endpoint that takes > 2s.

## Run the button test

**Requires the Flask server to be running** (e.g. `python restart_flask_app.py` or your usual run).

```bash
# From project root, default base http://127.0.0.1:5000
python scripts/test_all_button_endpoints.py

# Against production (replace with your URL if needed)
set BASE_URL=https://masternoder.dk
python scripts/test_all_button_endpoints.py
```

Results are printed to the console and saved to `logs/button_endpoint_test_results.json`.

## What is tested

The script hits **44 endpoints** that are used by:

- **Mission Control** — system overview, AI providers, video providers
- **Debug tab** — all-systems, all-routes, check-duplicates, report
- **Scanner tab** — scan, blueprints, routes, missing, suggestions
- **Agent fix buttons** — fix-personality, fix-missions, fix-quests, fix-history, fix-behavior, fix-all
- **Agent get** — personality, missions, quests, history, statistics, behavior-pattern, run-full-diagnostic
- **Profile (debugger)** — profile/points, profile/stats, profile/agent-points
- **Profile (main)** — user profile aggregated
- **Tasks** — debugger/tasks/list, debugger/tasks/stats, errors/tasks/list, errors/tasks/stats
- **Errors** — errors/stats, errors/list, errors/handler-status/analyze
- **Sync / points** — sync/status, points/all, points/comprehensive
- **Quests / shop / leaderboard** — quests/daily, leaderboard/ai-insights, shop/daily-deal
- **Generator** — unified/status

All of these routes exist in the backend (registered in `backend/routes/*`). If the server is not running, every test will report "Connection refused".

## Buttons that may still fail at runtime

Even when the route exists, a button can fail if:

1. **Wrong path** — Frontend calls a path that was renamed or never implemented (e.g. a typo).
2. **500 from handler** — Route exists but throws (missing dependency, DB error, etc.).
3. **Missing query/body** — Backend expects `user_id` or other params that the frontend does not send.

The test script uses the same paths and (where applicable) query params as the debugger. Fix any 404/500 by aligning frontend URLs with backend routes or fixing the handler.

## Quick fix for “loose” buttons

- **404** — Check that the button’s `fetch()` URL matches a `@route()` in `backend/routes/`. Add the route or fix the URL.
- **500** — Check server logs; fix the handler or add error handling.
- **Connection refused** — Start the Flask app, then re-run the test.
