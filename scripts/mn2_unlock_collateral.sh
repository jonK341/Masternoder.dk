#!/usr/bin/env bash
# Unlock wallet-locked collateral UTXOs so startmasternode can allocate vins.
# Run on production as root (or any user with RPC access).
#
# Usage:
#   sudo bash /var/www/html/scripts/mn2_unlock_collateral.sh
#   TXID=4b41ef0c… VOUT=1 sudo bash /var/www/html/scripts/mn2_unlock_collateral.sh
#   MN2_WALLET_PASSPHRASE='…' sudo -E bash /var/www/html/scripts/mn2_unlock_collateral.sh
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
DATADIR="${MN2_DATADIR:-$WEB/config}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
D="-datadir=${DATADIR}"
TXID="${TXID:-}"
VOUT="${VOUT:-}"

log() { echo "[unlock-collateral] $*"; }

unlock_wallet() {
  local pw="${MN2_WALLET_PASSPHRASE:-}"
  if [[ -z "$pw" ]]; then
    return 0
  fi
  log "walletpassphrase (120s, staking-only)"
  "$CLI" $D walletpassphrase "$pw" 120 true 2>/dev/null || true
}

unlock_outputs() {
  local locked
  locked=$("$CLI" $D listlockunspent 2>/dev/null || echo "[]")
  if [[ -z "$locked" || "$locked" == "[]" ]]; then
    log "No locked UTXOs"
    return 0
  fi
  if [[ -n "$TXID" && -n "$VOUT" ]]; then
    log "Unlocking target ${TXID:0:8}…:${VOUT} if locked"
    python3 - <<'PY' "$CLI" "$DATADIR" "$TXID" "$VOUT"
import json, subprocess, sys
cli, datadir, txid, vout = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
raw = subprocess.check_output([cli, f"-datadir={datadir}", "listlockunspent"], text=True)
rows = json.loads(raw or "[]")
want = (txid, int(vout))
targets = [r for r in rows if isinstance(r, dict) and str(r.get("txid")) == want[0] and int(r.get("vout", -1)) == want[1]]
if not targets:
    print("(target not in lock list)")
    sys.exit(0)
subprocess.run([cli, f"-datadir={datadir}", "lockunspent", "true", json.dumps(targets)], check=False)
PY
    return 0
  fi
  log "Unlocking all locked UTXOs ($(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])))" "$locked"))"
  "$CLI" $D lockunspent true "$locked" 2>/dev/null || true
}

show_collateral() {
  local tx="${TXID:-4b41ef0ca3b797a766b3ce84453a2b29c5c1ee5c98b813a890b0eaf97d37ad48}"
  local vo="${VOUT:-1}"
  log "gettxout ${tx:0:8}…:${vo}"
  "$CLI" $D gettxout "$tx" "$vo" 2>/dev/null || echo "(null — spent or not indexed)"
  log "listlockunspent"
  "$CLI" $D listlockunspent 2>/dev/null || echo "[]"
}

main() {
  unlock_wallet
  show_collateral
  unlock_outputs
  show_collateral
  log "Done — retry start only after daemon restart if vin was already allocated (see MN2_OPS §11.1)"
}

main "$@"
