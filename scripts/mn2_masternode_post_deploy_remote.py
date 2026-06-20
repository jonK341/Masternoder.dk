#!/usr/bin/env python3
"""
Post-deploy for MN2 masternode hosting: install provision cron + seed fleet slots 2–5 + verify API.

Prefer the combined ops runner (market + monetization crons):

  python scripts/mn2_next_ops_remote.py --ask-pass
  python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking --camgirls

This script remains for masternode-only re-runs:

  python scripts/mn2_masternode_post_deploy_remote.py --ask-pass
"""
import argparse
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass


def sh(ssh, cmd, timeout=120):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main():
    p = argparse.ArgumentParser(description="Masternode hosting post-deploy on production")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"== Connected {user}@{host} ==\n")

    remote_cmd = r'''
cd /var/www/html
set -e
echo "-- install masternode provision cron --"
chmod +x cron/mn2_masternode_provision.sh 2>/dev/null || true
if [ -f cron/masternoder-mn2-masternode-provision.cron.d ]; then
  cp cron/masternoder-mn2-masternode-provision.cron.d /etc/cron.d/masternoder-mn2-masternode-provision
  chmod 644 /etc/cron.d/masternoder-mn2-masternode-provision
  echo "cron installed"
else
  echo "WARN: cron file missing — run deploy mn2_staking first"
fi

SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
echo ""
echo "-- seed platform-mn-2 .. 5 --"
for n in 2 3 4 5; do
  id="platform-mn-${n}"
  curl -s -X POST -H "Content-Type: application/json" -H "X-Ops-Secret: $SECRET" \
    -d "{\"id\":\"${id}\",\"label\":\"Masternoder.dk fleet #${n}\",\"status\":\"queued\",\"notes\":\"Platform expansion slot\"}" \
    http://127.0.0.1:5000/api/mn2/masternode/hosts
  echo ""
done

echo "-- local API verify --"
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | python3 -c "
import json,sys
d=json.load(sys.stdin)
if not d.get('success'):
    print('FAIL', d); sys.exit(1)
pp=d.get('paypal') or {}
print('OK max_hosted_nodes=', d.get('max_hosted_nodes'),
      'price_usd=', pp.get('price_usd_per_slot'),
      'hosted_count=', d.get('hosted_count'),
      'slots_available=', d.get('slots_available'))
hosts=d.get('hosts') or []
print('fleet:', ', '.join(h.get('id','?') for h in hosts[:8]))
"

echo ""
echo "-- provision retry (once) --"
curl -s -X POST -H "X-Ops-Secret: $SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=10" | head -c 1200
echo ""
'''

    if args.dry_run:
        print(remote_cmd)
        ssh.close()
        return 0

    out = sh(ssh, remote_cmd, timeout=90)
    print(out)
    ssh.close()
    ok = "OK max_hosted_nodes=" in out and "FAIL" not in out
    print("\nDone." if ok else "\n[WARN] Check output above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
