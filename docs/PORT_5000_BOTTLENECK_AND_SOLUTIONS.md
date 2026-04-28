# Port 5000 bottleneck and how to reduce lag

## Run all steps (one command)

From your PC:

```bash
python scripts/run_bottleneck_fixes.py
```

This runs in order: (1) add swap on server if missing, (2) patch nginx to use upstream `flask_backend` (5000 + 5001), (3) deploy and start the second uWSGI on 5001, (4) deploy updated systemd units (LITE_APP=1) and restart `uwsgi-vidgenerator`. Use `--skip-swap` if you already have enough swap.

Alternatively: **`python fix_502.py`** installs both systemd units (5000 and 5001) and starts both; then run **`python scripts/enable_nginx_upstream.py`** once so nginx sends traffic to both backends.

---

## Synopsis: the bottleneck

- **Single entry point:** Nginx sends **all** traffic for `masternoder.dk` to **one** backend: `http://127.0.0.1:5000` (or, after running the fixes, to upstream `flask_backend` with 5000 + 5001).
- **One uWSGI app:** One or two process groups listen on 5000 and optionally 5001. Each runs the same Flask app (full or LITE_APP subset).
- **Limited concurrency:** With one port, `uwsgi.ini` uses **4 processes × 2 threads = 8 workers** per instance. With two backends you double that.
- **Heavy endpoints:** Pages like the generator or profile trigger many API calls at once (frontpage/init, points/all, battle/stats, stats/summary, etc.). A single page load can need 10+ requests; with 4 workers most of them queue and hit nginx/uWSGI timeouts (~15–300s), so users see long waits or timeouts.
- **RAM constraint:** The comment in `uwsgi.ini` says “Use 1 process to avoid OOM; increase to 2 if RAM allows.” So worker count was already capped to avoid the kernel killing the process (signal 9). More workers on the **same** app = more RAM; without enough RAM or swap, adding workers can cause OOM and make things worse.

**Bottom line:** Everything goes to one port, one app, and a small number of workers. That’s the bottleneck. To kill the lag you either add capacity on the same port (more workers, limited by RAM) or add capacity elsewhere (extra port(s) and/or split traffic).

---

## Possible solutions

### 1. More workers on the same port (easiest to try)

**Idea:** Increase concurrency on 5000 so more requests are handled at once.

- In **`uwsgi.ini`** raise **`processes`** and/or **`threads`** (e.g. `processes = 4`, `threads = 4` → 16 workers). Same app, same port, no nginx change.
- **Pros:** No nginx or routing changes; one config change and restart.
- **Cons:** Each process loads the full app (126 blueprints). More processes = much more RAM; on a small VPS you risk OOM (worker killed, signal 9). Check free RAM and swap before increasing; add swap if needed (`scripts/server_add_swap.py`).
- **Suggested step:** If the server has enough RAM, try `processes = 3` or `processes = 4` and `threads = 2` (or 4). Restart: `sudo systemctl restart uwsgi-vidgenerator`. Monitor with `dmesg | tail` and `free -h`; if you see “Killed” or OOM, add swap or reduce back.

---

### 2. Redirect / split traffic to another port (more workers via a second uWSGI)

**Idea:** Run **two** uWSGI instances (same app): one on 5000, one on 5001. Nginx sends traffic to **both** (e.g. round‑robin). You effectively double (or more) the number of workers without putting them all in one process group.

- **Server:**  
  - Keep current `uwsgi-vidgenerator` on port 5000 (e.g. `processes = 2`, `threads = 2`).  
  - Add a second unit, e.g. `uwsgi-vidgenerator-5001`, using the same `uwsgi.ini` but with a different **config override** so it binds to `127.0.0.1:5001` (e.g. a second ini that only overrides `http-socket = 127.0.0.1:5001`).
- **Nginx:**  
  - Define an **upstream** with both ports, e.g.  
    `upstream flask_backend { server 127.0.0.1:5000; server 127.0.0.1:5001; }`  
  - Set `proxy_pass http://flask_backend` in the `location /` (and any other blocks that currently use `proxy_pass http://127.0.0.1:5000`).
- **Pros:** More total workers (e.g. 4 + 4 = 8) without changing a single process’s memory; nginx spreads load. Same app code and deploy.
- **Cons:** Two systemd units to maintain; RAM still grows (each instance loads the full app). You need enough RAM for two uWSGI stacks.

