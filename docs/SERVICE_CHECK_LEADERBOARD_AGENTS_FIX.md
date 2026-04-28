# Service check failures: leaderboard 500 + `/agents` timeout (fix)

## Root cause

1. **Duplicate `/agents` routes**  
   `missing_endpoints_routes.serve_agents_page` registered `/agents` **after** `all_page_routes.agents_page`, so Flask used the second handler. That version only read `vidgenerator/agents/index.html`. On many installs the real page is **`agents/index.html`** at the project root — wrong file, tiny fallback, or slow/unexpected behavior.  
   **Fix:** Removed root `/agents` from `missing_endpoints`; kept only `/vidgenerator/agents` there, with fallback to root `agents/index.html` for that path. **`/agents` is only served by `all_page_routes`.**

2. **Leaderboard `get_all_users_points()` missing**  
   `leaderboard_routes._get_all_players()` called `unified_points_db.get_all_users_points()`, but the method did not exist on `UnifiedPointsDatabase` (calls were swallowed by `try/except`). Real user data could be inconsistent; corrupt JSON could still break `int()`.  
   **Fix:** Implemented **`get_all_users_points()`** (scan `logs/unified_points/*.json` only — fast). Added **`_safe_int`** in leaderboard routes for normalization and per-system scores.

## Service check updates

`scripts/service_check_all_components.py` now:

- Asserts leaderboard **categories** returns a list with at least 3 entries.
- Asserts **leaderboard all** / **generation** return a **`leaderboard`** list and generation has `system == "generation"`.
- Treats **Page agents** as OK only if HTML body length **≥ 500** (avoids passing on empty stub).

## Deploy workflow (upload without restart, then restart + verify)

**1. Upload new backend files without restarting uWSGI** (code on disk; old workers until restart):

```bash
python scripts/deploy.py service_check_backend --upload-only
```

**2. Restart app workers and run HTTP checks** (one command):

```bash
set PLATFORM_BASE_URL=https://masternoder.dk
python scripts/service_check_all_components.py --restart-uwsgi
```

Optional: also restart the second backend and wait longer for workers:

```bash
python scripts/service_check_all_components.py --restart-uwsgi --restart-5001 --wait-after-restart 90
```

Or set `PLATFORM_RESTART_UWSGI=1` instead of `--restart-uwsgi`.

**3. Full deploy** (upload + restart `uwsgi-vidgenerator` only, no `--upload-only`):

```bash
python scripts/deploy.py service_check_backend
```

---

**Checks only** (no SSH):

```bash
set PLATFORM_BASE_URL=https://masternoder.dk
python scripts/service_check_all_components.py
```

Use `PLATFORM_SKIP_SLOW_CHECKS=1` for a faster pass (skips MN2-heavy endpoints).
