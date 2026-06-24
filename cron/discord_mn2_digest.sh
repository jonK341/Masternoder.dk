#!/usr/bin/env bash
# MN2 Discord hub digest — run hourly; posts once at configured UTC hour unless forced via API.
set -euo pipefail
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="${DISCORD_OPS_SECRET:-}"
if [[ -z "$SECRET" ]]; then
  echo "DISCORD_OPS_SECRET not set" >&2
  exit 1
fi
curl -fsS -X POST -H "X-Ops-Secret: $SECRET" \
  "${HOST}/api/discord/mn2/digest/run" || \
python3 "$(dirname "$0")/../scripts/discord_mn2_channel.py" post-info
