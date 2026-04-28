# Server quick reference (masternoder.dk)

## News / recent updates (March 2026)

- **fix_502.py** — After bringing the app up, it now runs **URL timing** (Step 5c): `scripts/test_url_timing.py` refreshes `logs/url_timing_results.json`. At the end it prints a short summary from that file (OK/failed counts, total time, list of failed endpoints). No need to run the timing script separately after a fix.
- **Todos** — The app todo list is kept at **25 items** in `data/todos/todos.json`; `updated_at` is maintained when the list is edited.
- **Port 5000** — fix_502 polls up to ~2.5 min for workers to load; if the site still times out, see “Worker killed ~10 seconds after start” and “Port 5000 returns 000” below. `uwsgi.ini` uses `listen = 400` (or 200) to reduce “listen queue full” during startup.

## Get the site up (one path)

- **Site down / 502 / “nothing works”** — From your PC: **`python scripts/ensure_site_up.py`**  
  Runs fix_502 (free port, perms, start uwsgi-vidgenerator) + nginx timeouts, then you can test https://masternoder.dk/

- **Restart app only** (on server): `sudo systemctl restart uwsgi-vidgenerator`

- **Deploy code** — From your PC: `python scripts/deploy_all_and_restart_uwsgi.py` (starts uwsgi-vidgenerator, not emperor).

- **Production requirements (slim, when disk is tight):**  
  Upload: `python scripts/upload_requirements_production.py`  
  Then install: `python scripts/install_requirements_on_server.py --production -y`  
  (Uses `requirements-production.txt`; no torch/transformers; ~500MB–1GB.)

Full plan: **docs/DEPLOYMENT_PLAN.md** (single service, eager load, no emperor).

- **Generator jobs not persisting / lost on restart:** Run the generator DB migration once per environment: **`python scripts/generator_migration.py --standalone`** (creates `video_generation_jobs`, `job_artifacts`). See **docs/DEPLOYMENT_PLAN.md** and **docs/GENERATOR_AND_AI_OVERVIEW.md**. Ensure **VIDEOS_DIR** (or `vidgenerator/videos`) has at least **100 MB free** for encoding.

- **Generator: clear stuck jobs** — In-memory only: **`GET /api/generator/reset-for-test?confirm=test`**. To clear disk state: delete `<doc_id>.status.json` and `<doc_id>.job.json` (and optionally `<doc_id>.mp4`) in **VIDEOS_DIR** for the stuck job.

- **Generator subprocess log (why job stuck at "Starting...")** — Log is on the **server** at `VIDEOS_DIR/generator_subprocess.log`. The file is only created when the encoding **subprocess** runs; if encoding runs in-process (thread fallback), errors are in **uwsgi.log** instead. **On the server**, get the path then tail the log:
  ```bash
  # Get videos_dir (run on server)
  curl -s http://127.0.0.1:5000/api/generator/test | python3 -c "import sys,json; print(json.load(sys.stdin).get('videos_dir',''))"
  # Then (replace /var/www/html/vidgenerator/videos with the path printed above if different):
  tail -100 /var/www/html/vidgenerator/videos/generator_subprocess.log
  ```
  If that log file does not exist, use **`tail -100 /var/www/html/uwsgi.log`** and look for `[VideoGenerator]` or tracebacks.

## Stability: disable path correction in production (migration plan Phase 1)

To avoid worker death from recursion/OOM, path correction is **disabled** when the app runs in production. Set one of these in the uWSGI/systemd environment (e.g. `/etc/systemd/system/uwsgi-vidgenerator.service.d/environment.conf`):

- **`PRODUCTION=true`** or **`FLASK_ENV=production`** — path correction is off; front page and links stay up.
- **`DISABLE_PATH_CORRECTION=1`** — same effect (path correction off).

Optional: **`LITE_APP=1`** — register only ~25 critical+core blueprints (faster startup, lower memory); same pages/static/APIs. See **docs** migration plan Phase 1.2.

## Where to run fix_502.py

