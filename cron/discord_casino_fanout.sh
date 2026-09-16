#!/usr/bin/env bash
# Casino Discord fan-out — POST pending casino activity_events to #casino
# Default dry_run=true until CASINO_FANOUT_LIVE=1 is set on the server cron line.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SECRET="${DISCORD_OPS_SECRET:-${MN2_OPS_SECRET:-}}"
URL="${CASINO_FANOUT_URL:-http://127.0.0.1:5000/api/discord/casino/fanout}"
if [[ -z "$SECRET" ]]; then
  echo "discord casino fanout skipped: DISCORD_OPS_SECRET not set" >&2
  exit 0
fi
PAYLOAD='{"dry_run":true}'
if [[ "${CASINO_FANOUT_LIVE:-}" == "1" ]]; then
  PAYLOAD='{"dry_run":false}'
fi
curl -fsS -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" -d "$PAYLOAD" "$URL"
