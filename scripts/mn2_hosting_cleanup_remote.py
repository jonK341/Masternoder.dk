#!/usr/bin/env python3
"""Purge stuck masternode hosting registry rows and report slot capacity on production."""

from __future__ import annotations

import argparse
import json
import os
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 180) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Remote purge of stale MN2 masternode host rows")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Report what would be removed without deleting")
    p.add_argument(
        "--max-age-hours",
        type=float,
        default=0,
        help="Age threshold for stale provisioning rows (0 = force all no-collateral)",
    )
    args = p.parse_args()

    force = args.max_age_hours <= 0
    body = json.dumps({
        "force_no_collateral": force,
        "max_age_hours": max(0.0, args.max_age_hours),
        "dry_run": args.dry_run,
    })

    remote = rf'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
if [ -z "$SECRET" ]; then echo "FAIL no MN2_OPS_SECRET in .env"; exit 1; fi

echo "== before =="
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('hosted_count=', d.get('hosted_count'), 'slots_available=', d.get('slots_available'),
      'registry_count=', d.get('registry_count', len(d.get('hosts') or [])))
"

echo ""
echo "== purge stale hosts =="
curl -s -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{body}' \
  http://127.0.0.1:5000/api/mn2/masternode/purge-stale-hosts
echo ""

echo ""
echo "== after =="
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('hosted_count=', d.get('hosted_count'), 'slots_available=', d.get('slots_available'),
      'registry_count=', d.get('registry_count', len(d.get('hosts') or [])),
      'stale_provisioning=', d.get('stale_provisioning_count'))
"

echo ""
echo "== provision retry =="
curl -s -X POST -H "X-Ops-Secret: $SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=10" | head -c 1200
echo ""
ENDSCRIPT'''

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    print(f"== Connected {deploy_user()}@{deploy_host()} ==\n")
    out = sh(ssh, remote, timeout=180)
    print(out)
    ssh.close()
    ok = "slots_available=" in out and "FAIL" not in out
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
