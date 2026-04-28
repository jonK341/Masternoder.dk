# Backend ports: what stays, what moves, when to use 5002

**Decision date:** 2026-03-24  
**Goal:** One simple default, optional scale-out, avoid port sprawl.

---

## Summary (what to use)

| Port   | Role | Keep? |
|--------|------|--------|
| **5000** | **Primary** uWSGI → Flask app. Nginx (and cron/scripts) should target **this** by default. | **Yes — this is the canonical app port.** |
| **5001** | **Optional second** uWSGI (same codebase, load spreading with nginx `upstream` round-robin). | **Only if** you need extra worker capacity on one machine. Otherwise **disable** `uwsgi-vidgenerator-5001` and run a single stack on **5000** only. |
| **5002** | **Not used** in the default design. | **Do not add** unless you have a **specific** split (see below). |

**Recommendation:** Prefer **one** uWSGI on **127.0.0.1:5000** + nginx → that. Add **5001** only when metrics show queueing / CPU-bound workers and you want a second full instance without tuning `processes`/`threads` further.

---

## Why 5000 should stay the “main” one

- **Convention:** Tools, docs, `run.py` default, `AGENT_DAEMON_URL`, crons, and `service_check_all_components.py` assume **5000** unless you override `PLATFORM_BASE_URL`.
- **Less churn:** Moving “everything” to 5001 means editing nginx, every cron, MN2 scanner URL, deploy probes, etc.
- **Mental model:** “App lives on 5000” — second port is **optional capacity**, not the primary name.

---

## When 5001 stays (second instance)

Keep **`uwsgi-vidgenerator-5001`** + **`uwsgi_5001.ini`** when:

- Nginx uses `upstream flask_backend { server 127.0.0.1:5000; server 127.0.0.1:5001; }` (or equivalent), **and**
- You actually run **both** units and both return HTTP 200.

If you only need **one** backend: **stop and disable** `uwsgi-vidgenerator-5001`, point nginx **only** at **5000**, and simplify scripts that restart “both” backends.

---

## When 5002 would ever make sense (rare)

Use a **third** port only if you deliberately split **by traffic class**, for example:

- Long-running or CPU-heavy routes isolated so they don’t starve page/API traffic, **or**
- A separate experimental/staging app on the same host (unusual).

**Default:** **No 5002.** It duplicates systemd, logs, deploy steps, and nginx `location` rules without benefit for typical traffic.

If you ever need isolation, prefer first:

1. Tune **`uwsgi_common.ini`** (`processes`, `threads`, `listen`),  
2. Add a **second** full app on **5001** with nginx upstream,  
3. Only then consider a **dedicated** 5002 + narrow `location` blocks.

---

## Migration cheat sheet

| If you want… | Do this |
|--------------|---------|
| **Simplest prod** | Single uWSGI on **5000** only; disable 5001 unit; nginx → `127.0.0.1:5000`. |
| **More capacity, same server** | Keep **5000 + 5001**, separate pidfiles, nginx upstream to both. |
| **“Only 5001”** | Possible but **not recommended** — you must change nginx + all `127.0.0.1:5000` references; easier to keep **5000** as primary. |
| **5002** | Only with a **documented** reason (heavy API split, etc.); otherwise skip. |

---

## Related docs / files

- Second instance details: `docs/UWSGI_SECOND_INSTANCE.md`
- Nginx upstream / bottleneck context: `docs/PORT_5000_BOTTLENECK_AND_SOLUTIONS.md`
- uWSGI: `uwsgi.ini` (5000), `uwsgi_5001.ini` (5001), `uwsgi_common.ini` (shared)
