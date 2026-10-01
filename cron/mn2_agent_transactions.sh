#!/bin/bash
# MN2 agent transaction settlement — every 2 min: daemon probe, battle/aggregator/generator/casino/staking.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || ENV="/workspace/.env"
[ -f "$ENV" ] || ENV="$(dirname "$0")/../.env"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep -E '^MN2_OPS_SECRET=|^MN2_SCAN_SECRET=|^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST \
  -H "X-Ops-Token: $TOKEN" \
  -H "X-Agent-Cron-Token: $TOKEN" \
  "http://127.0.0.1:5000/api/agent/mn2/transactions/run?systems=all" >/dev/null