- **Run on your PC** (from the project folder): `python fix_502.py`  
  It connects by SSH to the server and does all steps (stop services, fix perms, start uwsgi-vidgenerator). The file does not need to exist on the server.

- **On the server**, to only restart the app:
  ```bash
  sudo systemctl restart uwsgi-vidgenerator
  ```
- **No warm-up needed:** `uwsgi.ini` uses `lazy-apps = false` so workers load at startup; first request responds immediately. (If you ever switch to `lazy-apps = true`, use **`python scripts/warm_up_workers.py`** after restart or run **`python scripts/disable_lazy_apps.py`** to switch back.)

## Required layout under /var/www/html

uWSGI uses `chdir = /var/www/html` and `module = wsgi`, so the server needs:

- `/var/www/html/wsgi.py`
- `/var/www/html/uwsgi.ini` (config and logto at root)
- `/var/www/html/src/` (Flask app)
- `/var/www/html/backend/` (routes, services)
- `/var/www/html/vidgenerator/src/` (calculator routes; rest of vidgenerator moved to root for space)
- `/var/www/html/static/`, `/var/www/html/index.html`, `/var/www/html/generator/`, etc. (pages and assets at root)

Deploy the full project with `python scripts/deploy_all_and_restart_uwsgi.py`. To move existing server content to root and remove the old vidgenerator folder: `python scripts/server_move_and_remove_vidgenerator.py` (run once after deploying the new layout).

## Internal Server Error (500) in browser

500 means the Flask app raised an exception. To see the Python traceback:

- **On the server:**  
  `tail -80 /var/www/html/uwsgi.log`  
  Look for `Traceback`, `Error`, and the last exception. Fix the reported line (e.g. missing file, missing package, bad path).

- **From your PC (if SSH works):**  
  `python scripts/investigate_502.py`  
  Section [6] and [6b] show uWSGI log and error grep.

- **Common causes after deploy:**  
  - `index.html` not at root: ensure `/var/www/html/index.html` exists (or redeploy).  
  - Missing Python package: if you use `requirements-production.txt`, a route may import a package that was omitted (e.g. `torch`). Install it or guard the import.  
  - Wrong path in code: e.g. still pointing at `vidgenerator/` when files were moved to root.

## All live URLs timeout from your PC (test_and_debug_urls / test_url_timing)

If **every** live URL shows READ TIMEOUT or 502 from your PC:

1. **On the server (SSH)** check that uWSGI is up and that port 5000 answers **after workers have loaded** (can take 2–3 minutes):
   ```bash
   systemctl status uwsgi-vidgenerator
   # Wait 2+ min after a fresh start, then:
   curl -s -o /dev/null -w "%{http_code}" --max-time 90 http://127.0.0.1:5000/
   ```
   - If you get **200** or **301**: app is fine; Nginx or network may be the limit. From PC try a longer timeout: `set LIVE_TIMEOUT=90` (Windows) or `LIVE_TIMEOUT=90` (bash) then re-run the test script.
   - If you get **000** or timeout on the server: workers are not ready or are crashing. Check:
     ```bash
     tail -100 /var/www/html/uwsgi.log
     grep -E 'killed|recursion|Traceback|DAMN' /var/www/html/uwsgi.log
     ```
   - If workers keep dying (signal 9): see "worker N died, killed by signal 9" below; add swap and/or ensure recursion fixes are deployed.
2. **Restart and wait, then test from PC:**  
   `python scripts/test_and_debug_urls.py --live --reboot` (restart script waits 150s). Or set **`LIVE_TIMEOUT=90`** (or **`READ_TIMEOUT=90`** for test_url_timing) and run the test again after 2–3 minutes.

## Curl on server only returns 502

502 means Nginx is not getting a valid response from uWSGI on port 5000. Either uWSGI is not responding (workers stuck or crashing) or not running.

