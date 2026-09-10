#!/usr/bin/env python3
"""Quick uwsgi restart on production."""
import sys, time, json, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== restart uwsgi =='
systemctl restart uwsgi 2>&1
sleep 3
systemctl is-active uwsgi
ps aux | grep '[u]wsgi.*uwsgi.ini' | head -3
echo 'waiting 90s for workers...'
sleep 90
for path in /api/shop/payment-health /api/mn2/masternode/service; do
  code=$(curl -sS -m 30 -o /tmp/t.json -w '%{http_code}' "http://127.0.0.1:5000$path")
  echo "$path -> $code"
done
curl -sS -m 30 -X POST http://127.0.0.1:5000/api/mn2/masternode/checkout/quote \
  -H 'content-type: application/json' \
  -d '{"slots":1,"payment_rail":"paypal","user_id":"post-restart"}' | head -c 400
echo
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/
echo
ENDSCRIPT"""

def public():
    print("\n=== PUBLIC ===")
    url = "https://masternoder.dk/api/mn2/masternode/checkout/quote"
    req = urllib.request.Request(url, data=json.dumps({"slots":1,"payment_rail":"paypal","user_id":"post-restart"}).encode(),
        method="POST", headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"checkout: HTTP {r.status}", r.read()[:400])
    except Exception as e:
        print(f"checkout: {e}")
    try:
        with urllib.request.urlopen(urllib.request.Request("https://masternoder.dk/api/shop/payment-health", headers={"User-Agent":"Mozilla/5.0"}), timeout=30) as r:
            d = json.loads(r.read())
            print(f"payment-health: mn2={d['mn2_daemon']['status']} block={d['mn2_daemon'].get('block_height')}")
    except Exception as e:
        print(f"payment-health: {e}")

ssh, auth, _ = connect_deploy_ssh()
print(f"Connected ({auth})\n")
_, o, _ = ssh.exec_command(REMOTE, timeout=180)
print(o.read().decode())
ssh.close()
public()
