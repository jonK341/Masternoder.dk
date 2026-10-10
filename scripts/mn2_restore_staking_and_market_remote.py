#!/usr/bin/env python3
"""
Restore MN2 daemon staking (unlock wallet) and kick trader agent market activity.

Usage:
  python scripts/mn2_restore_staking_and_market_remote.py --ask-pass
  python scripts/mn2_restore_staking_and_market_remote.py --ask-pass --market-rounds 3
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 180) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Unlock staking + run trader market on production")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--market-rounds", type=int, default=2, help="How many run-market ticks")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    rounds = max(1, int(args.market_rounds))
    remote = f'''bash -s <<'ENDSCRIPT'
set +e
cd {WEB}
RPC_USER=$(grep '^MN2_RPC_USER=' .env | cut -d= -f2- | tr -d '\\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' .env | cut -d= -f2- | tr -d '\\r"')
RPC_URL=$(grep '^MN2_RPC_URL=' .env | cut -d= -f2- | tr -d '\\r"')
RPC_URL=${{RPC_URL:-http://127.0.0.1:9332}}
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\\r"')

rpc() {{
  curl -s -m 25 -u "$RPC_USER:$RPC_PASS" -H 'Content-Type: application/json' \\
    -d "$1" "$RPC_URL/"
}}

echo "== getstakingstatus (before) =="
rpc '{{"jsonrpc":"1.0","id":"ops","method":"getstakingstatus","params":[]}}'
echo ""

echo "== unlock wallet + check staking =="
python3 - <<'PY'
import json, os, subprocess, urllib.request, base64
from datetime import datetime, timezone

def load_env(path):
    out = {{}}
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

env = load_env(".env")
rpc_url = env.get("MN2_RPC_URL") or "http://127.0.0.1:9332"
user = env.get("MN2_RPC_USER", "")
password = env.get("MN2_RPC_PASSWORD", "")
pw = env.get("MN2_WALLET_PASSPHRASE", "")

def rpc_call(method, params=None):
    body = json.dumps({{"jsonrpc": "1.0", "id": "ops", "method": method, "params": params or []}}).encode()
    req = urllib.request.Request(rpc_url, data=body, headers={{"Content-Type": "application/json"}})
    token = base64.b64encode(f"{{user}}:{{password}}".encode()).decode()
    req.add_header("Authorization", f"Basic {{token}}")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())

def staking_on(payload):
    r = payload.get("result") if isinstance(payload, dict) else {{}}
    if not isinstance(r, dict):
        return False
    return bool(r.get("staking status") or r.get("staking_status"))

before = rpc_call("getstakingstatus")
print("staking_before=", staking_on(before))

if pw:
    try:
        rpc_call("walletpassphrase", [pw, 0, True])
        print("walletpassphrase: OK")
    except Exception as exc:
        print("walletpassphrase: FAIL", exc)
else:
    print("WARN: MN2_WALLET_PASSPHRASE missing in .env")

after = rpc_call("getstakingstatus")
print("staking_after=", staking_on(after))

if staking_on(after):
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rec = {{"ts": ts, "type": "staking_resumed", "message": "MN2 daemon staking active again. Realized yield accrual resumed."}}
    with open("logs/mn2_network_alerts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\\n")
PY

echo ""
echo "== trader market ticks ({rounds}x) =="
for i in $(seq 1 {rounds}); do
  echo "-- round $i --"
  curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/agents/trader-staking/run-market | head -c 900
  echo ""
  curl -s -X POST -H "X-Ops-Secret: $SECRET" "http://127.0.0.1:5000/api/agents/cron/run?jobs=agent_trader" | head -c 400
  echo ""
  sleep 2
done

echo ""
echo "== market ticker =="
curl -s http://127.0.0.1:5000/api/market/ticker
echo ""
echo "== recent trades =="
curl -s 'http://127.0.0.1:5000/api/market/trades?limit=5'
echo ""
ENDSCRIPT
'''

    if args.dry_run:
        print(remote)
        return 0

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, auth_method, _ = connect_deploy_ssh(pw)
    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==")
    print("Running on server (wallet unlock + 3 market ticks ÔÇö may take 1ÔÇô3 min, output appears when done)...\n")
    out = sh(ssh, remote, timeout=300)
    print(out)
    ssh.close()

    ok = "staking_after= True" in out or "staking_after=True" in out
    print("\n" + ("Staking + market restore completed." if ok else "[WARN] Staking may still be off ÔÇö check output."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
