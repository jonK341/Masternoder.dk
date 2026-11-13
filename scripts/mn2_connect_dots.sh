#!/bin/bash
# Connect MN2 deposit dots on the live host:
#   RPC → deposit address map → scan/credit known txids → profile balance
# Usage (on Masternoder-Website):
#   bash scripts/mn2_connect_dots.sh user_182e722bae8c88b8 [txid ...]
set -euo pipefail

WEB="${MN2_WEB_ROOT:-/var/www/html}"
ENV_FILE="${MN2_ENV_FILE:-$WEB/.env}"
CONF="${MN2_CONF:-$WEB/config/masternoder2.conf}"
CLI="${MN2_CLI:-masternoder2-cli}"
APP="${MN2_APP_URL:-http://127.0.0.1:5000}"
USER_ID="${1:-}"
shift || true

if [ -z "$USER_ID" ]; then
  echo "usage: $0 <user_id> [txid ...]" >&2
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "missing env: $ENV_FILE" >&2
  exit 1
fi

TOKEN=$(grep '^MN2_SCAN_SECRET=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r"'"'" || true)
if [ -z "${TOKEN:-}" ]; then
  echo "MN2_SCAN_SECRET missing in $ENV_FILE" >&2
  exit 1
fi

echo "== 1) RPC / wallet =="
if [ -f "$CONF" ]; then
  HEIGHT=$($CLI -conf="$CONF" getblockcount 2>/dev/null || echo "err")
else
  HEIGHT=$($CLI getblockcount 2>/dev/null || echo "err")
fi
echo "getblockcount=$HEIGHT"

echo
echo "== 2) Deposit address for $USER_ID =="
ADDR_JSON=$(curl -sS --get "$APP/api/mn2/deposit-address" --data-urlencode "user_id=${USER_ID}")
echo "$ADDR_JSON"
ADDR=$(printf '%s' "$ADDR_JSON" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("deposit_address") or "").strip())')
echo "address=$ADDR"

echo
echo "== 3) Scan + optional known txids =="
BODY=$(python3 -c 'import json,sys; print(json.dumps({"txids": sys.argv[1:]} if len(sys.argv) > 1 else {}))' "$@")
SCAN=$(curl -sS -X POST -H "X-Scanner-Token: $TOKEN" -H "Content-Type: application/json" \
  -d "$BODY" "$APP/api/mn2/scan-deposits")
echo "$SCAN"

echo
echo "== 4) Balance =="
curl -sS --get "$APP/api/mn2/balance" --data-urlencode "user_id=${USER_ID}"
echo
echo
echo "Profile URL: /profile/?user_id=${USER_ID}"
if [ -n "$ADDR" ]; then
  # Prefer app-built explorer link (Chainz needs address.dws?<ADDR>.htm, not ?addr=).
  echo "Explorer path: /address.dws?${ADDR}.htm"
fi