- **From your PC:** **`python scripts/restart_uwsgi_fix_502.py`** — Stops uWSGI, frees port 5000, starts uwsgi-vidgenerator, waits 90s for workers to load, then tests `http://127.0.0.1:5000/` and `https://masternoder.dk/`.
- **On the server (manual):** Wait **at least 2 minutes** after start before curling (workers load 126 blueprints).
  ```bash
  sudo systemctl stop uwsgi-vidgenerator
  sudo pkill -9 -f uwsgi; sleep 2
  sudo fuser -k 5000/tcp 2>/dev/null
  sudo systemctl start uwsgi-vidgenerator
  echo "Waiting 120s for workers to load..."
  sleep 120
  curl -sI -w "HTTP: %{http_code}\n" --max-time 120 http://127.0.0.1:5000/
  ```
  If port 5000 still returns **000**, run uWSGI in foreground to see the error:  
  `sudo systemctl stop uwsgi-vidgenerator` then  
  `sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini`  
  In another terminal, when you see `[SUMMARY] Registered 126 blueprints`, run  
  `curl -v http://127.0.0.1:5000/` and watch the first terminal for a Python traceback.

## Still 502 or "upstream timed out"

- **"upstream timed out (110)" in nginx error log:** The backend is slow to respond (e.g. first request with lazy-apps, or heavy `/api/points/all`). Nginx gives up before the app answers.
  - Run **`python scripts/fix_502_nginx_only.py`** – it now sets proxy timeouts to **300s** so slow/first requests can finish.
  - Or manually: **`python scripts/fix_504_timeouts.py --increase 300`** then reload nginx on the server.
- **502 with no timeout in log:** Run **`python fix_502.py`** (app + nginx). If uWSGI is already up, run **`python scripts/fix_502_nginx_only.py`**.
- **"upstream prematurely closed" or "recv() failed (104)" in nginx:** uWSGI workers are crashing mid-request. Run **`python scripts/investigate_502.py`** and check section [6b] for tracebacks. To see the crash live: on server stop uwsgi, then run `sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini` and in another terminal `curl http://127.0.0.1:5000/api/points/all`; fix the exception and restart uwsgi-vidgenerator.
- **"worker N died, killed by signal 9" or uWSGI exits with "Killed" in foreground:** The kernel OOM killer is killing the process (out of memory). **Add swap** so the system has virtual memory before OOM fires. On the server (one-time):
  ```bash
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  free -h
  ```
  Then start uWSGI again: `sudo systemctl start uwsgi-vidgenerator`. `uwsgi.ini` already uses **`processes = 1`** to reduce RAM use.
- **Diagnose:** **`python scripts/investigate_502.py`** (nginx error log, uwsgi crash grep, config, port 5000 test).
- **Port 5000 returns 000 or times out; uwsgi.log shows "maximum recursion depth exceeded":** The worker is blocked by recursion in "Error saving intelligence" or "AI path correction". Deploy the fix that catches `RecursionError` in `agent_ai_intelligence.save_intelligence()` so the worker skips the save instead of blocking. Then run **`python scripts/restart_uwsgi_fix_502.py`** or **`python scripts/test_and_debug_urls.py --live --reboot`**. Log path for checks: **`/var/www/html/uwsgi.log`** (not vidgenerator/uwsgi.log).
- **"conflicting server name masternoder.dk":** Multiple nginx configs define the same server. From your PC run **`python scripts/fix_nginx_conflicting_server_name.py`** – it disables duplicate configs and keeps the one that proxies to port 5000. Or on the server: `ls -la /etc/nginx/sites-enabled/` then remove symlinks for duplicates (e.g. `sudo rm /etc/nginx/sites-enabled/other.conf`).

### Why "Port 5000 is LISTENING but curl got HTTP 000" / app not responding

From `investigate_502.py` and nginx logs you may see: **upstream timed out (110)**, **Port 5000: HTTP 000**, and many API requests (e.g. `/api/game/stats`, `/api/points/all`, `/api/battle/stats`) timing out. Common causes:

