#!/usr/bin/env python3
"""
Fix masternoder2.conf masternode=1 crash loop and broadcast fleet from masternode.conf.

MasterNoder2 requires masternodeprivkey= in masternoder2.conf when masternode=1 is set.
Multi-slot hosting uses masternode.conf + startmasternode alias (no masternode=1 needed).

Usage (from repo root):
  python scripts/mn2_masternode_start_fleet_remote.py --ask-pass
  python scripts/mn2_masternode_start_fleet_remote.py --ask-pass --dry-run
"""
import argparse
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass


def sh(ssh, cmd, timeout=180):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


REMOTE = r'''bash -s <<'ENDSCRIPT'
set -e
CONF=/var/www/html/config/masternoder2.conf
D="-datadir=/var/www/html/config"
CLI="/opt/masternoder2d/masternoder2-cli $D"

echo "== masternode settings in masternoder2.conf =="
grep -nE '^(masternode|masternodeprivkey|masternodeaddr)=' "$CONF" 2>/dev/null || echo "(none)"

if grep -q '^masternode=1' "$CONF" 2>/dev/null && ! grep -q '^masternodeprivkey=' "$CONF" 2>/dev/null; then
  echo "== removing masternode=1 (requires masternodeprivkey; fleet uses alias start) =="
  sed -i '/^masternode=1$/d' "$CONF"
  systemctl restart masternoder2d
else
  echo "== conf OK or local MN fully configured; ensuring daemon up =="
  systemctl start masternoder2d 2>/dev/null || true
fi

echo "== wait for RPC (up to 120s) =="
for i in $(seq 1 24); do
  if systemctl is-active --quiet masternoder2d && $CLI getblockcount 2>/dev/null | grep -qE '^[0-9]+$'; then
    echo "RPC ready after ${i}x5s"
    break
  fi
  sleep 5
done

systemctl is-active masternoder2d || { systemctl status masternoder2d --no-pager -l | tail -15; exit 1; }
HEIGHT=$($CLI getblockcount 2>/dev/null || echo -1)
echo "getblockcount=$HEIGHT"
if [ "$HEIGHT" = "-1" ]; then
  echo "WARN: chain still loading — wait and re-run alias starts"
fi

echo ""
echo "== listmasternodeconf =="
$CLI listmasternodeconf

echo ""
echo "== startmasternode alias for each configured alias =="
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
  echo "--- $a ---"
  $CLI startmasternode alias false "$a"
done

echo ""
echo "== results =="
$CLI getmasternodecount
$CLI listmasternodes | head -c 4000
echo ""
ENDSCRIPT
'''


def main():
    p = argparse.ArgumentParser(description="Fix MN2 conf and start masternode fleet on production")
    p.add_argument("--ask-pass", action="store_true", help="Prompt SSH password")
    p.add_argument("--dry-run", action="store_true", help="Print remote script only")
    args = p.parse_args()

    if args.dry_run:
        print(REMOTE)
        return 0

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    print(f"== Connected {deploy_user()}@{deploy_host()} ==\n")
    out = sh(ssh, REMOTE, timeout=240)
    print(out)
    ssh.close()
    ok = "getblockcount=" in out and "couldn't connect" not in out
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
