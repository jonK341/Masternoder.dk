#!/usr/bin/env python3
import json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== SERVICES =='
echo "masternoder2d: $(systemctl is-active masternoder2d)"
echo "profit-daemon: $(systemctl is-active masternoder-profit-daemon.service)"
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
BC=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/)
echo "RPC: $BC"
echo '== LOCAL APIS =='
for path in /api/shop/payment-health /api/mn2/masternode/service /api/mn2/explorer/status; do
  code=$(curl -sS -m 20 -o /tmp/apitest.json -w '%{http_code}' "http://127.0.0.1:5000$path")
  echo "$path -> HTTP $code $(head -c 200 /tmp/apitest.json)"
done
echo '== CHECKOUT QUOTE =='
curl -sS -m 30 -X POST http://127.0.0.1:5000/api/mn2/masternode/checkout/quote \
  -H 'content-type: application/json' \
  -d '{"slots":1,"payment_rail":"paypal","user_id":"final-verify"}' | head -c 500
echo
echo '== EXPLORER ROUTE ON PROD =='
grep -r 'explorer/status' /var/www/html/backend/routes/ 2>/dev/null | head -3
echo '== MEM =='
free -h | head -2
echo '== journal mn2 =='
journalctl -u masternoder2d --no-pager -n 3 2>/dev/null
ENDSCRIPT"""

def public():
    print("\n=== PUBLIC (urllib) ===")
    for url in [
        "https://masternoder.dk/api/shop/payment-health",
        "https://masternoder.dk/api/mn2/masternode/service",
        "https://masternoder.dk/api/mn2/masternode/checkout/quote",
    ]:
        try:
            if "quote" in url:
                req = urllib.request.Request(url, data=json.dumps({"slots":1,"payment_rail":"paypal","user_id":"x"}).encode(),
                    method="POST", headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
            else:
                req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                print(f"{url}: HTTP {r.status} {r.read()[:300]}")
        except Exception as e:
            print(f"{url}: {e}")

ssh, auth, _ = connect_deploy_ssh()
print(f"Connected ({auth})\n")
_, o, _ = ssh.exec_command(REMOTE, timeout=120)
print(o.read().decode())
ssh.close()
public()
