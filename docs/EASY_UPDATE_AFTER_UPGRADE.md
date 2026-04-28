# Easy Update After Upgrade — No Server Reboot

**Problem:** After deploying new code, the browser sometimes still shows the old interface. The only fix used to be a hard reset of the Ubuntu web server.

**Solution:** Use the **apply updates** flow below. No reboot, no hard reset.

---

## One Command (from your machine)

After you deploy (or after any upgrade), run:

```bash
python scripts/apply_updates.py
```

This will:

1. Clear Python cache (`__pycache__`, `.pyc`) on the server  
2. Purge nginx cache (if any)  
3. Restart app services in the correct order:
   - uwsgi-vidgenerator (primary app on :5000)
   - uwsgi-vidgenerator-5001 (optional second app worker)
   - python-proxy (if enabled for compatibility)
4. Reload nginx  
5. Ensure no-cache headers for generator, trophies, and service worker  

**No server reboot.** Users can refresh with **Ctrl+F5** (or wait for the `/api/version` check to trigger a reload).

---

## From the server (SSH)

If you are already on the server (e.g. after `git pull`):

```bash
cd /var/www/html && bash scripts/production_apply_routes.sh
```

Or from your machine:

```bash
ssh root@masternoder.dk "cd /var/www/html && bash scripts/production_apply_routes.sh"
```

This script:

- Clears Python cache  
- Purges nginx cache  
- Ensures uWSGI/python-proxy PYTHONPATH  
- Restarts uwsgi-vidgenerator → uwsgi-vidgenerator-5001 → python-proxy → reload nginx  
- Runs a quick route check  

Do not start the legacy `uwsgi` wrapper for this app. It can bind the same port as `uwsgi-vidgenerator` and serve stale/no-app workers.

Again, **no reboot**.

---

## Why the browser was stuck on old UI

1. **Server caches** – Python bytecode or nginx cache serving old content.  
2. **Browser cache** – Cached HTML/CSS/JS.  
3. **Service worker** – Old service worker caching pages.  

What we do:

- **Server:** Clear `__pycache__`, `.pyc`, and nginx cache; restart app services so new code runs.  
- **Browser:**  
  - Nginx sends `Cache-Control: no-store` for generator, trophies, and service-worker.js so new visits get fresh HTML.  
  - Service worker version is bumped on deploy (`CACHE_NAME` in `service-worker.js`) so updated SW replaces the old one and drops old caches.  
  - Pages that call `/api/version` can reload when the server version is newer.  

So you get a **reliable way to update the system** after an upgrade **without** rebooting the server.

---

## Optional: run apply after every deploy

You can run apply right after deploy:

```bash
python scripts/deploy_vidgenerator_solution.py && python scripts/apply_updates.py
```

Or add a call to `apply_updates` at the end of your deploy script. The deploy script already prints:

```
If browser still shows old UI (no reboot needed):
  python scripts/apply_updates.py
```

---

## Files involved

| File | Purpose |
|------|--------|
| `scripts/apply_updates.py` | Single command from your machine: clear caches, restart services, no-cache setup. No reboot. |
| `scripts/production_apply_routes.sh` | Run on server: clear caches, fix PYTHONPATH, restart services, reload nginx. |
| `scripts/setup_generator_no_cache.py` | Ensures nginx sends no-cache for generator, trophies, service-worker.js. |
| `vidgenerator/service-worker.js` | Bump `CACHE_NAME` (e.g. date) on deploy so browsers pick up new SW. |

---

## Summary

- **No Ubuntu reboot** – use `apply_updates.py` or `production_apply_routes.sh`.  
- **One command** – `python scripts/apply_updates.py` after deploy.  
- **Browser** – Ctrl+F5 or rely on `/api/version` and no-cache headers + new service worker version.

This is the intended way to update the system after an upgrade.
