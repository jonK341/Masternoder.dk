#!/bin/bash
# P2P market agent demo — seed listings + simulate trades every ~2 min.
# Uses MN2_OPS_SECRET (or MN2_SCAN_SECRET / AGENT_CRON_SECRET) from app .env.
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep -E '^MN2_OPS_SECRET=|^MN2_SCAN_SECRET=|^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST \
  -H "X-Ops-Token: $TOKEN" \
  -H "X-Agent-Cron-Token: $TOKEN" \
  "http://127.0.0.1:5000/api/mn2/p2p/ops/agent-seed?target_listings=10&max_trades=2" >/dev/null
