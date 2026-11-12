#!/bin/bash
# Security sweep cron — withdrawal risk, reconciliation hints, session cleanup trigger.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
curl -sf -X POST "${HOST}/api/security/cron/sweep" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "security sweep failed"
