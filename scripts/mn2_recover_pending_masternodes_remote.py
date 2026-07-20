#!/usr/bin/env python3
"""
Recover pending masternode hosts via SSH: restart daemon, rebind collateral, provision.

  python scripts/mn2_recover_pending_masternodes_remote.py --ask-pass
  python scripts/mn2_recover_pending_masternodes_remote.py --ask-pass --no-restart
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 900) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Recover pending MN2 masternode fleet on server")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--no-restart", action="store_true", help="Skip systemctl restart masternoder2d")
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()

    if args.ask_pass:
        require_deploy_pass(force_prompt=True)

    restart = "0" if args.no_restart else "1"
    remote = rf'''bash -s <<'ENDSCRIPT'
set -euo pipefail
WEB="{WEB}"
cd "$WEB"
chmod +x cron/mn2_masternode_daemon_recover.sh cron/mn2_masternode_provision.sh 2>/dev/null || true
if [ -f cron/masternoder-mn2-masternode-provision.cron.d ]; then
  cp cron/masternoder-mn2-masternode-provision.cron.d /etc/cron.d/masternoder-mn2-masternode-provision
  chmod 644 /etc/cron.d/masternoder-mn2-masternode-provision
fi
if [ -f scripts/mn2_fix_config_permissions.sh ]; then
  bash scripts/mn2_fix_config_permissions.sh 2>/dev/null || true
fi
if [ "{restart}" = "1" ]; then
  echo "== restart masternoder2d =="
  systemctl restart masternoder2d
  sleep 25
  systemctl is-active masternoder2d
  /opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getblockcount 2>&1 || true
fi
echo ""
echo "== fleet start =="
python3 scripts/mn2_start_masternode.py --all-from-conf 2>&1 | tail -40 || true
echo ""
echo "== provision recover API =="
# shellcheck source=/dev/null
source cron/mn2_read_ops_secret.sh
curl -s -X POST -H "X-Ops-Secret: ${{MN2_OPS_SECRET}}" \
  "http://127.0.0.1:5000/api/mn2/masternode/recover?limit={args.limit}&restart_daemon=0" | python3 -m json.tool
echo ""
echo "== service status =="
curl -s "http://127.0.0.1:5000/api/mn2/masternode/service?fresh=1" | python3 -c "
import json,sys
from collections import Counter
d=json.load(sys.stdin)
hosts=d.get('hosts',[])
c=Counter((h.get('status') or '?').lower() for h in hosts)
print('status', dict(c))
print('rpc', (d.get('network') or {{}}).get('rpc_error'))
print('collateral_outputs', d.get('collateral_outputs_available'))
"
ENDSCRIPT'''

    host = deploy_host()
    user = deploy_user()
    print(f"Connecting to {user}@{host} ...", flush=True)
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected via {auth}", flush=True)
    try:
        print(sh(ssh, remote.format(WEB=WEB, restart=restart, args=args), timeout=1200))
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
