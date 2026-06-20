#!/usr/bin/env python3
"""Check confirmed 10k collateral UTXOs on production."""
import argparse
import os
import sys

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

REMOTE = r'''bash -s <<'EOF'
D="-datadir=/var/www/html/config"
CLI="/opt/masternoder2d/masternoder2-cli $D"
echo "== daemon =="
systemctl is-active masternoder2d || true
echo "== getbalance =="
$CLI getbalance 2>&1
echo ""
echo "== 10k UTXOs =="
$CLI listunspent 1 9999999 > /tmp/mn2_unspent.json 2>&1 || true
python3 /tmp/mn2_check_unspent.py 2>&1 || python3 - <<'PY'
import json
rows=json.load(open("/tmp/mn2_unspent.json"))
hits=[u for u in rows if abs(float(u.get("amount") or 0)-10000)<1e-6]
print("total_10k:", len(hits))
for u in sorted(hits, key=lambda x: -int(x.get("confirmations") or 0)):
    print(u["txid"], "vout="+str(u["vout"]), "conf="+str(u.get("confirmations")), u.get("address",""))
confirmed=[u for u in hits if int(u.get("confirmations") or 0)>=10]
print("confirmed_10plus:", len(confirmed))
PY
echo ""
echo "== getmasternodecount =="
$CLI getmasternodecount 2>&1
echo ""
echo "== listmasternodeconf =="
$CLI listmasternodeconf 2>&1 | head -c 3000
echo ""
echo "== masternode.conf =="
cat /var/www/html/config/masternode.conf 2>/dev/null || echo "(missing)"
EOF
'''


def main():
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
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
