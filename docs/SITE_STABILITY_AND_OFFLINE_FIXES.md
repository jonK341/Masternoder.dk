# Site Keeps Going Offline – Brainstorm and Fixes

## What “offline” usually means

- **502 Bad Gateway** – nginx can’t reach the app on port 5000 (nothing listening or app crashed).
- **504 Gateway Timeout** – app is slow; nginx gives up before the app answers.
- **000 / timeout** – same as 502 from the client’s point of view (no response).

---

## Why the vidgenerator app might go offline or “get kicked”

1. **fix_502.py (or any script that restarts uwsgi)**  
   Every run **stops** `uwsgi-vidgenerator` and frees port 5000, then starts it again. So the site is down for ~15–30 seconds each time. **Avoid running fix_502 unless you need to fix 502 or after a deploy.**

2. **Old LSB `uwsgi.service` on boot**  
   The legacy “Start/stop uWSGI server instance(s)” service can start on boot, fail (“...fail!”), and cause confusion or conflict. **Fix:** disable it so only `uwsgi-vidgenerator` runs:
   ```bash
   sudo systemctl disable uwsgi
   ```
   `fix_502.py` now runs this for you.

3. **Workers killed by harakiri**  
   If a request takes longer than `harakiri` seconds (e.g. first request loading 123 blueprints), uWSGI kills that worker. If all workers are busy or killed, the site stops responding. **Fix:** increase `harakiri` in `vidgenerator/uwsgi.ini` (e.g. 300). Done in this repo.

4. **Out-of-memory (OOM)**  
   The app is large (many blueprints). With 4 workers all loading at once, a small VPS can run out of memory and the OOM killer can kill uWSGI. **Fix:** use `lazy-apps = true` in uwsgi.ini so workers load the app on first request, not all at once. Done in this repo. You can also reduce `processes` to 2 if memory is tight.

5. **Port 5000 taken by something else**  
   After a reboot or after another script, `gunicorn`, `python-proxy`, or the old `uwsgi` might bind to 5000. Then nginx talks to the wrong process (or it fails and you get 502). **Fix:** disable those services (`systemctl disable vidgenerator-gunicorn`, `disable uwsgi`), and only start the app with `uwsgi-vidgenerator`. fix_502.py already disables gunicorn and uwsgi.

6. **Restart loop**  
   If the app crashes right after start (e.g. import error, missing file), systemd keeps restarting it (Restart=always). The site may look “offline” or only work for a few seconds. **Fix:** check logs:
   ```bash
   journalctl -u uwsgi-vidgenerator -n 100 --no-pager
   tail -200 /var/www/html/vidgenerator/uwsgi.log
   ```
   Fix the underlying crash (import, path, permissions).

7. **Log write errors**  
   Multiple workers writing to the same log can cause “OSError: write error” and noise. **Fix:** `log-master = true` in uwsgi.ini (only master writes). Done in this repo.

---

## Checklist to keep the site stable

- [ ] **Only one service on port 5000**  
  Use only `uwsgi-vidgenerator`. Disable `uwsgi`, `vidgenerator-gunicorn`, and avoid starting `python-proxy` for 5000.

- [ ] **Disable LSB uwsgi on boot**  
  Run once (or use fix_502.py):  
  `systemctl disable uwsgi`

- [ ] **Don’t run fix_502.py unnecessarily**  
  It stops the app and restarts it. Use it after deploy or when you have 502.

- [ ] **Use lazy-apps and higher harakiri**  
  In `vidgenerator/uwsgi.ini`: `lazy-apps = true`, `harakiri = 300`. Deploy and restart.

- [ ] **After deploy, restart once**  
  `python fix_502.py` (or on server: `systemctl restart uwsgi-vidgenerator`). Then wait 30–60 s before testing; first request can be slow.

- [ ] **If the site is still flaky**  
  Check restart count:  
  `systemctl show uwsgi-vidgenerator -p NRestarts`  
  If it keeps increasing, the process is exiting; use journalctl and uwsgi.log to find the cause.

---

## Quick test (HTTPS)

From your machine (allow up to 45 s for first response):

```bash
curl -s -o /dev/null -w "%{http_code}" -m 45 https://masternoder.dk/
curl -s -o /dev/null -w "%{http_code}" -m 45 https://masternoder.dk/vidgenerator/
```

200 = app is up. 000 = timeout (app not responding or very slow). 502 = nothing on 5000 or crash.

---

## All pages registration

The Flask app **registers all pages automatically** from `backend/routes/all_page_routes.py`: the `PAGES` list is used to create routes for `/vidgenerator/<page>/`. No extra “todo” is required for registration; add new subdirs with `index.html` to `PAGES` if you add new pages.
