#!/bin/bash
# Casino free-daily flip push reminder — e.g. daily 16:00 UTC.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^MN2_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || TOKEN=$(grep '^DISCORD_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"free_daily"}' \
  "http://127.0.0.1:5000/api/casino/ops/push-broadcast" >/dev/null