1. **Too few workers for concurrent load** — With `processes = 2`, a single page (e.g. shop) can fire 10+ API calls at once. Two workers handle two requests; the rest wait. Nginx waits `proxy_read_timeout` (set 300s by fix_502_nginx_only) then returns 504/110. **Fix:** Ensure **`python scripts/fix_502_nginx_only.py`** has been run (300s timeouts). If the server has enough RAM, in `uwsgi.ini` try **`processes = 3`** or **`processes = 4`** and restart uwsgi-vidgenerator.
2. **Slow or blocking requests** — Heavy endpoints (`/api/points/all`, `/api/points/comprehensive`, etc.) or code that runs outside app context ("Working outside of application context", "Error ensuring debug_sessions table") can block a worker. Fix those in app code (use `app.app_context().push()` where needed, or guard DB access).
3. **NameError: name 'OK' is not defined** — Appears during blueprint load in uwsgi.log; app usually still finishes (126 blueprints). If a worker crashes on it, fix the code that uses `OK` as a variable (e.g. use the string `"OK"`).
4. **Reload nginx after app is up** — So nginx reconnects to :5000. **`python fix_502.py`** does this in Step 4b; or on the server: `systemctl reload nginx`.

Quick checks: **`python scripts/check_latency_from_server.py`** (latency from server to app); **`python scripts/investigate_502.py`** (services, nginx log, uwsgi log).

## Service worker (minimal, low power)

The app uses a **minimal** service worker: no cache, no background sync, no fetch interception. All requests go to the network. To disable: add **`?sw=0`** to the URL, or run `localStorage.setItem('sw_disabled','1')` in the console and reload.

## Test and debug URLs (root-first setup)

- **Local (Flask test client):** **`python scripts/test_and_debug_urls.py`** — Verifies `/`, `/generator`, `/vidgenerator` redirects, `/static/` without hitting the network.
- **Live site:** **`python scripts/test_and_debug_urls.py --live`** — Curls https://masternoder.dk/ and key paths (run from a machine that can reach the server).
- **Restart server then test:** **`python scripts/test_and_debug_urls.py --live --reboot`** — Runs `restart_uwsgi_fix_502.py` (stop uWSGI, free port 5000, start, wait for workers), then runs the live URL tests. Use when the site times out or returns 502.
- If live **`/` redirects to `/vidgenerator/`** or **`/generator` is 404**, nginx is still on the old config. After deploying code, run **`python scripts/fix_nginx_root_proxy.py`** so nginx proxies all requests to the app (no redirect from `/` to `/vidgenerator/`).

## Test URL and screenshot

From your PC: **`python scripts/test_url_and_screenshot.py`**  
- Tests `https://masternoder.dk/` with a 120s timeout and prints HTTP status and page title.  
- If **playwright** is installed (`pip install playwright` then `playwright install chromium`), saves a screenshot to `scripts/screenshot_masternoder.png`.  
- If the test times out, run `fix_502_nginx_only.py` or `fix_502.py` first so the app responds within the timeout.

## Startup log warnings (non-fatal)

- **"Could not create database tables: (sqlite3.OperationalError) unable to open database file"** – The app wants to write SQLite to `instance/database.db`. Ensure the directory exists and is writable by www-data. `fix_502.py` Step 1b now creates `mkdir -p /var/www/html/instance` and `chown www-data:www-data /var/www/html/instance`.
- **"NameError: name 'OK' is not defined"** – Occurs in one of the app-load test workers; the app still finishes (124 blueprints, "Done."). If you need to fix it, run the app load test and check the full traceback for the file and line.
- **"Could not import agent_automation: ... circular import"** – One worker may skip it; another often loads it later ([OK] Registered agent_automation). Safe to ignore unless that blueprint is missing in production.

## Nginx errors: recv() failed (104), connect() failed (111)

- **104 (Connection reset by peer):** Upstream (uWSGI) closed the connection while nginx was reading the response. Often means the worker died, was killed (harakiri), or the app crashed during the request.
- **111 (Connection refused):** Nothing is listening on 127.0.0.1:5000. uWSGI is down or not bound yet. Run `systemctl start uwsgi-vidgenerator` or `python fix_502.py`.

