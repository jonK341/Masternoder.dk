import sys, os
os.chdir(r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

checks = r"""
set +e
echo "=== TIMESTAMP ==="
date -u
echo
echo "=== DISK / MEMORY ==="
df -h / | tail -1
free -h | head -2
echo
echo "=== UWSGI ==="
systemctl is-active uwsgi-vidgenerator 2>/dev/null; systemctl is-active uwsgi-vidgenerator-5001 2>/dev/null
systemctl status uwsgi-vidgenerator --no-pager -l 2>/dev/null | head -8
echo
echo "=== NGINX ==="
systemctl is-active nginx 2>/dev/null || echo nginx-n/a
systemctl status nginx --no-pager 2>/dev/null | head -5
echo
echo "=== HTTP LOCALHOST ==="
for u in \
  "http://127.0.0.1:5000/" \
  "http://127.0.0.1:5000/api/mn2/health" \
  "http://127.0.0.1:5000/casino/" \
  "http://127.0.0.1:5000/api/exchange/sales-pool/status" \
  "http://127.0.0.1:5000/explorer/" \
  "http://127.0.0.1:5001/"
do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "$u" 2>/dev/null || echo curl-fail)
  echo "$code $u"
done
echo
echo "=== HTTP PUBLIC FROM SERVER ==="
for u in \
  "https://masternoder.dk/" \
  "https://masternoder.dk/api/mn2/health"
do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$u" 2>/dev/null || echo curl-fail)
  echo "$code $u"
done
echo
echo "=== AGENT STATE ==="
AS=/var/www/html/data/crypto_exchange/agent_state.json
if [ -f "$AS" ]; then
  python3 << 'PY'
import json, os
p="/var/www/html/data/crypto_exchange/agent_state.json"
d=json.load(open(p))
print("last_tick", d.get("last_tick") or d.get("last_tick_utc"))
print("tick_count", d.get("tick_count"))
PY
  stat -c "mtime %y" "$AS"
else echo "MISSING $AS"; fi
echo
echo "=== EXCHANGE MASTER LOG TAIL ==="
tail -8 /var/log/masternoder-exchange-master.log 2>/dev/null || echo "no log"
echo
echo "=== CRON EXCHANGE MASTER ==="
if [ -f /etc/cron.d/masternoder-exchange-master ]; then
  echo "exists OK"
  file /etc/cron.d/masternoder-exchange-master
  cat /etc/cron.d/masternoder-exchange-master
else echo "MISSING cron file"; fi
echo
echo "=== MN2 DAEMON ==="
systemctl is-active masternoder2d 2>/dev/null
/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getblockcount 2>/dev/null || echo rpc-fail
/opt/masternoder2d/masternoder2d --version 2>/dev/null || /opt/masternoder2d/masternoder2-cli -version 2>/dev/null || echo version-unknown
echo
echo "=== MN2 CRON ==="
ls -la /etc/cron.d/*mn2* /etc/cron.d/*masternoder* 2>/dev/null | head -20
echo
echo "=== MULTIPING / PING WATCH ==="
if [ -f /var/www/html/data/mn2_ping_watch.json ]; then
  python3 << 'PY'
import json
d=json.load(open("/var/www/html/data/mn2_ping_watch.json"))
for k in ("updated_at","last_ok","status","summary"):
    if k in d: print(k, d[k])
if not any(k in d for k in ("updated_at","last_ok","status","summary")):
    print("keys", list(d.keys())[:12])
PY
fi
pgrep -af multiping 2>/dev/null | head -3 || echo "no multiping proc"
echo
echo "=== LONG RUNNING DAEMONS ==="
pgrep -af "all_profit|profit_daemons" 2>/dev/null | head -10 || echo "none matched"
ps aux | grep -E "[p]ython.*daemon|[a]ll_profit" | head -8
echo
echo "=== TREASURY WALLET (MN2 balance only) ==="
TW=/var/www/html/data/crypto_exchange/wallets/platform_treasury.json
if [ -f "$TW" ]; then
  python3 << 'PY'
import json
d=json.load(open("/var/www/html/data/crypto_exchange/wallets/platform_treasury.json"))
b=d.get("balances") or d
if isinstance(b, dict):
    print("MN2", b.get("MN2"))
else:
    print("structure", type(b).__name__)
PY
fi
echo
echo "=== PAYOUT CONFIG (no secrets) ==="
PC=/var/www/html/data/crypto_exchange/payout_config.json
if [ -f "$PC" ]; then
  python3 << 'PY'
import json
d=json.load(open("/var/www/html/data/crypto_exchange/payout_config.json"))
safe={k:d.get(k) for k in d if "key" not in k.lower() and "secret" not in k.lower() and "pass" not in k.lower()}
print(json.dumps(safe, indent=0)[:800])
PY
fi
test -f /var/www/html/scripts/check_prod_binance_payout.py && echo "check_prod_binance_payout.py exists"
"""

ssh, auth, _ = connect_deploy_ssh()
print(f"Connected ({auth})")
try:
    _, stdout, stderr = ssh.exec_command(checks, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out.rstrip())
    if err.strip():
        print("STDERR:", err.strip()[-800:])
finally:
    ssh.close()
