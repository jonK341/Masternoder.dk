#!/usr/bin/env bash
# One command: drain all pending rented hosts + startmasternode all (multi-ping fleet).
#
# Run after RPC is healthy (e.g. post-reboot):
#   cd /var/www/html && bash scripts/mn2_activate_all_rented.sh
#   bash scripts/mn2_activate_all_rented.sh --summary
#   bash scripts/mn2_activate_all_rented.sh --skip-drain
#
# Optional env: MN2_WALLET_PASSPHRASE, WEB_ROOT, MN2_RPC_TIMEOUT=60
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="${WEB_ROOT:-/var/www/html}"
if [[ ! -d "$WEB" ]]; then
  WEB="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$WEB"

export PYTHONUNBUFFERED=1
export MN2_RPC_HEALTH_TIMEOUT="${MN2_RPC_HEALTH_TIMEOUT:-60}"
export MN2_RPC_TIMEOUT="${MN2_RPC_TIMEOUT:-60}"
export MN2_RPC_MAX_RETRIES="${MN2_RPC_MAX_RETRIES:-2}"

if [[ -f "$WEB/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$WEB/.env"
  set +a
fi

if [[ -x "$SCRIPT_DIR/mn2_unlock_collateral.sh" && -n "${MN2_WALLET_PASSPHRASE:-}" ]]; then
  bash "$SCRIPT_DIR/mn2_unlock_collateral.sh" || true
fi

CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
DATADIR="${MN2_DATADIR:-$WEB/config}"
if [[ -x "$CLI" ]]; then
  if ! out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) || [[ ! "$out" =~ ^[0-9]+$ ]]; then
    echo "[activate-all] WARN: CLI RPC not ready yet: ${out:0:120}" >&2
    echo "[activate-all] Waiting up to 120s for getblockcount…" >&2
    for _ in $(seq 1 120); do
      if out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) && [[ "$out" =~ ^[0-9]+$ ]]; then
        echo "[activate-all] RPC height=$out" >&2
        break
      fi
      sleep 1
    done
  fi
fi

exec python3 "$SCRIPT_DIR/mn2_activate_all_rented.py" "$@"
