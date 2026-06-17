#!/bin/bash
# M8 Casino win highlights (#58) — activity_events.jsonl → Discord #casino (Gate S).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=mn2_read_ops_secret.sh
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh"
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="$(mn2_read_ops_secret 2>/dev/null || true)"
SECRET="${SECRET:-${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}}"
HDR=()
[ -n "${SECRET:-}" ] && HDR=(-H "X-Ops-Secret: ${SECRET}")
curl -sf -X POST "${HOST}/api/discord/casino/fanout" \
  "${HDR[@]}" \
  -H "Content-Type: application/json" \
  -d '{}' || echo "casino discord fanout failed"
