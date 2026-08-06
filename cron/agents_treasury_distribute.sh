#!/bin/bash
# Idempotent treasury pool → trader agent funding distribution.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
curl -sf -X POST "${HOST}/api/agents/treasury/distribute" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "treasury distribute failed"
