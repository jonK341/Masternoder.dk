#!/bin/bash
# M8 #52 — rotate shop promo codes in Discord #announcements (Mon/Wed/Fri cron)
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-${MN2_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
curl -sf -X POST "${HOST}/api/discord/m8/promo-rotator" \
  ${SECRET:+-H "X-Ops-Secret: ${SECRET}"} \
  -H "Content-Type: application/json" \
  -d '{}' || echo "discord promo rotator failed"
