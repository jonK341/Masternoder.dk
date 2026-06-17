#!/usr/bin/env python3
"""
Run remaining MN2 production ops in one SSH session (password via --ask-pass).

  python scripts/mn2_next_ops_remote.py --ask-pass
  python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking
  python scripts/mn2_next_ops_remote.py --ask-pass --camgirls
"""
from __future__ import annotations

import argparse
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 180) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 next ops: crons, fleet verify, optional restore/camgirls")
    p.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (required if .env DEPLOY_PASS is stale)")
    p.add_argument("--restore-staking", action="store_true", help="Unlock wallet + run trader market ticks")
    p.add_argument("--camgirls", action="store_true", help="Provision payout addresses + post-deploy verify + Discord spotlight")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    remote = rf'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}

echo "== masternode provision cron =="
chmod +x cron/mn2_masternode_provision.sh 2>/dev/null || true
if [ -f cron/masternoder-mn2-masternode-provision.cron.d ]; then
  cp cron/masternoder-mn2-masternode-provision.cron.d /etc/cron.d/masternoder-mn2-masternode-provision
  chmod 644 /etc/cron.d/masternoder-mn2-masternode-provision
  echo "OK masternode provision cron"
else
  echo "WARN masternode provision cron.d missing"
fi

echo ""
echo "== discord market fan-out cron =="
chmod +x cron/discord_market_fanout.sh 2>/dev/null || true
if [ -f cron/masternoder-discord-market.cron.d ]; then
  cp cron/masternoder-discord-market.cron.d /etc/cron.d/masternoder-discord-market
  chmod 644 /etc/cron.d/masternoder-discord-market
  echo "OK discord market cron"
else
  echo "WARN discord market cron.d missing — deploy mn2_staking first"
fi

echo ""
echo "== monetization retention cron =="
chmod +x cron/monetization_cron.sh 2>/dev/null || true
if [ -f cron/masternoder-monetization.cron.d ]; then
  cp cron/masternoder-monetization.cron.d /etc/cron.d/masternoder-monetization
  chmod 644 /etc/cron.d/masternoder-monetization
  echo "OK monetization cron (needs AGENT_CRON_SECRET + NOTIFY_SMTP_* for emails)"
else
  echo "WARN monetization cron.d missing"
fi

SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
echo ""
echo "== verify masternode service API =="
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | python3 -c "
import json,sys
d=json.load(sys.stdin)
if not d.get('success'):
    print('FAIL', d); sys.exit(1)
pp=d.get('paypal') or {{}}
print('OK max_hosted_nodes=', d.get('max_hosted_nodes'),
    'price_usd=', pp.get('price_usd_per_slot'),
    'hosted_count=', d.get('hosted_count'),
    'slots_available=', d.get('slots_available'))
hosts=d.get('hosts') or []
print('fleet:', ', '.join(h.get('id','?') for h in hosts[:10]))
"

echo ""
echo "== provision retry =="
curl -s -X POST -H "X-Ops-Secret: $SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=10" | head -c 800
echo ""
ENDSCRIPT
'''

    if args.dry_run:
        print(remote)
        if args.restore_staking:
            print("\n# would also run mn2_restore_staking_and_market_remote.py logic")
        if args.camgirls:
            print("\n# would also run camgirls provision + verify + spotlight")
        return 0

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    print(f"== Connected {deploy_user()}@{deploy_host()} ==\n")
    out = sh(ssh, remote, timeout=120)
    print(out)
    ok = "OK max_hosted_nodes=" in out and "FAIL" not in out

    if args.restore_staking:
        ssh.close()
        import subprocess
        restore = os.path.join(os.path.dirname(__file__), "mn2_restore_staking_and_market_remote.py")
        cmd = [sys.executable, restore]
        if args.ask_pass:
            cmd.append("--ask-pass")
        return subprocess.call(cmd)

    if args.camgirls:
        print("\n== Camgirls server ops ==")
        cg = rf'''bash -s <<'ENDCG'
set +e
cd {WEB}
bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py
bash scripts/camgirls_py.sh scripts/camgirls_post_deploy_verify.py
source cron/mn2_read_ops_secret.sh 2>/dev/null || true
SECRET=$(mn2_read_ops_secret 2>/dev/null || grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
curl -s -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{{"title":"Live AI performers","summary":"Nova, Luna, Sage, Ember, Iris — camgirls.masternoder.dk","href":"/camgirls/"}}' \
  http://127.0.0.1:5000/api/discord/m8/partner-spotlight
echo ""
ENDCG'''
        print(sh(ssh, cg, timeout=180))

    ssh.close()
    print("\nNext ops completed." if ok else "\n[WARN] Check output above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
