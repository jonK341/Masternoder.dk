#!/usr/bin/env python3
"""Quick post-restart test: new RPC wrappers + provision-pending."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

REMOTE = r"""bash -s <<'ENDSCRIPT'
set -e
cd /var/www/html
echo "== code on server =="
grep -c createmasternodekey backend/services/mn2_masternode_service.py || echo 0
echo "== uwsgi =="
systemctl is-active uwsgi-vidgenerator
echo "== daemon RPC createmasternodekey =="
U=$(grep '^MN2_RPC_USER=' .env | cut -d= -f2- | tr -d '\r"')
P=$(grep '^MN2_RPC_PASSWORD=' .env | cut -d= -f2- | tr -d '\r"')
curl -s -u "$U:$P" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"createmasternodekey","params":[]}' \
  http://127.0.0.1:9332/ | head -c 220
echo ""
echo "== masternode.conf permissions =="
touch /var/www/html/config/masternode.conf
chown www-data:www-data /var/www/html/config/masternode.conf
chmod 664 /var/www/html/config/masternode.conf
ls -la /var/www/html/config/masternode.conf
echo ""
echo "== provision-pending =="
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
curl -s -X POST -H "X-Ops-Secret: $SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=10"
echo ""
echo "== service snapshot =="
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | head -c 600
echo ""
ENDSCRIPT
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()
    ok = (
        "createmasternodekey" in out
        and "Method not found" not in out
        and "active" in out
    )
    if '"success":true' in out.replace(" ", "") or '"success": true' in out:
        if "Method not found" in out:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
