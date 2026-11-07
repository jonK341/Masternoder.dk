#!/usr/bin/env bash
# Run a command with /var/www/html/.env loaded (same vars as uwsgi EnvironmentFile).
# Usage:  bash scripts/mn2_with_env.sh python3 scripts/mn2_bring_rented_online.py --snapshot
set -euo pipefail
WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
if [[ ! -f .env ]]; then
  echo "missing $WEB/.env" >&2
  exit 1
fi
set -a
# shellcheck source=/dev/null
source .env
set +a
exec "$@"
