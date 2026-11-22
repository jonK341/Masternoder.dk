#!/usr/bin/env bash
# Weekly Invite Party host coin prizes (ISO week). Idempotent.
set -euo pipefail
ROOT="${MASTERNODER_ROOT:-/var/www/html}"
cd "$ROOT"
if [[ -f .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
OPS="${DISCORD_OPS_SECRET:-${ADMIN_OPS_SECRET:-}}"
if [[ -z "$OPS" ]]; then
  echo "skip: no OPS secret"
  exit 0
fi
curl -fsS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Ops-Secret: ${OPS}" \
  "http://127.0.0.1:5000/api/casino/social/referral/weekly-payout" \
  || curl -fsS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Ops-Secret: ${OPS}" \
  "http://127.0.0.1:5001/api/casino/social/referral/weekly-payout"
echo
