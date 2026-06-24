#!/bin/bash
# Game MN2 rewards / battle events → Discord #game
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${MN2_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
curl -sf -X POST "${HOST}/api/discord/game/fanout" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "discord game fanout failed"
