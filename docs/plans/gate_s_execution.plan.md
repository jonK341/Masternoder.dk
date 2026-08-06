---
name: Gate S Execution (Stage 1.5 Hardening)
overview: "Close Gate S before Stage 2 money features: atomic money path, earn auth, treasury ops-only, admin audit, backups, rate limits."
todos:
  - id: admin-audit-service
    content: "admin_audit_service.py — append-only logs/admin_audit.jsonl"
    status: completed
  - id: backup-service
    content: "backup_service.py + POST /api/security/cron/backup + cron/mn2_backup.sh"
    status: completed
  - id: treasury-hardening
    content: "Treasury address ops-only; sign-off route; distribute gated + audited"
    status: completed
  - id: earn-rate-limits
    content: "Rate limits on game/battle/starmap/generator/mn2 earn paths"
    status: completed
  - id: gate-s-tests
    content: "test_gate_s_orchestrator.py + test_gate_b_orchestrator.py all green"
    status: completed
  - id: prod-deploy
    content: "Deploy Gate S services to prod + run first backup via cron endpoint"
    status: pending
isProject: false
---

# Gate S Execution — Stage 1.5 Hardening

**Prerequisite:** Gate A closed on prod (2026-07-20).

**Blocks:** All Stage 2 money features (market, generator pay/earn, casino crypto, game rewards, agent funding).

---

## Gate S checklist

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Atomic + locked money writes | `unified_points_database.py` per-user lock + `os.replace` | Done |
| Idempotency on money credits | `reference` in metadata + `_IDEMPOTENCY_CACHE` | Done |
| Earn auth (no anon/default_user) | `mn2_earn_auth.require_earn_user` | Done |
| Rate limits on earn paths | `rate_limit_middleware.py` game/battle/starmap/generator | Done |
| Treasury ops-only address | `GET /api/agents/treasury/address` requires ops secret | Done |
| Treasury sign-off before 100k+ batch | `treasury_signoff_service` + `POST /sign-off` | Done |
| Admin audit log | `admin_audit_service.py` → `logs/admin_audit.jsonl` | Done |
| Backup job | `backup_service.py` + `cron/mn2_backup.sh` | Done |
| Conservation / reconcile cron | `security_cron_routes` sweep | Existing |

---

## Services added

- `backend/services/admin_audit_service.py` — append-only audit for treasury/ops actions
- `backend/services/backup_service.py` — backs up ledger, unified_points, SQLite, config
- `cron/mn2_backup.sh` — daily backup via `POST /api/security/cron/backup`

## Routes hardened

- `GET /api/agents/treasury/address` — ops-only (public gets `ops_only: true`, no address)
- `GET|POST /api/agents/treasury/sign-off` — cold-wallet sign-off before large batches
- `POST /api/agents/treasury/distribute` — sign-off gate + audit log
- `POST /api/security/cron/backup` — ops/cron backup trigger

---

## Test command

```bash
python3 -m pytest tests/unit/test_gate_s_orchestrator.py tests/unit/test_gate_b_orchestrator.py -q
```

Expected: **11 passed**.

---

## Prod deploy

```bash
export DEPLOY_PASS='...'
python3 scripts/deploy.py mn2_env   # or targeted upload of Gate S files
curl -X POST -H "X-Ops-Secret: $ADMIN_OPS_SECRET" http://127.0.0.1:5000/api/security/cron/backup
```

---

## Next after Gate S: Stage 2 / Gate C

Market, generator-crypto, game-rewards, casino-crypto — each must emit `activity_events` and pass tests.
