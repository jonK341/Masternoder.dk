#!/bin/bash
# Trader agent market-maker tick — keeps P2P order book liquid.
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
OPS=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
if [ -n "${TOKEN:-}" ]; then
  curl -sS -X POST -H "X-Agent-Cron-Token: $TOKEN" \
    "http://127.0.0.1:5000/api/agents/cron/run?jobs=agent_trader" >/dev/null
elif [ -n "${OPS:-}" ]; then
  curl -sS -X POST -H "X-Ops-Secret: $OPS" \
    "http://127.0.0.1:5000/api/agents/cron/run?jobs=agent_trader" >/dev/null
else
  curl -sS -X POST "http://127.0.0.1:5000/api/agents/cron/run?jobs=agent_trader" >/dev/null
fi
