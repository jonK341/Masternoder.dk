#!/usr/bin/env python3
"""
Masternode fleet: install boot autostart, run local-first start, poll ENABLED / activetime.

Run after deploy (while waiting for masternodes to go ENABLED):

  python scripts/mn2_masternode_fleet_ops_remote.py --ask-pass
  python scripts/mn2_masternode_fleet_ops_remote.py --ask-pass --watch --interval 30
  python scripts/mn2_masternode_fleet_ops_remote.py --ask-pass --status-only
  python scripts/mn2_masternode_fleet_ops_remote.py --ask-pass --install-autostart --no-start

Requires on server: scripts/mn2_start_masternode.py, scripts/mn2_fleet_autostart.sh
(deploy mn2_staking manifest first).
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 600) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


REMOTE = r'''bash -s <<'ENDSCRIPT'
set +e
WEB="/var/www/html"
D="-datadir=/var/www/html/config"
CLI="/opt/masternoder2d/masternoder2-cli $D"
INSTALL_AUTOSTART="__INSTALL__"
DO_FIX_PRIVKEY="__FIX_PRIVKEY__"
DO_START="__START__"
DO_WATCH="__WATCH__"
WATCH_SEC="__INTERVAL__"
WATCH_MAX="__MAX_LOOPS__"

log() { echo "[fleet-ops] $*"; }

wait_rpc() {
  local i max sec="${MN2_RPC_WAIT_SEC:-180}"
  max=$((sec / 5))
  [ "$max" -lt 6 ] && max=6
  for i in $(seq 1 "$max"); do
    if systemctl is-active --quiet masternoder2d && $CLI getblockcount 2>/dev/null | grep -qE '^[0-9]+$'; then
      log "RPC ready height=$($CLI getblockcount 2>/dev/null)"
      return 0
    fi
    sleep 5
  done
  log "WARN: RPC not ready after ${sec}s"
  return 1
}

fix_daemon_privkey() {
  PRIMARY="platformmn2"
  MN_CONF="/var/www/html/config/masternode.conf"
  DCONF="/var/www/html/config/masternoder2.conf"
  if [ ! -f "$MN_CONF" ] || [ ! -f "$DCONF" ]; then
    log "WARN: skip privkey fix — conf missing"
    return 1
  fi
  WANT=$(awk -v p="$PRIMARY" '
    $1==p && NF==5 && index($2,":")>0 { k=$3 }
    END { if (k!="") print k }
  ' "$MN_CONF")
  HAVE=$(grep '^masternodeprivkey=' "$DCONF" 2>/dev/null | cut -d= -f2- | tail -1)
  PK_LINES=$(grep -c '^masternodeprivkey=' "$DCONF" 2>/dev/null || echo 0)
  MN1_LINES=$(grep -c '^masternode=1' "$DCONF" 2>/dev/null || echo 0)
  if [ -z "$WANT" ]; then
    log "ERROR: no privkey for $PRIMARY in masternode.conf"
    return 1
  fi
  if [ "$HAVE" = "$WANT" ] && [ "$PK_LINES" -le 1 ] && [ "$MN1_LINES" -le 1 ]; then
    log "OK masternoder2.conf privkey matches $PRIMARY (${WANT:0:8}…)"
    return 0
  fi
  if [ "$PK_LINES" -gt 1 ]; then
    log "FIX duplicate masternodeprivkey lines ($PK_LINES) in masternoder2.conf"
  fi
  log "FIX privkey mismatch have=${HAVE:0:8}… want=${WANT:0:8}…"
  if [ -f "$WEB/scripts/mn2_fix_daemon_privkey.sh" ]; then
    bash "$WEB/scripts/mn2_fix_daemon_privkey.sh" --primary="$PRIMARY"
    return $?
  fi
  PORT=$(grep '^port=' "$DCONF" | head -1 | cut -d= -f2-)
  EXTIP=$(grep '^externalip=' "$DCONF" | head -1 | cut -d= -f2-)
  PING=$(grep '^masternodeaddr=' "$DCONF" | head -1 | cut -d= -f2-)
  PORT=${PORT:-17646}
  EXTIP=${EXTIP:-140.82.39.124}
  PING=${PING:-127.0.0.1:17646}
  grep -vE '^(listen=|port=|externalip=|masternode=1|masternodeprivkey=|masternodeaddr=)' "$DCONF" > "${DCONF}.tmp" || true
  {
    cat "${DCONF}.tmp"
    echo "listen=1"
    echo "port=${PORT}"
    echo "externalip=${EXTIP}"
    echo "masternode=1"
    echo "masternodeprivkey=${WANT}"
    echo "masternodeaddr=${PING}"
  } > "$DCONF"
  rm -f "${DCONF}.tmp"
  systemctl restart masternoder2d
  if ! wait_rpc; then
    log "ERROR: abort start — RPC not ready after privkey fix"
    return 1
  fi
  $CLI startmasternode alias false "$PRIMARY" 2>/dev/null || true
  $CLI startmasternode local false 2>/dev/null || true
  log "Fixed and restarted daemon for $PRIMARY"
  return 0
}

fix_config_permissions() {
  if [ -f "$WEB/scripts/mn2_fix_config_permissions.sh" ]; then
    bash "$WEB/scripts/mn2_fix_config_permissions.sh"
    return $?
  fi
  CONFIG="/var/www/html/config"
  chmod 750 "$CONFIG" 2>/dev/null || chmod 755 "$CONFIG"
  chown root:www-data "$CONFIG/masternoder2.conf" 2>/dev/null && chmod 640 "$CONFIG/masternoder2.conf" 2>/dev/null || true
  chown www-data:www-data "$CONFIG/masternode.conf" 2>/dev/null && chmod 664 "$CONFIG/masternode.conf" 2>/dev/null || true
  log "Applied inline config permissions"
  return 0
}

show_status() {
  echo ""
  echo "== masternoder2.conf (masternode lines) =="
  grep -nE '^(masternode|masternodeprivkey|masternodeaddr|externalip|listen|port)=' \
    /var/www/html/config/masternoder2.conf 2>/dev/null || echo "(none)"

  echo ""
  echo "== listmasternodeconf =="
  $CLI listmasternodeconf 2>/dev/null | head -c 3000

  echo ""
  echo "== getmasternodecount =="
  $CLI getmasternodecount 2>/dev/null

  echo ""
  echo "== listmasternodes (status / activetime) =="
  $CLI listmasternodes 2>/dev/null | python3 -c "
import json, sys
raw = sys.stdin.read().strip()
if not raw:
    print('(empty)')
    sys.exit(0)
try:
    rows = json.loads(raw)
except Exception as exc:
    print('parse error:', exc)
    print(raw[:2000])
    sys.exit(0)
if not isinstance(rows, list):
    rows = [rows]
enabled = active = 0
for r in rows:
    if not isinstance(r, dict):
        continue
    st = (r.get('status') or r.get('State') or '').upper()
    tx = r.get('txhash') or r.get('proTxHash') or r.get('collateral') or '?'
    tx = str(tx)[:16]
    act = r.get('activetime', r.get('active_time', '?'))
    addr = r.get('addr') or r.get('address') or ''
    if 'ENABLE' in st:
        enabled += 1
    if 'ACTIVE' in st:
        active += 1
    print(f\"  {st:10} activetime={act:>8}  {tx}…  {addr}\")
print(f'--- summary: ENABLED={enabled} ACTIVE={active} total={len(rows)} ---')
" 2>/dev/null || $CLI listmasternodes 2>/dev/null | head -c 4000

  echo ""
  echo "== recent ping (debug.log tail) =="
  tail -30 /var/www/html/config/debug.log 2>/dev/null | grep -iE 'masternode|ping|SendMasternode' | tail -8 || echo "(no ping lines)"
}

if [ "$INSTALL_AUTOSTART" = "1" ]; then
  echo "== install mn2-fleet-autostart =="
  if [ -f "$WEB/scripts/mn2_fleet_autostart.sh" ]; then
    cp "$WEB/scripts/mn2_fleet_autostart.sh" /usr/local/bin/mn2-fleet-autostart
    chmod +x /usr/local/bin/mn2-fleet-autostart
    echo "OK /usr/local/bin/mn2-fleet-autostart"
  else
    echo "FAIL mn2_fleet_autostart.sh missing — deploy mn2_staking first"
  fi
  if [ -f "$WEB/systemd/mn2-fleet-autostart.service.example" ]; then
    cp "$WEB/systemd/mn2-fleet-autostart.service.example" /etc/systemd/system/mn2-fleet-autostart.service
    systemctl daemon-reload
    systemctl enable mn2-fleet-autostart.service 2>/dev/null || true
    echo "OK mn2-fleet-autostart.service enabled"
  else
    echo "WARN systemd unit example missing"
  fi
fi

systemctl is-active masternoder2d >/dev/null || systemctl start masternoder2d 2>/dev/null || true
wait_rpc

fix_config_permissions

if [ "$DO_FIX_PRIVKEY" = "1" ]; then
  echo ""
  echo "== verify/fix masternoder2.conf privkey (primary_ping_alias) =="
  fix_daemon_privkey
fi

if [ "$DO_START" = "1" ]; then
  echo ""
  echo "== unlock locked collateral UTXOs =="
  LOCKED=$($CLI listlockunspent 2>/dev/null || echo "[]")
  if [ "$LOCKED" != "[]" ] && [ -n "$LOCKED" ]; then
    $CLI lockunspent true "$LOCKED" 2>/dev/null || true
  fi

  echo ""
  echo "== start local-first (mn2_start_masternode.py --all-from-conf) =="
  if [ -f "$WEB/scripts/mn2_start_masternode.py" ]; then
    cd "$WEB" && python3 scripts/mn2_start_masternode.py --all-from-conf
  else
    log "WARN mn2_start_masternode.py missing — fallback: local then aliases"
    $CLI startmasternode local false 2>/dev/null || true
    for a in $($CLI listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
try:
    rows=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for r in rows:
    if isinstance(r,dict) and r.get('alias'):
        print(r['alias'])
" 2>/dev/null); do
      echo "--- alias $a ---"
      $CLI startmasternode alias false "$a" 2>/dev/null || true
    done
  fi
fi

show_status

if [ "$DO_WATCH" = "1" ]; then
  loops=0
  while [ "$loops" -lt "$WATCH_MAX" ]; do
    loops=$((loops + 1))
    enabled=$($CLI listmasternodes 2>/dev/null | python3 -c "
import json,sys
try:
    rows=json.load(sys.stdin)
except Exception:
    print(0); sys.exit(0)
if not isinstance(rows, list):
    rows=[rows]
print(sum(1 for r in rows if isinstance(r,dict) and 'ENABLE' in str(r.get('status','')).upper()))
" 2>/dev/null || echo 0)
    echo ""
    log "watch $loops/$WATCH_MAX — ENABLED count=$enabled (sleep ${WATCH_SEC}s)"
    if [ "$enabled" -ge 1 ] 2>/dev/null; then
      log "At least one ENABLED — showing final status"
      show_status
      exit 0
    fi
    sleep "$WATCH_SEC"
  done
  log "Watch ended without ENABLED — check hairpin masternodeaddr=127.0.0.1:17646"
  show_status
fi
ENDSCRIPT
'''


def build_remote(*, install: bool, start: bool, watch: bool, interval: int, max_loops: int, fix_privkey: bool) -> str:
    return (
        REMOTE.replace("__INSTALL__", "1" if install else "0")
        .replace("__FIX_PRIVKEY__", "1" if fix_privkey else "0")
        .replace("__START__", "1" if start else "0")
        .replace("__WATCH__", "1" if watch else "0")
        .replace("__INTERVAL__", str(max(10, interval)))
        .replace("__MAX_LOOPS__", str(max(1, max_loops)))
    )


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 fleet autostart + local-first start + status watch")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status-only", action="store_true", help="Skip install/start; show listmasternodes only")
    p.add_argument("--install-autostart", action="store_true", help="Install systemd boot autostart (default: on)")
    p.add_argument("--no-install", action="store_true", help="Skip autostart install")
    p.add_argument("--no-start", action="store_true", help="Skip mn2_start_masternode.py")
    p.add_argument("--fix-privkey", action="store_true", help="Verify/fix masternoder2.conf privkey (default: on unless --no-fix-privkey)")
    p.add_argument("--no-fix-privkey", action="store_true", help="Skip masternoder2.conf privkey verify/fix")
    p.add_argument("--watch", action="store_true", help="Poll until at least one ENABLED")
    p.add_argument("--interval", type=int, default=30, help="Watch poll seconds (default 30)")
    p.add_argument("--max-loops", type=int, default=40, help="Max watch iterations (~20 min at 30s)")
    args = p.parse_args()

    install = not args.no_install and not args.status_only
    if args.install_autostart:
        install = True
    start = not args.no_start and not args.status_only
    watch = args.watch and not args.status_only
    fix_privkey = not args.no_fix_privkey and not args.status_only
    if args.fix_privkey:
        fix_privkey = True

    remote = build_remote(
        install=install,
        start=start,
        watch=watch,
        interval=args.interval,
        max_loops=args.max_loops,
        fix_privkey=fix_privkey,
    )

    if args.dry_run:
        print(remote)
        return 0

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, auth_method, _ = connect_deploy_ssh(pw)
    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==\n")
    timeout = 900 if watch else 300
    out = sh(ssh, remote, timeout=timeout)
    print(out)
    ssh.close()
    ok = "RPC ready" in out or "listmasternodeconf" in out.lower()
    if watch:
        ok = ok and ("At least one ENABLED" in out or "ENABLED count=" in out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
