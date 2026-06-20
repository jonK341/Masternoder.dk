#!/bin/bash
# Casino agent play loop — all specialized personas take one leaderboard bet each.
# Requires AGENT_CRON_SECRET or AGENT_CASINO_SECRET in app .env.
set -euo pipefail
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || ENV="$(dirname "$0")/../.env"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep -E '^(AGENT_CASINO_SECRET|AGENT_CRON_SECRET)=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
curl -s -S -X POST \
  -H "X-Agent-Cron-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  "${HOST}/api/agents/cron/run?jobs=casino" >/dev/null || \
curl -s -S -X POST \
  -H "X-Agent-Casino-Key: $TOKEN" \
  -H "Content-Type: application/json" \
  "${HOST}/api/agent/casino/ops/run-all" >/dev/null || echo "casino agents cron failed"
