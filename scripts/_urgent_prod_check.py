#!/usr/bin/env python3
"""Urgent production diagnostic for wallet/daemon/masternode orders."""
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
echo '== SYSTEMCTL =='
systemctl status masternoder2d --no-pager -l 2>&1 | head -25
echo
systemctl status masternoder-profit-daemon --no-pager -l 2>&1 | head -15
echo
echo '== RPC DIRECT =='
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -m 5 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/ 2>&1
echo
echo '== PORT 9332 =='
ss -tlnp | grep 9332 || echo '9332 not listening'
echo '== MEM =='
free -h | head -2
echo '== RECENT ORDERS =='
if [ -f /var/www/html/logs/mn2_masternode_orders.jsonl ]; then
  tail -10 /var/www/html/logs/mn2_masternode_orders.jsonl
elif [ -f /var/www/html/data/mn2_masternode_orders.json ]; then
  python3 -c "import json; d=json.load(open('/var/www/html/data/mn2_masternode_orders.json')); items=d if isinstance(d,list) else list(d.values()); print(json.dumps(items[-5:], indent=2))"
else
  ls -la /var/www/html/data/*masternode* /var/www/html/logs/*masternode* 2>/dev/null
fi
echo '== PENDING ORDERS =='
cd /var/www/html && LITE_APP=1 python3 -c "
import json
try:
    from backend.services.mn2_masternode_hosting_service import list_orders
    orders = list_orders(limit=10)
    pending = [o for o in orders if o.get('status') in ('pending','paid','provisioning')]
    print(json.dumps({'total': len(orders), 'pending_recent': pending[:5]}, indent=2, default=str))
except Exception as e:
    print('order check error:', e)
" 2>&1 | head -80
echo '== JOURNAL mn2 last 15 =='
journalctl -u masternoder2d --no-pager -n 15 2>/dev/null
echo '== UWSGI =='
systemctl is-active uwsgi 2>/dev/null; ps aux | grep '[u]wsgi' | head -2
echo '== MN2 CHECKOUT QUOTE TEST =='
curl -sS -m 15 -X POST http://127.0.0.1:5000/api/mn2/masternode/hosting/quote \
  -H 'content-type: application/json' \
  -d '{"slots":1,"payment_rail":"paypal"}' 2>&1 | head -c 600
echo
ENDSCRIPT"""


def public_checks() -> None:
    print("\n=== PUBLIC API ===")
    urls = [
        "https://masternoder.dk/api/mn2/explorer/status",
        "https://masternoder.dk/api/mn2/masternode/service",
        "https://masternoder.dk/api/shop/payment-health",
    ]
    for url in urls:
        print(f"\n--- {url} ---")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "UrgentCheck/1.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                d = json.loads(resp.read().decode())
            if "checks" in d:
                print(f"status={d.get('status')} rpc={d.get('checks',{}).get('rpc')}")
            elif "hosting_stats" in d:
                hs = d.get("hosting_stats") or {}
                print(f"enabled={d.get('enabled')} pending={hs.get('pending_orders')} paid={hs.get('paid_orders')}")
            else:
                print(json.dumps(d, indent=2)[:800])
        except Exception as exc:
            print(f"FAIL: {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=90)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        print("\nSTDERR:", err[:500])
    public_checks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
