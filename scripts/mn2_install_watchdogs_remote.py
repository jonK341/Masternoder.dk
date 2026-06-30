#!/usr/bin/env python3
"""
Install MN2 cron watchdogs on production + run restore-staking once.

  python scripts/mn2_install_watchdogs_remote.py --ask-pass
  python scripts/mn2_install_watchdogs_remote.py --ask-pass --skip-restore
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"

REMOTE = rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}

install_cron() {{
  local src="$1" dest="$2"
  if [ -f "$src" ]; then
    cp "$src" "$dest"
    chmod 644 "$dest"
    echo "OK cron: $dest"
  else
    echo "FAIL missing $src — deploy mn2_staking first"
  fi
}}

chmod +x cron/mn2_masternode_provision.sh cron/mn2_ops_watchdog.sh 2>/dev/null || true
chmod +x scripts/mn2_staking_watchdog.py 2>/dev/null || true

echo "== install cron.d =="
install_cron cron/masternoder-mn2-masternode-provision.cron.d /etc/cron.d/masternoder-mn2-masternode-provision
install_cron cron/masternoder-mn2-watchdogs.cron.d /etc/cron.d/masternoder-mn2-watchdogs

echo ""
echo "== run watchdog once =="
bash cron/mn2_ops_watchdog.sh 2>&1 | tail -20

echo ""
echo "== cron status =="
ls -la /etc/cron.d/masternoder-mn2-masternode-provision /etc/cron.d/masternoder-mn2-watchdogs 2>/dev/null || true
tail -5 logs/mn2_watchdog.log 2>/dev/null || echo "(no watchdog log yet)"
ENDSCRIPT
'''


def main() -> int:
    p = argparse.ArgumentParser(description="Install MN2 watchdog crons + optional restore-staking")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--skip-restore", action="store_true", help="Only install crons, skip restore-staking")
    args = p.parse_args()

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, auth_method, _ = connect_deploy_ssh(pw)
    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==\n")

    _, stdout, _ = ssh.exec_command(REMOTE, timeout=180)
    out = stdout.read().decode(errors="replace")
    print(out)
    ssh.close()

    ok = "OK cron:" in out
    if not args.skip_restore:
        restore = os.path.join(ROOT, "scripts", "mn2_restore_staking_and_market_remote.py")
        cmd = [sys.executable, restore]
        if args.ask_pass:
            cmd.append("--ask-pass")
        print("\n== restore staking + trader market ==")
        rc = subprocess.call(cmd)
        if rc != 0:
            return rc

    print("\nWatchdogs installed. Logs: /var/www/html/logs/mn2_watchdog.log")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
