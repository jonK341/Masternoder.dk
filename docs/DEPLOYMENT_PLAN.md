# Deployment plan — 90% uptime, one path

**Goal:** One way to run the site. No more “try fix_502, then deploy, then something else breaks.”

---

## 1. What was wrong

| Problem | Effect |
|--------|--------|
| **Two ways to run the app** | `fix_502.py` starts **uwsgi-vidgenerator** (direct systemd unit). Other scripts (e.g. `deploy_all_and_restart_uwsgi.py`, `reset_port_5000.py`) start **uwsgi** (emperor). After fix_502 the site works; after deploy we start the wrong service → 502 or conflict. |
| **lazy-apps = true** | Workers load on first request (1–3 min each). First requests time out → 502/504. |
| **Nginx timeouts too low** | Slow or first requests hit “upstream timed out (110)”. |
| **Many overlapping scripts** | fix_502, deploy, reset_port, stop_ports_5000_5003… each does slightly different things; easy to run the wrong one. |

---

## 2. Single path (what we use now)

- **One service:** `uwsgi-vidgenerator` (direct systemd unit). No emperor. All scripts that start the app use:
  ```bash
  systemctl start uwsgi-vidgenerator
  ```
- **Eager load:** In `vidgenerator/uwsgi.ini`, `lazy-apps = false`. Workers load at startup; first request answers immediately. No `warm_up_workers.py` needed.
- **Nginx:** Proxy to `127.0.0.1:5000`; timeouts 300s (so slow/heavy requests don’t 504). Applied by `fix_502_nginx_only.py` or `ensure_site_up.py`.
- **Stable screen:** On 502/503/504 nginx serves `502.html` (loading page with auto-refresh) so users never see a blank page. Set up by `fix_nginx_502_page.py` (run automatically from `fix_502_nginx_only` / `ensure_site_up`).
- **One “get site up” command:** Run **`python scripts/ensure_site_up.py`** (or **`python fix_502.py`** then **`python scripts/fix_502_nginx_only.py`**). After deploy, **`python scripts/deploy_all_and_restart_uwsgi.py`** also starts `uwsgi-vidgenerator` (same service).

---

## 3. Commands (canonical)

| When | Command |
|------|--------|
| **Site down / 502 / “try everything”** | From PC: `python scripts/ensure_site_up.py` |
| **Deploy code** | From PC: `python scripts/deploy_all_and_restart_uwsgi.py` |
| **Restart app only (on server)** | `sudo systemctl restart uwsgi-vidgenerator` |
| **Check status** | `systemctl status uwsgi-vidgenerator` and `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/` |
| **Generator DB (once per environment)** | `python scripts/generator_migration.py --standalone` — creates `video_generation_jobs` and `job_artifacts` so jobs persist across restarts. Run after deploy in each environment (dev/staging/production). |

Never run `systemctl start uwsgi` (emperor) for this app. Only `uwsgi-vidgenerator`.

---

## 4. What’s in the repo (implementation)

- **`vidgenerator/uwsgi.ini`** — `lazy-apps = false` so workers load at startup.
- **`fix_502.py`** — Full fix: free port, perms, install and start `uwsgi-vidgenerator`, test. Still the “nuclear” fix.
- **`scripts/ensure_site_up.py`** — One script: run fix_502 + nginx timeouts + verify. Use when you just want the site up.
- **`scripts/deploy_all_and_restart_uwsgi.py`** — Deploy files, then start **uwsgi-vidgenerator** (not uwsgi), and optionally apply nginx timeout fix.
- **`scripts/reset_port_5000.py`**, **`scripts/stop_ports_5000_5003_restart_uwsgi.py`** — Start **uwsgi-vidgenerator** after freeing ports.
- **`scripts/fix_502_database.py`**, **`scripts/deploy_502_fix_and_restart.py`**, **`scripts/hard_fix_502.py`** — Updated to start **uwsgi-vidgenerator** where they restart the app.
- **`docs/SERVER_QUICK_REFERENCE.md`** — Updated to point to this plan and `ensure_site_up.py`.

---

## 5. If it still fails

1. **Run:** `python scripts/ensure_site_up.py`  
2. **If 502 persists:** `python scripts/investigate_502.py`  
3. **If uWSGI exits with code 1:** `python scripts/diagnose_uwsgi_exit_code.py`  
4. **If port 5000 stuck:** `python scripts/reset_port_5000.py` then `python scripts/ensure_site_up.py`

No more mixing emperor and direct unit; one service, one path, eager load, high timeouts.

---

## 6. URL structure (generator at root)

- **Primary site:** All pages and the generator live at the domain root: `https://masternoder.dk/`, `https://masternoder.dk/generator`, `https://masternoder.dk/gallery`, etc. Static assets at `/static/`, APIs at `/api/`.
- **Legacy:** `https://masternoder.dk/vidgenerator` and `https://masternoder.dk/vidgenerator/*` return **301 redirects** to `/*` (e.g. `/vidgenerator/generator` → `/generator`). Use root URLs for new links; old bookmarks still work via redirect.
