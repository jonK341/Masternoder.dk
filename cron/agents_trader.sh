#!/bin/bash
# Run trader agent market-making tick (place sells + cross-fill).
# Prefers agents control board (ops secret); falls back to agent cron job.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
OPS_SECRET="${MN2_OPS_SECRET:-${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
if [ -n "${OPS_SECRET}" ]; then
  curl -sf -X POST "${HOST}/api/agents/control/trader/run" \
    -H "X-Ops-Secret: ${OPS_SECRET}" \
    -H "Content-Type: application/json" \
    -d '{}' || echo "agent trader cron failed"
  exit 0
fi
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
TOKEN=""
if [ -f "$ENV" ]; then
  TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
fi
[ -n "${TOKEN:-}" ] || { echo "agent trader cron skipped: no ops/cron secret"; exit 0; }
curl -sf -X POST "${HOST}/api/agents/cron/run?jobs=trader" \
  -H "X-Agent-Cron-Token: ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"jobs":["agent_trader"]}' || echo "agent trader cron failed"
