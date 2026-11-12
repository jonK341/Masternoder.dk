#!/bin/bash
# Social platform fan-out — Discord channels + Facebook Page + YouTube community queue.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${SOCIAL_OPS_SECRET:-${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
curl -sf -X POST "${HOST}/api/social/platforms/fanout/run" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "social platform fanout failed"
