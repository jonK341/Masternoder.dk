#!/bin/bash
# Daily agent jobs: user_skills_maintenance, automation_maintenance, llm_status_snapshot
# Requires AGENT_CRON_SECRET in app .env (see docs/RESEARCH_AI_SYSTEMS.md).
ENV="${AGENTS_CRON_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^AGENT_CRON_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST -H "X-Agent-Cron-Token: $TOKEN" \
  "http://127.0.0.1:5000/api/agents/cron/run?jobs=daily" >/dev/null
