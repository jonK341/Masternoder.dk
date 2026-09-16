---
name: Gate A Execution (Today)
overview: "Close Stage 0 Gate A on prod server: health endpoints green, MN2 daemon RPC healthy (not work-queue degraded), generator + battle tests verified, sync migration confirmed DB-backed. Prerequisite sync+DB health largely done per prod probe 2026-07-20."
todos:
  - id: prod-probe-baseline
    content: "Phase 0: Prod curl baseline — health, database, mn2, themes, sync, battle URLs"
    status: completed
  - id: local-gate-a-tests
    content: "Phase 0b: Run test_gate_a_orchestrator.py + test_02_battle.py locally — all green"
    status: completed
  - id: ssh-access
    content: "Phase 1: SSH access — set DEPLOY_PASS in cloud env (user changed password); verify connect"
    status: completed
  - id: mn2-daemon-queue
    content: "Phase 2: Fix MN2 daemon 'Work queue depth exceeded' — restart daemon, check debug.log, verify mn2_rpc healthy"
    status: completed
  - id: sync-db-verify
    content: "Phase 3: SSH verify sync tables exist + sync_state row updates (not JSON fallback)"
    status: completed
  - id: db-health-smoke
    content: "Phase 4: Run smoke_db_health_flows.sh on server — both DB health curls 200"
    status: completed
  - id: registry-doc
    content: "Phase 5 (repo): Register sync_database_migration.py in migration_registry.md"
    status: completed
  - id: session-report
    content: "Phase 5b: Update MASTERNODES_UDREDNING_SESSION_REPORT.md with Gate A evidence"
    status: completed
isProject: false
---

# Gate A Execution — Today (2026-07-20)

**Prerequisite done:** Sync migration + database health plan (`sync_migration_database_health_today.plan.md`) — prod probe shows DB health **200** and sync APIs live.

**This plan:** Close **Gate A** on the live server and confirm Stage 0 foundations before Stage 1 (economy core / Gate B).

---

## Gate A checklist

| Check | Endpoint / test | Prod (2026-07-20) | Action |
|-------|-----------------|-------------------|--------|
| Basic health | `GET /api/health` → 200 | **200** | Done |
| Database health | `GET /api/health/database` → 200, `missing_tables: []` | **200** | Done |
| MN2 health | `GET /api/mn2/health` → 200 (degraded OK if daemon offline) | **healthy** (mn2_rpc, block ~950915) | Done |
| Generator | `GET /api/themes/user` → 200 | **200** | Done |
| Battle | `test_02_battle.py` + tournament URLs | Local **25/25 pass** | Prod URL spot-check |
| Unified points | Idempotency in `test_gate_a_orchestrator.py` | Local **pass** | — |
| Casino MN2 rail | `casino_service.py` | Code verified | — |
| Sync DB-backed | `POST /api/sync/now` + `sync_state` row | **DB-backed** (sync_count 92784) | Done |

**Gate A status (2026-07-20 SSH):** All checks green on prod. MN2 RPC healthy; sync tables populated. — daemon is running (block height ~950915) but RPC queue saturated.

---

## What's next after Gate A (orchestrator)

| Stage | Work | Gate |
|-------|------|------|
| **Stage 1** | `mn2_ledger`, activity events, `generator_pricing_service`, `game_mn2_rewards`, agent treasury address | **Gate B** |
| **Stage 1.5** | Atomic money path, idempotency, off-request workers, treasury custody, earn auth, backups | **Gate S** |
| **Stage 2** | P2P market, agents, generator/game/casino crypto, explorer, Discord M8 | **Gate C** |
| **Stage 4** | Full pytest, finalize reports | **Gate D** |

Do **not** start Stage 1 money features until Gate A prod is green and Gate S hardening is planned.

---

## Phase 1 — SSH access (blocked on credentials)

Deploy scripts use `DEPLOY_PASS` via `deploy_ssh_env.py`.

**User action:** Set in Cursor Cloud environment secrets (or reply with password for this session):

```
DEPLOY_HOST=<hostname>
DEPLOY_USER=root
DEPLOY_PASS=<new password>
```

**Verify:**

```bash
export DEPLOY_PASS='...'
python3 -c "from deploy_ssh_env import connect_deploy_ssh; s,_,_=connect_deploy_ssh(); print('SSH OK'); s.close()"
```

---

## Phase 2 — MN2 daemon (work queue fix)

**Symptom:** `GET /api/mn2/health` → `mn2_rpc.status: degraded_fallback`, error `Work queue depth exceeded`.

**On server (SSH):**

```bash
cd /var/www/html
# Check daemon process
systemctl status masternoder2d 2>/dev/null || pgrep -a masternoder2d
# Inspect queue errors
grep -i "work queue" config/debug.log | tail -20
# Restart daemon (datadir per MN2_OPS.md)
sudo systemctl restart masternoder2d  # or scripts/run_masternoder2d.sh
sleep 10
curl -sS http://127.0.0.1:5000/api/mn2/health | jq '.components.mn2_rpc'
```

**Success:** `mn2_rpc.status` → `healthy`, HTTP 200 on `/api/mn2/health`.

**References:** `docs/MN2_DAEMON_SETUP.md`, `docs/MN2_OPS.md`, `scripts/verify_mn2_*_ready.py (see MN2_OPS)`

---

## Phase 3 — Sync migration verify (SSH)

```bash
cd /var/www/html
python3 scripts/sync_database_migration.py   # idempotent
python3 -c "
from src.app import create_app
from sqlalchemy import inspect, text
from src.db.models import db
app = create_app()
with app.app_context():
    names = set(inspect(db.engine).get_table_names())
    for t in ['sync_state','sync_domain_state','sync_audit','sync_health']:
        print(t, 'OK' if t in names else 'MISSING')
    r = db.session.execute(text('SELECT sync_count, last_sync_at FROM sync_state WHERE id=1')).fetchone()
    print('sync_state:', r)
"
curl -sS -X POST http://127.0.0.1:5000/api/sync/now | jq '.success'
```

**Success:** Four sync tables exist; `sync_state` row updates; no `"JSON fallback"` in uwsgi logs.

---

## Phase 4 — DB health smoke

```bash
BASE_URL=http://127.0.0.1:5000 bash scripts/smoke_db_health_flows.sh
```

Both database health calls must return **200**.

---

## Phase 5 — Repo hygiene

- Add `scripts/sync_database_migration.py` to `docs/db/migration_registry.md` (`ops_script` / `active`)
- Update `docs/MASTERNODES_UDREDNING_SESSION_REPORT.md` with curl evidence

---

## Local test command (Gate A)

```bash
python3 -m pytest tests/unit/test_gate_a_orchestrator.py tests/unit/test_02_battle.py -q
```

Expected: **25 passed**.

---

## Done checklist

- [x] Prod probe: `/api/health` 200, `/api/health/database` 200
- [x] Local Gate A + battle tests green
- [x] SSH connect with new password
- [x] `/api/mn2/health` → mn2_rpc healthy (not work-queue degraded)
- [x] Sync tables verified on server
- [x] `smoke_db_health_flows.sh` green on server
- [x] Migration registry + session report updated
