#!/bin/bash
# Trigger network-overview snapshot (throttled server-side ~10 min) — P4 #174.
ENV="${MN2_ENV_FILE:-/var/www/html/.env}"
BASE="${MN2_SMOKE_BASE:-http://127.0.0.1:5000}"
curl -sS -m 20 "${BASE}/api/mn2/network-overview" >/dev/null || true
