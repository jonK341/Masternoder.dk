#!/usr/bin/env python3
"""Verify checkout routes and order state on production."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== BLUEPRINT CHECK =='
cd /var/www/html && LITE_APP=1 python3 -c "
from backend.app import create_app
app = create_app()
bps = sorted(app.blueprints.keys())
print('blueprints:', [b for b in bps if 'mn2' in b or 'masternode' in b])
for rule in app.url_map.iter_rules():
    if 'checkout' in rule.rule and 'masternode' in rule.rule:
        print(rule.rule, rule.methods)
" 2>&1 | head -30

echo '== RECENT JSONL ORDERS =='
tail -15 /var/www/html/logs/mn2_masternode_orders.jsonl 2>/dev/null || echo 'no jsonl'

echo '== DAEMON NOW =='
systemctl is-active masternoder2d
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/ 2>&1
echo
ss -tlnp | grep 9332 || echo '9332 down'
ENDSCRIPT"""


def public_checkout() -> None:
    print("\n=== PUBLIC CHECKOUT ===")
    url = "https://masternoder.dk/api/mn2/masternode/checkout/quote"
    body = json.dumps({"slots": 1, "payment_rail": "paypal", "user_id": "prod-verify"}).encode()
    try:
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "CheckoutVerify/1.0"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            d = json.loads(resp.read().decode())
        print(json.dumps(d, indent=2)[:1500])
    except Exception as exc:
        print(f"FAIL: {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=120)
    print(stdout.read().decode("utf-8", errors="replace"))
    ssh.close()
    public_checkout()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
