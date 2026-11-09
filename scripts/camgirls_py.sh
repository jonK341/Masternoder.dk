#!/usr/bin/env bash
# Run camgirls ops scripts on the server with the correct Python (no ./venv on prod).
# Usage (on server):
#   cd /var/www/html && bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py
#   bash scripts/camgirls_py.sh scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.json --provision-addresses
set -euo pipefail
WEB="${CAMGIRLS_WEB_ROOT:-/var/www/html}"
cd "$WEB"
if [ -x ./.venv/bin/python ]; then
  PY=./.venv/bin/python
elif [ -x ./venv/bin/python ]; then
  PY=./venv/bin/python
else
  PY=python3
fi
echo "[camgirls_py] using $PY" >&2

_ensure_requests() {
  "$PY" -c "import requests" 2>/dev/null && return 0
  echo "[camgirls_py] installing requests (optional; MN2 RPC also uses stdlib urllib)..." >&2
  if "$PY" -m pip install -q "requests>=2.32.0,<2.34" 2>/dev/null; then return 0; fi
  if "$PY" -m ensurepip --upgrade 2>/dev/null; then
    "$PY" -m pip install -q "requests>=2.32.0,<2.34" 2>/dev/null && return 0
  fi
  SITE=$("$PY" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null || true)
  if [ -n "${SITE:-}" ] && python3 -m pip install -q -t "$SITE" "requests>=2.32.0,<2.34" 2>/dev/null; then
    return 0
  fi
  echo "[camgirls_py] WARN: requests not in venv; provision uses urllib RPC fallback" >&2
  return 0
}
_ensure_requests

exec "$PY" "$@"
