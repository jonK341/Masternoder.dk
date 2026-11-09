#!/bin/bash
# MN2 deposit scanner — triggered by cron. Reads MN2_SCAN_SECRET from app .env (same as uwsgi).
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST -H "X-Scanner-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/scan-deposits" >/dev/null
