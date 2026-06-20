#!/usr/bin/env bash
# Fund missing 10k collateral + reinstall platform-mn-2..5 on production.
#   bash scripts/mn2_masternode_reinstall_on_server.sh --dry-run
#   bash scripts/mn2_masternode_reinstall_on_server.sh
#   bash scripts/mn2_masternode_reinstall_on_server.sh --fund-only
set -euo pipefail

WEB="${WEB:-/var/www/html}"
DRY=0
FUND_ONLY=0
SKIP_FUND=0
WAIT_MIN=45
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --fund-only) FUND_ONLY=1 ;;
    --skip-fund) SKIP_FUND=1 ;;
    --wait-minutes=*) WAIT_MIN="${arg#*=}" ;;
  esac
done

cd "$WEB"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/mn2_masternode_reinstall_remote.py" \
  --hosts platform-mn-2,platform-mn-3,platform-mn-4,platform-mn-5 \
  $([ "$DRY" = 1 ] && echo --dry-run) \
  $([ "$FUND_ONLY" = 1 ] && echo --fund-only) \
  $([ "$SKIP_FUND" = 1 ] && echo --skip-fund) \
  --wait-minutes "$WAIT_MIN" 2>/dev/null || python3 - <<PY
# Inline fallback when repo script not wired — run remote body locally on server
import os, subprocess, sys
sys.path.insert(0, "$WEB")
# Re-invoke embedded logic via curl from git is overkill; user should deploy script.
print("Deploy scripts first, or run: python scripts/mn2_masternode_reinstall_remote.py --ask-pass")
print("From your PC (recommended).")
sys.exit(1)
PY
