#!/bin/bash
# Gate S: daily MN2/economy backup (ledger, unified_points, SQLite).
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
curl -sf -X POST "${HOST}/api/security/cron/backup" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "mn2 backup failed"
