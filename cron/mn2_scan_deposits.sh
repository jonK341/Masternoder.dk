#!/bin/bash
# MN2 deposit scanner — triggered by cron. Credits confirmed receives to user balances.
# Reads MN2_SCAN_SECRET from app .env (same as uwsgi). Override with MN2_ENV_FILE / MN2_SCAN_URL.
set -euo pipefail

ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
if [ ! -f "$ENV" ]; then
  echo "mn2_scan_deposits: env file missing: $ENV" >&2
  exit 1
fi

TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || true)
if [ -z "${TOKEN:-}" ]; then
  echo "mn2_scan_deposits: MN2_SCAN_SECRET unset in $ENV — scanner not authorized" >&2
  exit 1
fi

BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT

try_post() {
  local url="$1"
  local code
  code=$(curl -s -S -o "$BODY" -w "%{http_code}" \
    -X POST -H "X-Scanner-Token: $TOKEN" "$url" || echo "000")
  echo "$code"
}

HTTP="000"
URL="${MN2_SCAN_URL:-}"
if [ -n "$URL" ]; then
  HTTP=$(try_post "$URL")
else
  for port in "${MN2_APP_PORT:-5000}" 5003; do
    URL="http://127.0.0.1:${port}/api/mn2/scan-deposits"
    HTTP=$(try_post "$URL")
    if [ "$HTTP" = "200" ] || [ "$HTTP" = "403" ] || [ "$HTTP" = "500" ]; then
      break
    fi
  done
fi

if [ "$HTTP" != "200" ]; then
  echo "mn2_scan_deposits: HTTP $HTTP from $URL" >&2
  cat "$BODY" >&2 || true
  exit 1
fi
exit 0
