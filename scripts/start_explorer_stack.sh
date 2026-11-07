#!/usr/bin/env bash
# Start MN2 daemon + MongoDB + eiquidus (PM2) for the block explorer stack.
# Run on the live server (typically /var/www/html).
#
#   cd /var/www/html && sudo bash scripts/start_explorer_stack.sh
#
# Does not run -reindex; use MN2_DAEMON_SETUP / explorer sync docs for heavy ops.
set -euo pipefail

ROOT="${WEB_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DATADIR="${MN2_DATADIR:-$ROOT/config}"
UNIT_MN2="${MN2_UNIT:-masternoder2d}"
PM2_NAME="${EXPLORER_PM2_NAME:-explorer}"
EXPLORER_DIR="${EQUIDUS_DIR:-/var/www/explorer}"

log() { echo "[explorer-stack] $*"; }

need_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    log "Re-run with sudo for systemd / PM2 as root."
    exit 1
  fi
}

ensure_mongo() {
  if ! systemctl cat mongod.service &>/dev/null; then
    log "WARN: mongod.service missing — install MongoDB first (see docs/EXPLORER_REINSTALL_CHECKLIST.md)"
    return 0
  fi
  if ! systemctl is-active --quiet mongod; then
    if [[ ! -f /etc/systemd/system/mongod.service.d/glibc-rseq.conf ]]; then
      log "Applying MongoDB glibc-rseq drop-in (kernel 6.19–7.0.13)..."
      bash "$ROOT/scripts/install_mongod_glibc_rseq.sh"
    fi
    systemctl start mongod
  fi
  log "mongod: $(systemctl is-active mongod 2>/dev/null || echo unknown)"
}

ensure_mn2_daemon() {
  if systemctl cat "$UNIT_MN2".service &>/dev/null; then
    if [[ ! -f "$DATADIR/.lock" ]] || ! pgrep -x masternoder2d &>/dev/null; then
      rm -f "$DATADIR/.lock"
      systemctl start "$UNIT_MN2"
    else
      systemctl start "$UNIT_MN2" 2>/dev/null || true
    fi
    log "$UNIT_MN2: $(systemctl is-active "$UNIT_MN2" 2>/dev/null || echo unknown)"
    return 0
  fi
  log "WARN: $UNIT_MN2.service missing — start masternoder2d manually"
}

ensure_pm2_explorer() {
  if ! command -v pm2 &>/dev/null; then
    log "WARN: pm2 not installed"
    return 0
  fi
  if pm2 describe "$PM2_NAME" &>/dev/null; then
    pm2 restart "$PM2_NAME"
  elif [[ -d "$EXPLORER_DIR" && -x "$EXPLORER_DIR/bin/cluster" ]]; then
    (cd "$EXPLORER_DIR" && pm2 start ./bin/cluster --name "$PM2_NAME" \
      --node-args="--stack-size=10000" -- 1)
  else
    log "WARN: eiquidus not at $EXPLORER_DIR — pm2 start explorer manually"
    return 0
  fi
  pm2 list | grep -E "name|$PM2_NAME" || true
}

probe() {
  local code
  local eiquidus_port="${EQUIDUS_HTTP_PORT:-3000}"
  # pragma: allowlist secret
  code=$(curl -s -m 8 -o /dev/null -w '%{http_code}' "http://127.0.0.1:${eiquidus_port}/" 2>/dev/null || echo "000")
  log "eiquidus :3000 → HTTP ${code}"
  if command -v masternoder2-cli &>/dev/null || [[ -x /opt/masternoder2d/masternoder2-cli ]]; then
    local cli="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
    if [[ -x "$cli" ]]; then
      local bc
      bc=$("$cli" -datadir="$DATADIR" getblockcount 2>/dev/null) || bc="(rpc fail)"
      log "MN2 getblockcount: $bc"
    fi
  fi
}

main() {
  need_root
  ensure_mongo
  ensure_mn2_daemon
  sleep 3
  ensure_pm2_explorer
  sleep 5
  probe
}

main "$@"
