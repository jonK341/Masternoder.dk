#!/bin/bash
# API service skill pass — frontend vs backend route gap scan (discover_all).
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST -H "X-Agent-Cron-Token: $TOKEN" \
  "http://127.0.0.1:5000/api/agents/cron/run?jobs=api_service_skill" >/dev/null
