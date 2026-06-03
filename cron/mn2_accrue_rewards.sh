#!/bin/bash
# MN2 staking reward accrual — triggered by cron. Reads MN2_OPS_SECRET (or MN2_SCAN_SECRET) from app .env.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
TOKEN=$(grep '^MN2_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${TOKEN:-}" ] || exit 0
curl -s -S -X POST -H "X-Ops-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/staking/ops/accrue" >/dev/null
