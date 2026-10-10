#!/usr/bin/env python3
"""Repair MN2 daemon layout + systemd unit on production (203/EXEC, missing CLI)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass
from mn2_release_config import RELEASE_URL

REPAIR_SCRIPT = r"""bash -s <<'ENDSCRIPT'
set -e
RELEASE_URL='__RELEASE_URL__'
ROLLBACK_URL='https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz'
DAEMON_BIN=/opt/masternoder2d/masternoder2d
CLI_BIN=/opt/masternoder2d/masternoder2-cli
UNIT=/etc/systemd/system/masternoder2d.service
DATADIR=/var/www/html/config
MODE='__MODE__'

systemctl stop masternoder2d 2>/dev/null || true
pkill -f 'masternoder2d -datadir' 2>/dev/null || true

if [ "$MODE" = "diagnose" ] || [ "$MODE" = "fix-segv" ]; then
  echo "== debug.log (last 60 lines) =="
  tail -60 "$DATADIR/debug.log" 2>/dev/null || echo "(no debug.log)"
  echo ""
  echo "== masternode.conf =="
  if [ -f "$DATADIR/masternode.conf" ]; then
    wc -l "$DATADIR/masternode.conf"
    cat "$DATADIR/masternode.conf"
  else
    echo "(missing)"
  fi
  echo ""
  echo "== ldd daemon =="
  ldd "$DAEMON_BIN" 2>&1 | head -20 || true
  echo ""
  echo "== foreground test (no masternode.conf) =="
  if [ -f "$DATADIR/masternode.conf" ]; then
    mv "$DATADIR/masternode.conf" "$DATADIR/masternode.conf.bak.segv"
  fi
  set +e
  timeout 35 "$DAEMON_BIN" -datadir="$DATADIR" 2>&1 | tail -25
  rc=${PIPESTATUS[0]}
  set -e
  if pgrep -f "$DAEMON_BIN" >/dev/null 2>&1; then
    echo "OK: daemon still running after 35s without masternode.conf"
    pkill -f "$DAEMON_BIN" 2>/dev/null || true
    sleep 2
    if [ "$MODE" = "fix-segv" ]; then
      echo "Keeping masternode.conf aside; restart via systemd"
      # platform-mn-1 only — minimal safe conf
      # Keep first valid line only (bad extra lines often cause SEGV on v1.2.3.0)
      awk 'NF>=5 && $0 !~ /^#/ { print; exit }' "$DATADIR/masternode.conf.bak.segv" > "$DATADIR/masternode.conf" 2>/dev/null || true
      if [ ! -s "$DATADIR/masternode.conf" ]; then
        : > "$DATADIR/masternode.conf"
        echo "WARN: empty masternode.conf — re-add platform-mn-1 manually"
      fi
    else
      mv "$DATADIR/masternode.conf.bak.segv" "$DATADIR/masternode.conf" 2>/dev/null || true
    fi
  else
    echo "FAIL: daemon exited/crashed without masternode.conf (rc=$rc)"
    mv "$DATADIR/masternode.conf.bak.segv" "$DATADIR/masternode.conf" 2>/dev/null || true
    if [ "$MODE" = "fix-segv" ]; then
      echo "== rollback to v1.2.2.0 =="
      cp "$DAEMON_BIN" "${DAEMON_BIN}.v123.bak" 2>/dev/null || true
      cd /tmp
      curl -fsSL -o mn2-1220.tar.gz "$ROLLBACK_URL"
      tar -xzf mn2-1220.tar.gz
      cp masternoder2d/masternoder2d "$DAEMON_BIN"
      cp masternoder2d/masternoder2-cli "$CLI_BIN"
      cp masternoder2d/masternoder2-cli /usr/local/bin/masternoder2-cli
      chmod +x "$DAEMON_BIN" "$CLI_BIN" /usr/local/bin/masternoder2-cli
      "$DAEMON_BIN" -version 2>&1 | head -1
    fi
  fi
  echo ""
fi

if [ -d "$DAEMON_BIN" ]; then rm -rf "$DAEMON_BIN"; fi
mkdir -p /opt/masternoder2d

if [ "$MODE" = "repair" ]; then
  need_fetch=0
  [ -x "$DAEMON_BIN" ] || need_fetch=1
  [ -x "$CLI_BIN" ] || need_fetch=1
  if [ "$need_fetch" = 1 ]; then
    echo "== fetch v1.2.3.0 =="
    cd /tmp && rm -rf masternoder2d.tar.gz masternoder2d
    curl -fsSL -o masternoder2d.tar.gz "$RELEASE_URL"
    tar -xzf masternoder2d.tar.gz
    cp masternoder2d/masternoder2d "$DAEMON_BIN"
    cp masternoder2d/masternoder2-cli "$CLI_BIN"
    cp masternoder2d/masternoder2-cli /usr/local/bin/masternoder2-cli
    chmod +x "$DAEMON_BIN" "$CLI_BIN" /usr/local/bin/masternoder2-cli
  fi
fi

if [ -f "$UNIT" ]; then
  sed -i 's|^ExecStart=.*|ExecStart=/opt/masternoder2d/masternoder2d -datadir=/var/www/html/config|' "$UNIT"
  systemctl daemon-reload
  grep '^ExecStart=' "$UNIT"
fi

echo "== start daemon =="
systemctl start masternoder2d
sleep 25
systemctl is-active masternoder2d || true
systemctl status masternoder2d --no-pager -l | tail -15
echo ""
"$CLI_BIN" getstakinginfo 2>&1 | head -c 400 || true
echo ""
ENDSCRIPT
"""


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Repair MN2 daemon binary paths + systemd ExecStart")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--diagnose", action="store_true", help="Print debug.log, masternode.conf, foreground crash test")
    p.add_argument("--fix-segv", action="store_true",
                   help="Diagnose SEGV; quarantine bad masternode.conf or rollback to v1.2.2.0")
    args = p.parse_args()

    mode = "fix-segv" if args.fix_segv else ("diagnose" if args.diagnose else "repair")

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    script = REPAIR_SCRIPT.replace("__RELEASE_URL__", RELEASE_URL).replace("__MODE__", mode)
    _, stdout, stderr = ssh.exec_command(script, get_pty=True, timeout=300)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()
    ok = code == 0 and "active" in out and "FAIL" not in out.split("== rollback")[0]
    return 0 if ok else (code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
