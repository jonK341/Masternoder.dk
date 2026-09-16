#!/usr/bin/env bash
# Daily casino revenue rollup — POST summary to ops webhook or stdout (dry_run safe).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASE="${CASINO_REVENUE_BASE_URL:-http://127.0.0.1:5000}"
DAYS="${CASINO_REVENUE_DAYS:-1}"
DRY_RUN="${CASINO_REVENUE_DRY_RUN:-1}"
WEBHOOK="${DISCORD_OPS_WEBHOOK_URL:-${CASINO_REVENUE_WEBHOOK:-}}"

payload="$(curl -fsS "${BASE}/api/casino/revenue/report/today" 2>/dev/null || echo '{"success":false}')"
if [[ "$(echo "$payload" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("success",False))' 2>/dev/null || echo False)" != "True" ]]; then
  echo "casino revenue report: API unavailable" >&2
  exit 0
fi

summary="$(echo "$payload" | python3 -c "
import json,sys
d=json.load(sys.stdin)
s=d.get('summary') or {}
print(f\"Casino daily revenue ({d.get('day','?')}): {s.get('headline','n/a')} | big wins {s.get('big_wins',0)} | rewards {s.get('reward_coins_granted',0)} coins\")
" 2>/dev/null || echo "Casino daily revenue report ready")"

echo "$summary"

# Optional weekly email digest stub (ops-only — set CASINO_REVENUE_EMAIL to enable)
REVENUE_EMAIL="${CASINO_REVENUE_EMAIL:-}"
if [[ -n "$REVENUE_EMAIL" && "$DRY_RUN" != "1" ]]; then
  SUBJECT="MasterNoder casino revenue digest — $(echo "$payload" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("day","?"))' 2>/dev/null || echo '?')"
  BODY="Weekly operator summary (no PII):\n\n$summary\n\nFull report: ${BASE}/api/casino/revenue/report/today"
  if command -v mail >/dev/null 2>&1; then
    echo -e "$BODY" | mail -s "$SUBJECT" "$REVENUE_EMAIL" 2>/dev/null && echo "email digest sent to $REVENUE_EMAIL" || echo "email digest failed (mail unavailable)" >&2
  else
    echo "CASINO_REVENUE_EMAIL set but 'mail' not installed — digest stub only:" >&2
    echo -e "$BODY" >&2
  fi
fi

if [[ "$DRY_RUN" == "1" || -z "$WEBHOOK" ]]; then
  echo "casino revenue report dry_run (set CASINO_REVENUE_DRY_RUN=0 and DISCORD_OPS_WEBHOOK_URL to post)" >&2
  exit 0
fi

curl -fsS -X POST -H "Content-Type: application/json" \
  -d "$(python3 -c "import json; print(json.dumps({'content': '''$summary'''}))")" \
  "$WEBHOOK" >/dev/null
echo "posted to webhook"
