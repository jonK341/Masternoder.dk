#!/bin/bash
# Security sweep cron — conservation, drift, deposits, risk, anomaly.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
OPS_SECRET="${MN2_OPS_SECRET:-${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
PRESET="${SECURITY_CRON_PRESET:-sweep}"
if [ -n "${OPS_SECRET}" ]; then
  curl -sf -X POST "${HOST}/api/security/cron/sweep?preset=${PRESET}" \
    -H "X-Ops-Secret: ${OPS_SECRET}" \
    -H "Content-Type: application/json" \
    -d "{\"preset\":\"${PRESET}\"}" || echo "security sweep failed"
  exit 0
fi
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
TOKEN=""
if [ -f "$ENV" ]; then
  TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
fi
[ -n "${TOKEN:-}" ] || { echo "security sweep skipped: no ops/cron secret"; exit 0; }
curl -sf -X POST "${HOST}/api/agents/cron/run?jobs=security" \
  -H "X-Agent-Cron-Token: ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"jobs":["security_sweep"]}' || echo "security sweep failed"
