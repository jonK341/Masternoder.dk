#!/bin/bash
# Run trader agent market-making tick (place sells + cross-fill).
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
curl -sf -X POST "${HOST}/api/agents/control/trader/run" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "agent trader cron failed"
