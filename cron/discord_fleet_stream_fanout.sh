#!/usr/bin/env bash
# Fleet livestream → Discord #general (YouTube unfurl + monitor link + GPRS tick)
# Set FLEET_STREAM_FANOUT_LIVE=1 on the server cron line to post for real.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SECRET="${DISCORD_OPS_SECRET:-${MN2_OPS_SECRET:-}}"
URL="${FLEET_STREAM_FANOUT_URL:-http://127.0.0.1:5000/api/discord/fleet-stream/fanout}"
if [[ -z "$SECRET" ]]; then
  echo "discord fleet stream fanout skipped: DISCORD_OPS_SECRET not set" >&2
  exit 0
fi
PAYLOAD='{"dry_run":true}'
if [[ "${FLEET_STREAM_FANOUT_LIVE:-}" == "1" ]]; then
  PAYLOAD='{"dry_run":false}'
fi
curl -fsS -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" -d "$PAYLOAD" "$URL"