---

### 3. Split by path: heavy APIs on a second port

**Idea:** Send only **heavy** or **slow** API paths to a dedicated backend on another port (e.g. 5001), so they don’t block the main app on 5000.

- **Nginx:**  
  - `location /api/points/` → `proxy_pass http://127.0.0.1:5001`
  - `location /api/frontpage/` → `proxy_pass http://127.0.0.1:5001`
  - (Optional) other heavy paths to 5001.  
  - `location /` → keep `proxy_pass http://127.0.0.1:5000`.
- **Server:** Run a second uWSGI instance (same app) on 5001, e.g. with 2 processes × 2 threads, so heavy endpoints get dedicated workers.
- **Pros:** Main traffic (pages, light APIs) stays on 5000; heavy calls don’t starve the rest.  
- **Cons:** Two units; same app runs twice (RAM). If 5001 is underpowered, those endpoints can still be slow.

---

### 4. LITE_APP: fewer blueprints, less RAM, more room for workers

**Idea:** Reduce app size so each worker uses less memory; then you can safely run more workers on the same (or same + extra) port.

- Set env **`LITE_APP=1`** (e.g. in `uwsgi-vidgenerator.service` or override). The app then registers only ~25 critical blueprints (see `backend/register_blueprints.py`). Same pages/APIs you use for the main site; fewer optional ones.
- **Pros:** Lower RAM per process, faster startup, less risk of OOM when you raise `processes` or add a second port.
- **Cons:** Some routes may not be registered; only enable if the lite set covers what you need (docs: SERVER_QUICK_REFERENCE.md, migration Phase 1.2).

---

### 5. Caching and slow-endpoint hardening

**Idea:** Reduce how often heavy work runs and how long it holds a worker.

- **Caching:** Cache responses for heavy GETs (e.g. `/api/points/all`, `/api/stats/summary`) in Redis or in-process with a short TTL so repeated requests don’t hit the DB every time.
- **Timeouts / optimization:** Ensure heavy endpoints either finish within harakiri or are optimized; add indexes or simplify queries so they don’t hold workers for 30+ seconds.
- **Pros:** Less contention on the same 4 workers; fewer timeouts.
- **Cons:** Requires code and possibly new infrastructure (e.g. Redis); doesn’t by itself add more workers.

---

## Quick comparison

| Approach                         | Effort | Effect on lag              | RAM / risk   |
|---------------------------------|--------|----------------------------|--------------|
| More workers (same port)        | Low    | More concurrent requests   | Higher, OOM  |
| Second port, same app (upstream)| Medium | More workers total         | Higher, 2×   |
| Split heavy APIs to second port | Medium | Isolate slow calls         | Higher, 2×   |
| LITE_APP + more workers         | Low    | More workers without OOM   | Lower        |
| Caching / optimize endpoints    | Higher | Fewer long requests        | Same         |

---

## Implemented (what’s in the repo)

- **Swap:** `scripts/server_add_swap.py` — run once if the server has no swap.
- **More workers on 5000:** `uwsgi.ini` has `processes = 4`, `threads = 2` (8 workers per instance).
- **Second backend (5001):** `systemd/uwsgi-vidgenerator-5001.service`; deploy/start with `scripts/enable_second_backend.py` or via `fix_502.py` (Step 2e2 + 3b).
- **Nginx upstream:** `scripts/enable_nginx_upstream.py` adds `upstream flask_backend { server 127.0.0.1:5000; server 127.0.0.1:5001; }` and `proxy_pass http://flask_backend`.
- **LITE_APP=1:** Set in both `uwsgi-vidgenerator.service` and `uwsgi-vidgenerator-5001.service` for lower RAM and faster startup.
- **Caching:** Heavy GETs (`/api/points/all`, `/api/stats/summary`, `/api/frontpage/init`) use `@cached_response(ttl=60)` (or 30s for frontpage/init) in `backend/routes/points_routes.py` and `backend/routes/missing_endpoints_routes.py` via `backend/middleware/response_cache_middleware.py`.

**One-shot:** `python scripts/run_bottleneck_fixes.py` runs swap, nginx upstream, second backend, and restarts with updated units.

All of this keeps the “root masternoder.dk” setup; you’re only changing how many backends serve it and how traffic is distributed across them.
