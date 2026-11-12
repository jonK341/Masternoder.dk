#!/bin/bash
# M7 Staking Yield Advisor refresh cron (off-request).
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
USER_ID="${STAKING_ADVISOR_USER_ID:-ops_batch}"
curl -sf -X POST "${HOST}/api/ai/staking-advisor/refresh" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${USER_ID}\"}" || echo "staking advisor refresh failed"
