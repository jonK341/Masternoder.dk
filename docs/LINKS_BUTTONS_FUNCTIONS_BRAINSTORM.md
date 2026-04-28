# Links, Buttons & Functions — Brainstorm & Report

**Goal:** Make all links, buttons, and functions work across the site.

---

## 1. Page links (from index.html and nav)

| Link | Route / File | Status / Risk |
|------|----------------|---------------|
| `/` | Root index.html (all_page_routes) | ✅ Served |
| `/generator` | generator/index.html | ✅ In PAGES |
| `/game` | game/index.html | ✅ In PAGES |
| `/points` | points/index.html | ✅ In PAGES |
| `/battle` | battle/index.html | ✅ In PAGES |
| `/shop` | shop/index.html | ✅ In PAGES |
| `/profile` | profile/index.html | ✅ In PAGES |
| `/gallery` | gallery/index.html | ✅ In PAGES |
| `/stats` | stats/index.html | ✅ In PAGES |
| `/unified_dashboard` | unified_dashboard/index.html | ✅ In PAGES |
| `/trophies` | trophies/index.html | ✅ In PAGES |
| `/quests` | quests/index.html | ✅ In PAGES |
| `/leaderboards` | leaderboards/index.html | ✅ In PAGES |
| `/social` | social/index.html | ✅ In PAGES |
| `/analytics` | analytics/index.html | ✅ In PAGES |
| `/chat` | chat/index.html | ✅ In PAGES |
| `/agents` | agents/index.html | ✅ Dedicated handler in all_page_routes |
| `/dashboard/master_control` | dashboard/master_control/index.html | ✅ Dedicated handler |
| `/dashboard/points` | theme_premium links here | ⚠️ No `/dashboard/points` in PAGES — may 404 |
| `/lab`, `/debugger`, `/aggregator` | In PAGES | ✅ Served |
| `/vidgenerator/*` | Redirect to `/` or `/generator` | ✅ Handled by redirect routes |

**Gaps:**  
- **`/dashboard/points`** — Linked from theme_premium; not in `all_page_routes` PAGES. Add route or point link to an existing page (e.g. `/points` or `/theme_premium`).

---

## 2. Frontpage API calls (index.html)

| Endpoint | Purpose | Backend |
|----------|---------|---------|
| `GET /api/frontpage/init` | Init systems | missing_endpoints_routes |
| `GET /api/stats/summary` | Videos, users, achievements | missing_endpoints_routes |
| `GET /api/points/all?user_id=` | XP, level, points, trophies | points_routes |
| `GET /api/battle/stats?user_id=` | Battle counts | battle_routes, missing_endpoints |
| `GET /api/agent-skillset/all` | Tester agent card | agent_automation_routes, missing_endpoints |
| `GET /api/aggregator/frontend?user_id=` | Unified data for pages | missing_endpoints_routes |

**Risk:** If blueprints are not registered or deploy is stale, these can 404. Frontend uses `BASE_URL` (origin), so paths are `/api/...` (root), not `/vidgenerator/api/...`.

---

## 3. Other pages – API usage (sample)

- **Generator:** `/api/generator/*`, `/api/ai-clips/*`, `/api/documentary/*`, `/api/gallery/clean`, `/api/debugger/tasks/*`
- **Battlegrounds:** `/api/payment/ticket/create`, `/api/battlegrounds/<id>/online`, `/api/battlegrounds/<id>/live`
- **Champions-league:** `/api/champions-league/top10`
- **Theme premium / points:** `/api/points/all`, `/api/178-systems/leaderboard/all`
- **Dashboard / aggregator:** `/api/aggregator/frontend`

Any of these can 404 if the corresponding blueprint or route is missing or not deployed.

---

## 4. Static assets

- **CSS:** `/static/css/modern-design-system.css`, `navigation-toolbar.css`, `image-support.css`, `template-effects.css`, `agent-skill-sets.css`, etc.
- **JS:** `/static/js/error-manager.js`, `unified-point-counters.js`, `comprehensive-api-integration.js`, and many others.
- **Images:** `/static/images/frontpage-bg-theme.png`, etc.

Served by `all_page_routes` at `/static/<path>`. 404 if file is missing under `static/` or not deployed.

---

## 5. Buttons and client-side actions

- **Theme sound toggle** — Pure JS (no API).
- **Quick action / action cards** — All `<a href="...">`; work if the target page route exists.
- **Stats/points loading** — Depends on `/api/stats/summary`, `/api/points/all`, `/api/battle/stats` returning 200; otherwise values stay 0 or “Loading…”.
- **Tester agent card** — Depends on `/api/agent-skillset/all`.
- **Generator buttons** — Depend on generator API routes; 404/500 show as failed requests in console or “error” in UI.

---

