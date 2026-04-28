# Deploy preparation – recheck and run

**Last recheck:** URL timing run against https://masternoder.dk (see below).  
**Goal:** Deploy route files and restart uwsgi so front page and profile endpoints return 200.

---

## 1. Recheck results (latest URL timing)

Run:

```bash
python scripts/test_url_timing.py
```

With production: `set BASE_URL=https://masternoder.dk` then run again (or use default if .env points to production).

**Typical current state (production):**

| Result | Endpoints |
|--------|-----------|
| **OK (200)** | Stats summary, Points all, Aggregator frontend, Bind session, Geo ref, PayPal control panel, Agents activity feed, My agents, Game achievements |
| **Failed (404)** | Front page init, Battle stats, Agent skillset all, Profile aggregated, User identity, Account summary points, Gallery recent, Trophies list, Battle PVP trophies |

Details: `logs/url_timing_results.json`, `logs/production_404_deploy_checklist.txt`.

---

## 2. What gets deployed (fix_404 manifest)

The manifest **fix_404** deploys exactly the route and registration files needed for the 404 list:

| File | Purpose |
|------|---------|
| `backend/routes/missing_endpoints_routes.py` | Fallbacks for front page init, battle stats, agent skillset, profile aggregated, user identity, account summary, gallery recent, trophies, battle PVP |
| `backend/register_blueprints.py` | Blueprint registration (missing_endpoints, gallery, etc.) |
| `backend/routes/user_profile_routes.py` | Profile aggregated |
| `backend/routes/user_account_routes.py` | User identity, Account summary points |
| `backend/routes/battle_routes.py` | Battle stats, Battle PVP trophies |
| `backend/routes/agent_automation_routes.py` | Agent skillset all |
| `backend/routes/gallery_routes.py` | Gallery recent |
| `backend/routes/trophies_routes.py` | Trophies list |

---

## 3. Commands to prepare and run deploy

**Option A – Deploy fix_404 and restart uwsgi (recommended)**

```bash
cd c:\Users\jonkh\UsecaseSampler\Masternoder.dk
.venv\Scripts\python.exe scripts\deploy_all_and_restart_uwsgi.py --manifest fix_404
```

This will:

1. Connect to server (masternoder.dk)
2. **Kill gunicorn and free port 5000 first** (fixes 502 Bad Gateway)
3. Stop uwsgi
4. Upload the 8 files in the fix_404 manifest
5. Clear cache
6. Start uwsgi
7. Verify :5000 and reload nginx

**Option B – Dry-run first**

```bash
.venv\Scripts\python.exe scripts\deploy_all_and_restart_uwsgi.py --manifest fix_404 --dry-run
```

**Option C – Full deploy (all project files) then restart**

```bash
.venv\Scripts\python.exe scripts\deploy_all_and_restart_uwsgi.py
```

(No `--manifest`: deploys all files under vidgenerator, backend, scripts, docs, data.)

**Fix 502 Bad Gateway (restart only, no upload)**

If the site returns 502, gunicorn may be holding port 5000. The deploy script now **kills gunicorn first**, then stops uwsgi, then starts uwsgi. To only restart services (no file upload):

```bash
.venv\Scripts\python.exe scripts\deploy_all_and_restart_uwsgi.py --no-upload
```

On the server you can also run: `bash scripts/server_fix_uwsgi.sh` (kills gunicorn first, then uwsgi, frees 5000, then run uwsgi in foreground to see errors).

---

**Option D – 404 fallbacks only (single file)**

```bash
.venv\Scripts\python.exe scripts\deploy_404_fallbacks.py
```

Then on server (or via a restart script): restart uwsgi / python-proxy so the new code is loaded.

---

## 4. After deploy – verify

```bash
set BASE_URL=https://masternoder.dk
.venv\Scripts\python.exe scripts\test_url_timing.py
```

Check that Failed count is 0 or reduced. If 404s remain, ensure the app process (uwsgi) was restarted and that `APPLICATION_ROOT` / blueprint prefix matches `/vidgenerator` (see docs/CHECKPOINTS_RECHECK.md §9).

---

## 5. Quick reference

| Task | Command |
|------|---------|
| Recheck URLs | `python scripts/test_url_timing.py` |
| Deploy fix_404 + restart uwsgi | `python scripts/deploy_all_and_restart_uwsgi.py --manifest fix_404` |
| Deploy everything + restart | `python scripts/deploy_all_and_restart_uwsgi.py` |
| Deploy only fallbacks file | `python scripts/deploy_404_fallbacks.py` |
| 404 checklist | `logs/production_404_deploy_checklist.txt` |
| Full checkpoints | `docs/CHECKPOINTS_RECHECK.md` |
