#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
echo '== UWSGI =='
ps aux | grep '[u]wsgi' | head -5
echo '== LOCAL HTTP =='
curl -sS -m 10 -o /dev/null -w 'payment-health:%{http_code}\n' http://127.0.0.1:5000/api/shop/payment-health
curl -sS -m 15 -o /dev/null -w 'masternode-service:%{http_code}\n' http://127.0.0.1:5000/api/mn2/masternode/service
curl -sS -m 30 -o /dev/null -w 'checkout-quote:%{http_code}\n' -X POST http://127.0.0.1:5000/api/mn2/masternode/checkout/quote -H 'content-type: application/json' -d '{"slots":1,"payment_rail":"paypal","user_id":"test"}'
echo '== MN2 PROCESS =='
pgrep -a masternoder2d || echo 'no mn2'
systemctl is-active masternoder2d
tail -3 /var/log/mn2-reindex.log 2>/dev/null || echo 'no reindex log'
ENDSCRIPT"""

ssh, auth, _ = connect_deploy_ssh()
print(f"Connected ({auth})\n")
_, o, _ = ssh.exec_command(REMOTE, timeout=90)
print(o.read().decode())
ssh.close()