## 6. Root causes when things “don’t work”

| Symptom | Likely cause | Fix |
|--------|---------------|-----|
| Link returns 404 | Page not in PAGES or no dedicated route; or nginx not proxying to app | Add page to `all_page_routes` PAGES or add handler; run `fix_nginx_root_proxy.py` |
| API returns 404 | Route/blueprint missing or not deployed | Deploy `fix_404` manifest; ensure `missing_endpoints_routes`, `points_routes`, `battle_routes`, `agent_automation_routes`, etc. are deployed and registered |
| API returns 500 | Server error (recursion, import, DB) | Check `/var/www/html/uwsgi.log`; fix recursion/import/DB; restart uwsgi |
| Stats/counters stay 0 | Frontpage API 404 or CORS/network | Ensure `/api/frontpage/init`, `/api/stats/summary`, `/api/points/all`, `/api/battle/stats` return 200 |
| Button does nothing / console error | fetch() to missing or wrong URL | Align frontend URL with backend route; add route or fix path |
| Static file 404 | File not in `static/` or not deployed | Add file under `static/` and deploy (e.g. full deploy or deploy_index_and_pages) |

---

## 7. Recommended action plan

1. **Verify page routes**
   - Add **`/dashboard/points`** if you want that URL (e.g. serve `dashboard/points/index.html` or redirect to `/points` or `/theme_premium`).
   - Run **`python scripts/test_and_debug_urls.py`** (local) and **`python scripts/test_and_debug_urls.py --live`** (production) and fix any failing paths.

2. **Verify API endpoints**
   - Run **`python scripts/test_url_timing.py`** (if available) to hit frontpage/profile APIs and get OK/FAIL; check **`logs/production_404_deploy_checklist.txt`** for suggested route files.
   - Deploy routes that are missing:  
     **`python scripts/deploy_all_and_restart_uwsgi.py --manifest fix_404`**  
     then re-run the test.

3. **Deploy full set of route and page files**
   - So server has same blueprints and pages as repo:  
     **`python scripts/deploy_all_and_restart_uwsgi.py`**  
     (or at least deploy `fix_404` + pages you use).

4. **Nginx**
   - Ensure all requests hit the app:  
     **`python scripts/fix_nginx_root_proxy.py`**  
   - Resolve “conflicting server name” if present:  
     **`python scripts/fix_nginx_conflicting_server_name.py`**

5. **Static assets**
   - Ensure `static/` is complete on server (full deploy or `deploy_index_and_pages` with required extras).

6. **Manual smoke test**
   - Open `/` → click Generator, Gallery, Profile, Shop, Battle, Game, Points, Stats, Trophies, Quests, Leaderboards, Social, Analytics, Chat, Agents, Unified Dashboard.
   - Confirm no 404s and stats/tester card load (if not, check network tab for which API returns 404/500).

---

## 8. One-command checklist

```bash
# 1) Fix nginx (root proxy + no conflicting server name)
python scripts/fix_nginx_root_proxy.py
python scripts/fix_nginx_conflicting_server_name.py

# 2) Deploy routes that fix common 404s
python scripts/deploy_all_and_restart_uwsgi.py --manifest fix_404

# 3) Optional: full deploy (all pages + backend)
python scripts/deploy_all_and_restart_uwsgi.py

# 4) Test key URLs
python scripts/test_and_debug_urls.py --live

# 5) If you have URL timing script
python scripts/test_url_timing.py
# Then fix any endpoints listed in logs/production_404_deploy_checklist.txt
```

---

## 9. Summary

- **Links:** Almost all page links are covered by `all_page_routes` (PAGES + `/agents`, `/dashboard/master_control`). Add or redirect **`/dashboard/points`** if needed.
- **Buttons:** Work if target page exists and (for API-backed buttons) the corresponding API route exists and returns 200.
- **Functions:** Frontpage stats, point counters, and tester card depend on `/api/frontpage/init`, `/api/stats/summary`, `/api/points/all`, `/api/battle/stats`, `/api/agent-skillset/all`, and `/api/aggregator/frontend`. Deploy `fix_404` + relevant blueprints and ensure nginx proxies to the app so these endpoints and static files are reachable.

Making “all links, buttons and functions work” = **correct nginx + deploy route/page/static set + fix any missing route (e.g. dashboard/points) + verify with test scripts and a quick manual click-through.**

---

## 10. Terminal evidence (session snapshot)

