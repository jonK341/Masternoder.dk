#!/usr/bin/env bash
# Smoke: health + heavy POST paths (run on server or against BASE_URL).
# Usage:
#   BASE_URL=http://127.0.0.1:5000 bash scripts/smoke_db_health_flows.sh
#   BASE_URL=https://masternoder.dk bash scripts/smoke_db_health_flows.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"
BASE_URL="${BASE_URL%/}"

echo "=== smoke_db_health_flows BASE_URL=$BASE_URL ==="

echo "--- GET /api/health ---"
curl -sS -m 15 -w "\nHTTP %{http_code}\n" "${BASE_URL}/api/health" | head -c 400
echo

echo "--- GET /api/health/database ---"
curl -sS -m 30 -w "\nHTTP %{http_code}\n" "${BASE_URL}/api/health/database" | head -c 1200
echo

echo "--- POST /api/user/create (minimal JSON) ---"
curl -sS -m 45 -X POST -H "Content-Type: application/json" \
  -d '{"preferences":{},"device_fingerprint":"smoke-test"}' \
  -w "\nHTTP %{http_code}\n" "${BASE_URL}/api/user/create" | head -c 800
echo

echo "--- GET /api/health/database (after create) ---"
curl -sS -m 30 -w "\nHTTP %{http_code}\n" "${BASE_URL}/api/health/database" | head -c 800
echo

echo "=== done (add shop/points/paypal tests manually with real session/user_id) ==="
