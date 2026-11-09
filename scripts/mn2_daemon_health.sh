#!/usr/bin/env bash
# Quick MN2 RPC + app payment-health check (run on server after starting masternoder2d).
# Usage: ./scripts/mn2_daemon_health.sh [BASE_URL]
#   BASE_URL default https://masternoder.dk
set -euo pipefail
BASE="${1:-https://masternoder.dk}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENVF="${ROOT}/.env"
if [[ -f "$ENVF" ]]; then
  # shellcheck source=/dev/null
  set +u
  export "$(grep -E '^MN2_RPC_(URL|USER|PASSWORD)=' "$ENVF" | xargs)" || true
  set -u
fi
URL="${MN2_RPC_URL:-http://127.0.0.1:9332}"
USER="${MN2_RPC_USER:-mn2rpc}"
PASS="${MN2_RPC_PASSWORD:-}"
echo "== RPC getblockcount → $URL"
if [[ -n "$PASS" ]]; then
  curl -sS --max-time 8 -u "${USER}:${PASS}" \
    -d '{"jsonrpc":"1.0","id":"h","method":"getblockcount","params":[]}' \
    -H 'content-type: text/plain;' "$URL" | head -c 400 || echo "(curl failed)"
  echo ""
else
  echo "MN2_RPC_PASSWORD not set in environment; skip authenticated RPC probe."
fi
echo "== GET ${BASE}/api/shop/payment-health"
curl -sS --max-time 12 "${BASE}/api/shop/payment-health" | head -c 800 || echo "(curl failed)"
echo ""
