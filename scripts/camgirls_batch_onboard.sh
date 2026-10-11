#!/usr/bin/env bash
# Server-safe entry for batch wave onboard (do not: bash camgirls_batch_onboard.py).
# Usage:
#   cd /var/www/html && bash scripts/camgirls_batch_onboard.sh --file waves/wave2.json --batch 2 --dry-run
set -euo pipefail
WEB="${CAMGIRLS_WEB_ROOT:-/var/www/html}"
cd "$WEB"
exec bash scripts/camgirls_py.sh scripts/camgirls_batch_onboard.py "$@"
