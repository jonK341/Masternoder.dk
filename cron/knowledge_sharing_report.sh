#!/bin/bash
# Reporter agent — knowledge-sharing ingredients (optional append to jsonl log).
# Reads KNOWLEDGE_REPORT_SECRET from app .env (same as uwsgi).
ENV="${KNOWLEDGE_REPORT_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^KNOWLEDGE_REPORT_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST \
  -H "X-Reporter-Token: $TOKEN" \
  "http://127.0.0.1:5000/api/agents/reporter/knowledge-ingredients?append_log=1&record_activity=1" \
  >/dev/null
