# 504 Gateway Timeout and 502 Bad Gateway

When the profile (or other pages) show **504 Gateway Timeout** or **502 Bad Gateway** on API calls, the reverse proxy (nginx) is either waiting too long for the app (504) or the app crashed/refused the connection (502).

## Causes

- **504**: uWSGI/Flask took longer than the proxy timeout (e.g. 60s). Often due to:
  - **Harakiri**: uWSGI kills a worker after `harakiri` seconds. Default can be 30s. Long-running or many concurrent requests can hit this.
  - **Nginx**: `proxy_read_timeout` (e.g. 60s) – nginx gives up waiting for the backend.
- **502**: Backend not responding (worker died, app crash, or not listening).

If you fixed 502 (e.g. with `fix_502.py`) and now get **504**, the backend is reachable but responses are slower than nginx’s read timeout. Increase nginx proxy timeouts (and optionally uWSGI harakiri) as below.

## Why 502 can keep coming back

Even after running `fix_502.py` or deploy, 502 can return because:

1. **Several services can use port 5000**  
   Nginx proxies to `127.0.0.1:5000`. The intended backend there is **uWSGI**. But **vidgenerator-gunicorn** and **python-proxy** also bind to port 5000 in some setups. If any of these is **enabled** and starts (e.g. on boot or after another script), it can grab 5000 before uWSGI, or conflict with it. Result: wrong app on 5000 or nothing listening → 502.

2. **vidgenerator-gunicorn is only stopped, not disabled**  
   The fix scripts stop `vidgenerator-gunicorn` and kill gunicorn processes, but by default they do not run `systemctl disable vidgenerator-gunicorn`. So after a **server reboot**, that service can start and take port 5000; uWSGI may then fail to bind or bind elsewhere, and nginx still talks to 5000 → 502.

3. **Different scripts assume different backends on 5000**  
   - `fix_502.py` and `deploy_all_and_restart_uwsgi.py` assume **uWSGI** on 5000 (they kill gunicorn/python-proxy and start uwsgi).  
   - Other deploy/route scripts (e.g. `fix_gateways.py`, `deploy.py`, `ensure_flask_routes_registered.py`) **restart python-proxy** and expect it on 5000.  
   If you run fix_502 and then run one of those scripts, python-proxy may be started again and contend for 5000, or replace uWSGI, leading to 502 or wrong app.

4. **uWSGI failing to start**  
   If uWSGI crashes on start (bad config, missing module, permission, or port in use), nothing is listening on 5000 → 502. Check `journalctl -u uwsgi` and `/var/www/html/vidgenerator/uwsgi.log`.

5. **Workers crashing (e.g. “Working outside of application context”)**  
   If the uwsgi log shows this and workers are “buried”, a route or helper is using the DB or Flask context when none is active. The codebase has been updated so `get_user_level_info` and similar helpers return safe defaults instead of crashing. Deploy the latest code and restart uWSGI (see “Fix 502 from your machine” below).

**One-time hardening (on the server):** Disable services that must not use port 5000 so they don’t start on boot:

```bash
sudo systemctl stop vidgenerator-gunicorn
sudo systemctl disable vidgenerator-gunicorn
```

Then use **one** canonical way to put the app on 5000 (uWSGI via `fix_502.py` or `deploy_all_and_restart_uwsgi.py`) and avoid scripts that start python-proxy for 5000 unless that’s your chosen backend. To inspect current state: `python scripts/investigate_502.py`.

## Fix 502 from your machine

1. **Deploy the latest code** (includes the app-context fix in `backend/routes/hunters_game.py` so workers don’t crash):
   ```bash
   python scripts/deploy_all_and_restart_uwsgi.py
   ```
   This uploads code and restarts uWSGI. If you already get 502 and deploy fails or times out, run step 2 first, then deploy with `--no-upload` or run step 2 again.

2. **If the site still returns 502**, free port 5000 and start uWSGI:
   ```bash
   python fix_502.py
   ```

## Fix 504 quickly (from your machine)

If the site now returns **504 Gateway Timeout** (backend is up but nginx gives up waiting):

```bash
python scripts/fix_504_timeouts.py
```

This updates nginx so `proxy_connect_timeout`, `proxy_send_timeout`, and `proxy_read_timeout` are 120s for the app backend, then reloads nginx. Use `--dry-run` to see what would be changed without applying.

If 504 persists, also increase uWSGI `harakiri` (and optionally worker count) as below.

## Fixes on the server

### 1. Increase uWSGI timeouts

Edit the vidgenerator uWSGI config (e.g. `/var/www/html/vidgenerator/uwsgi.ini` or the one in `/etc/uwsgi/apps-enabled/`):

```ini
# Allow a request to run longer before worker is killed (seconds)
harakiri = 120
# Socket timeout
socket-timeout = 120
```

Then restart uWSGI:

```bash
sudo systemctl restart uwsgi
```

### 2. Increase nginx proxy timeouts

In the server block that proxies to the Flask app (e.g. `location /vidgenerator/`):

```nginx
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

Then reload nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Restart the app

If the app is unstable (502 after load), restart and watch logs:

```bash
sudo systemctl restart uwsgi
sudo journalctl -u uwsgi -f
# or
tail -f /var/log/uwsgi/app/vidgenerator.log
```

### 4. From your machine

Run the project fix script to restart uWSGI and free port 5000:

```bash
python fix_502.py
```

Then deploy the latest code (including profile static assets) so 404s and timeouts are reduced:

```bash
python scripts/deploy.py profile
# or full sync/static
python scripts/deploy.py rewind_missing
```

## Reducing timeouts in the app

- Avoid heavy work in the request path (move to background tasks if possible).
- Ensure DB and external calls have reasonable timeouts and error handling.
- If many concurrent requests hit the same worker, consider increasing `processes`/`threads` in uwsgi.ini (within server resource limits).

---

## Why the site feels very slow (e.g. 2 minutes to load)

Slow page loads are usually a combination of:

1. **Backend slow or timing out**  
   If API requests return 504/502 or take 60+ seconds, the page waits on them. Fix timeouts and worker capacity as above; check uWSGI/Flask logs for slow routes or DB queries.

2. **Too many API calls on each page**  
   Profile (and other pages) trigger many requests on load: user identity, profile display, sync status, stats summary, achievements, battles, points, trophies, milestones, currency, notifications. With few uWSGI workers, these queue and many can hit the read timeout (e.g. 60s), so total wait can feel like 1–2 minutes.

3. **Frontend changes that help**
   - `stats-achievements-tracker.js` now fetches its 7 stats endpoints **in parallel** (no longer one-by-one), so that block takes ~max(one request) instead of the sum.
   - Stats tracker poll interval was increased from 10s to 30s to reduce server load.

4. **What to do on the server**
   - Increase uWSGI **workers** (e.g. `processes = 4` in uwsgi.ini) so more requests are handled at once.
   - Increase **harakiri** and nginx **proxy_read_timeout** as in the sections above so slow requests don’t fail as 504.
   - Optimize slow API routes (DB queries, N+1, external calls); add timeouts and caching where possible.

---

## Generator progress (cross-worker)

The documentary progress endpoint (`GET /api/documentary/progress/<doc_id>`) is safe for multi-worker uWSGI: it **prefers the sidecar file** (and DB when used) over in-memory job state, so any worker can serve progress for a job started on another worker. Progress is written to a `.status.json` sidecar next to the video output; the API reads that first so polling works regardless of which worker handles the request.
