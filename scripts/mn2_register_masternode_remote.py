#!/usr/bin/env python3
"""
Register the first platform masternode in data/mn2_masternode_hosts.json on the server.

Discovers the live on-chain masternode (listmasternodes) and any 10k collateral UTXO,
then POSTs to /api/mn2/masternode/hosts (ops) or writes the registry file directly.

Usage (from repo root):
  python scripts/mn2_register_masternode_remote.py --ask-pass
  python scripts/mn2_register_masternode_remote.py --ask-pass --label "Masternoder primary"
  python scripts/mn2_register_masternode_remote.py --ask-pass --dry-run
"""
import argparse
import json
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
    p = argparse.ArgumentParser(description="Register first platform masternode on production")
    p.add_argument("--ask-pass", action="store_true", help="Prompt SSH password (ignore stale .env DEPLOY_PASS)")
    p.add_argument("--dry-run", action="store_true", help="Discover only; do not register")
    p.add_argument("--label", default="Masternoder.dk primary", help="Host label in registry")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"== Connected {user}@{host} ==\n")

    discover = r'''
cd /var/www/html
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
RPC_USER=$(grep '^MN2_RPC_USER=' .env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' .env | cut -d= -f2- | tr -d '\r"')
RPC_URL=$(grep '^MN2_RPC_URL=' .env | cut -d= -f2- | tr -d '\r"')
RPC_URL=${RPC_URL:-http://127.0.0.1:9332}

rpc() {
  local method="$1"
  local params="${2:-[]}"
  curl -s -m 20 -u "$RPC_USER:$RPC_PASS" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"1.0\",\"id\":\"ops\",\"method\":\"$method\",\"params\":$params}" \
    "$RPC_URL/"
}

echo "-- listmasternodes --"
rpc listmasternodes
echo ""
echo "-- getmasternodecount --"
rpc getmasternodecount
echo ""
echo "-- listunspent 10k filter --"
rpc listunspent '[1, 9999999]' | python3 -c "
import json,sys
d=json.load(sys.stdin)
rows=d.get('result') or []
hits=[u for u in rows if isinstance(u,dict) and abs(float(u.get('amount') or 0)-10000)<1e-6]
print(json.dumps({'count': len(hits), 'outputs': hits[:5]}, indent=2))
" 2>/dev/null || echo '(listunspent parse failed)'
echo ""
echo "-- existing hosts file --"
cat data/mn2_masternode_hosts.json 2>/dev/null || echo '{}'
echo ""
echo "-- public IP hint --"
curl -s -m 5 ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}'
echo ""
echo "-- masternode.conf tail --"
tail -5 /var/www/html/config/masternode.conf 2>/dev/null || tail -5 ~/.masternoder2/masternode.conf 2>/dev/null || echo '(no masternode.conf)'
'''
    out = sh(ssh, discover, timeout=90)
    print(out)

    # Parse first masternode addr from listmasternodes JSON in output
    import re
    mn_addr = None
    mn_block = re.search(r'-- listmasternodes --\s*\n(\{.*?\})\s*\n', out, re.DOTALL)
    if mn_block:
        try:
            data = json.loads(mn_block.group(1))
            rows = data.get("result")
            if isinstance(rows, list) and rows:
                mn_addr = rows[0].get("addr")
        except Exception:
            pass
    if not mn_addr:
        m = re.search(r'"addr"\s*:\s*"([^"]+)"', out)
        if m:
            mn_addr = m.group(1)

    if not mn_addr:
        print("\n[WARN] No enabled masternode found on-chain. You may need to create 10k collateral and broadcast first.")
        ssh.close()
        return 1

    print(f"\n== On-chain masternode address: {mn_addr} ==")

    if args.dry_run:
        print("[DRY-RUN] Would register host with label:", args.label)
        ssh.close()
        return 0

    body_obj = {
        "id": "platform-mn-1",
        "label": args.label,
        "status": "active",
        "broadcast_address": mn_addr,
        "notes": "Auto-registered from listmasternodes",
    }
    body_json = json.dumps(body_obj).replace("'", "'\"'\"'")
    register_cmd = f'''
cd /var/www/html
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\\r"')
echo "Registering via API..."
curl -s -X POST -H "Content-Type: application/json" -H "X-Ops-Secret: $SECRET" \\
  -d '{body_json}' \\
  http://127.0.0.1:5000/api/mn2/masternode/hosts
echo ""
echo "Fallback: direct service write"
./venv/bin/python3 - <<'PY'
import json
import sys
sys.path.insert(0, "/var/www/html")
from backend.services import mn2_masternode_service as m
payload = {json.dumps(body_obj)}
print(json.dumps(m.register_host(payload), indent=2))
PY
echo ""
echo "-- service status --"
curl -s http://127.0.0.1:5000/api/mn2/masternode/service | head -c 1200
echo ""
'''
    reg_out = sh(ssh, register_cmd, timeout=60)
    print("\n== Register response ==")
    print(reg_out)

    ssh.close()
    if '"success": true' in reg_out.replace(" ", "") or '"success":true' in reg_out.replace(" ", ""):
        print("\nDone — first platform masternode registered.")
        return 0
    print("\n[WARN] Registration may have failed — check output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
