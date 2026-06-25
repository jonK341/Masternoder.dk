#!/usr/bin/env bash
# Casino Discord fan-out — POST pending casino activity_events to #casino
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SECRET="${DISCORD_OPS_SECRET:-${MN2_OPS_SECRET:-}}"
URL="${CASINO_FANOUT_URL:-http://127.0.0.1:5000/api/discord/casino/fanout}"
if [[ -z "$SECRET" ]]; then
  echo "discord casino fanout skipped: DISCORD_OPS_SECRET not set" >&2
  exit 0
fi
curl -fsS -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" -d '{}' "$URL"