| Terminal | Command(s) | Result |
|----------|------------|--------|
| 37 | `python fix_502.py` | Completed; 126 blueprints; NameError `'OK'` during registration; "Working outside of application context" for debug_sessions/browser_profiles. |
| 39 | nginx root proxy + fix conflicting server name + `--manifest fix_404` | Nginx OK; 5 backup configs disabled; 8 files deployed; uwsgi restarted; **[WARN] Verify timeout** (workers may still be starting). |
| 40 | `test_and_debug_urls.py --live` | All 6 URLs **READ TIMEOUT** (/, /generator, /vidgenerator, …). |
| 41 | `test_url_timing.py` | All 6 front-page APIs **FAIL** (timeout ~15s): frontpage init, stats summary, points all, battle stats, agent-skillset all, aggregator frontend. |
| 42 | `fix_nginx_root_proxy.py` + `fix_nginx_conflicting_server_name.py` | Both OK; 2 configs disabled; nginx reloaded. |
| 494214 | `deploy_uwsgi_ini_and_restart.py` | Paramiko **PipeTimeout** during uwsgi restart. |
| 84530 | `test_and_debug_urls.py` (local) | Local run; SQLite warning; blueprint load. |
| 712693 | `test_and_debug_urls.py --live` | Same as 40 — all timeouts. |

**Conclusion from terminals:** Nginx and fix_404 deploy are in place; **live site and APIs still time out** — uWSGI on server likely not responding in time (slow start, harakiri, OOM, or not bound).

---

## 11. Current status vs goal

| Goal | Status | Blocker |
|------|--------|--------|
| All page links work | Routes exist in code | Live URLs time out (server not responding) |
| All buttons work | Targets defined | Same; API timeouts prevent data load |
| Frontpage stats/counters | 0 or loading | APIs timeout (stats summary, points all, battle stats, etc.) |
| Nginx correct | Done | — |
| fix_404 routes deployed | 8 files deployed | uWSGI verify step timed out; workers may need more time or stability |

**Primary blocker:** uWSGI on server does not respond within 20s (and often not within 15s for API timing). Until the app responds, links that load pages can timeout, and all API-backed functions (stats, points, tester card) will fail.

---

## 12. Continue — recommended next steps (in order)

1. **Stabilize uWSGI on server**
   - Ensure unit has **TimeoutStartSec=300** (run `python fix_502.py` if not already done).
   - On server: `grep harakiri /var/www/html/uwsgi.ini` — should be `harakiri = 300`.
   - Restart and wait: `python scripts/restart_uwsgi_fix_502.py` (waits 150s), then test: `python scripts/test_and_debug_urls.py --live`.

2. **If live URLs still timeout**
   - On server: `tail -80 /var/www/html/uwsgi.log` and `grep -E 'harakiri|killed|recursion|Traceback' /var/www/html/uwsgi.log`.
   - Fix recursion/OOM/harakiri per SERVER_QUICK_REFERENCE.md; redeploy important manifest if needed.

3. **Once live URLs return 200**
   - Run `python scripts/test_url_timing.py` again — front-page APIs should move from FAIL to OK (or show 404 if a route is missing).
   - Fix any remaining 404s using `logs/production_404_deploy_checklist.txt` and redeploy.

4. **Close the dashboard/points gap**
   - Add route or redirect for `/dashboard/points` (see §1) or change theme_premium link to `/points`.

5. **Smoke-test in browser**
   - Open https://masternoder.dk/ — click Generator, Gallery, Profile, Shop, Battle, Game, Points, Stats, Trophies, Quests, Leaderboards, Social, Analytics, Chat, Agents, Unified Dashboard.
   - Confirm no 404s and stats/tester card load; fix any failing API in Network tab.

---

## 13. One-line "continue" checklist

```
fix_502.py (TimeoutStartSec=300) → restart_uwsgi_fix_502.py → test_and_debug_urls.py --live
→ if 200: test_url_timing.py; fix 404s from checklist; add /dashboard/points if needed; browser smoke-test.
→ if still timeout: inspect uwsgi.log and SERVER_QUICK_REFERENCE.
```

---

## 14. "Too many redirects" — cause and fix

**Cause:** When Flask runs behind Nginx over HTTPS, the app sees the request as **HTTP** (the connection from Nginx to uWSGI is HTTP). If any code builds redirect URLs from `request` (e.g. `redirect('/')` or login redirects), Flask can send `Location: http://masternoder.dk/`. The browser then goes to HTTP → Nginx returns `301` to HTTPS → browser hits HTTPS again → Flask again returns HTTP in the redirect → loop.

**Fix (applied):** Use Werkzeug **ProxyFix** so Flask trusts `X-Forwarded-Proto` (and related headers) set by Nginx. Then `request.scheme` is `https` and redirect URLs stay HTTPS.

- In `src/app/__init__.py`: `app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)`.
- Nginx already sends `X-Forwarded-Proto $scheme` in `fix_nginx_root_proxy.py`.

**Deploy:** Redeploy the app (e.g. `src/app/__init__.py`) and restart uWSGI so the change is active. Then retest in the browser.