## Check app status on the server

```bash
systemctl status uwsgi-vidgenerator
journalctl -u uwsgi-vidgenerator -n 50 --no-pager
curl -s -o /dev/null -w "%{http_code}" --max-time 60 http://127.0.0.1:5000/
```

**Important:** Only use **uwsgi-vidgenerator**. Do not run `systemctl start uwsgi` (emperor) for this app; deploy and fix scripts now all use uwsgi-vidgenerator.

## Stable screen (no blank page)

When the app is starting or returns 502/503/504, nginx serves a **loading page** instead of a blank or generic error. Run **`python scripts/fix_502_nginx_only.py`** or **`python scripts/ensure_site_up.py`** to deploy `static/502.html` and configure nginx `error_page 502 503 504 /502.html`. To only update the loading page: **`python scripts/fix_nginx_502_page.py`**.

## Worker killed ~10 seconds after start

Something is killing the uWSGI worker shortly after startup. Check these in order:

1. **systemd start timeout** – If the unit has no `TimeoutStartSec` or a small one (e.g. 10s), systemd can kill the process before workers finish loading (126 blueprints take 60–90s+).  
   - **Fix:** Run **`python fix_502.py`** from your PC to deploy the unit with **`TimeoutStartSec=300`**, then `systemctl daemon-reload` and `systemctl start uwsgi-vidgenerator`.  
   - Or on the server: `sudo systemctl edit uwsgi-vidgenerator.service` and add under `[Service]`: `TimeoutStartSec=300`, then reload and start.

2. **uWSGI harakiri** – If `/var/www/html/uwsgi.ini` has **`harakiri = 10`** (or another small value), uWSGI kills any worker that doesn’t finish a request within that many seconds. The first request (or a slow one) can then kill the only worker.  
   - **Fix:** In `uwsgi.ini` set **`harakiri = 300`** (or remove it to use uWSGI default). Redeploy `uwsgi.ini` or edit on server, then restart uwsgi-vidgenerator.

3. **OOM (out of memory)** – The kernel can kill the process (SIGKILL). Check: `dmesg | tail -30` for "Out of memory" or "Killed process". Add swap if needed (see "worker N died, killed by signal 9" in this doc).

To see who killed the process: `journalctl -u uwsgi-vidgenerator -n 50 --no-pager` and `grep -E 'harakiri|killed|SIGKILL|TimeoutStartSec' /var/www/html/uwsgi.log`.

## If you see "Main process exited, code=killed, status=9" (SIGKILL)

- **When you run `systemctl stop`:** The unit sets `TimeoutStopSec=120`, so systemd waits up to 2 minutes for uWSGI to exit after SIGTERM. **If you still see SIGKILL after ~20 seconds**, the server is using an old unit: run **`python fix_502.py`** from your PC to deploy the updated unit (no ExecStopPost, TimeoutStopSec=120), then `systemctl stop` will allow graceful shutdown.
- **`sh[pid]: 17606 17608` (PIDs in log):** That was from an old `ExecStopPost` that ran `fuser -k 5000/tcp`; it has been removed.
- **When you run fix_502.py:** The script stops the service and runs `fuser -k 5000/tcp` from your PC, so the process is intentionally killed. No action needed if the service comes back up.
- **If "Address already in use" on restart:** Run `python fix_502.py` once, or on the server: `sudo fuser -k 5000/tcp` then `sudo systemctl start uwsgi-vidgenerator`.

## If you see "Main process exited, code=exited, status=1" (exit-code 1)

uWSGI is **crashing** (not being killed). The journal only shows “getting INI configuration” then exit 1; the real error is on stderr. From your PC run:

```bash
python scripts/diagnose_uwsgi_exit_code.py
```

That script runs uwsgi in the foreground on the server and prints the first error (e.g. **chdir permission**, **Python import error**, **port in use**, **uid/gid**, or **CRLF in uwsgi.ini**). Fix that error and restart.
