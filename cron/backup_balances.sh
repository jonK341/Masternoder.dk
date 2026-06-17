#!/bin/bash
# MN2 balance / ledger backup — daily via cron.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
[ -f "$ENV" ] || exit 0
SECRET=$(grep '^ADMIN_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
[ -n "${SECRET:-}" ] || SECRET=$(grep '^DISCORD_OPS_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"') || true
HDR=()
[ -n "${SECRET:-}" ] && HDR=(-H "X-Ops-Secret: $SECRET")
curl -s -S -X POST "${HDR[@]}" "http://127.0.0.1:5000/api/security/cron/backup" >/dev/null
