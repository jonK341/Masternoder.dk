#!/bin/bash
# Discord activity funnel digest (M8 #53) — posts recent activity_events to Discord webhook.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=mn2_read_ops_secret.sh
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh"
HOST="${MN2_CRON_HOST:-http://127.0.0.1:5000}"
SECRET="$(mn2_read_ops_secret 2>/dev/null || true)"
HDR=()
[ -n "${SECRET:-}" ] && HDR=(-H "X-Ops-Secret: ${SECRET}")
curl -s -S -X POST "${HDR[@]}" "${HOST}/api/discord/m8/alert-funnel" >/dev/null
