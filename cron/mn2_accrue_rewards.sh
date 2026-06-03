#!/bin/bash
# MN2 staking reward accrual — triggered by cron. Reads MN2_OPS_SECRET (or MN2_SCAN_SECRET) from app .env.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^MN2_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
# Accrue staking rewards, then clear matured on-ramp / P2P holds (releases withdrawals + seller payouts).
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/staking/ops/accrue" >/dev/null
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/onramp/ops/clear-matured" >/dev/null
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/p2p/ops/clear-matured" >/dev/null
# Drive the autonomous staking personas one policy step (heartbeat, auto-restake, rebalance within caps).
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/agent/staking/ops/run-all" >/dev/null
# Conservation invariant (sec.8): non-zero exit / 409 body signals drift — log it for ops to alert on.
RECON=$(curl -s -S -o /dev/null -w "%{http_code}" -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/staking/ops/reconcile")
[ "$RECON" = "200" ] || echo "[mn2] reconcile drift: HTTP $RECON at $(date -u +%FT%TZ)" >&2
