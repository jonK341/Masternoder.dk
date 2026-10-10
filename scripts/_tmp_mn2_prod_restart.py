import sys, time
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

REMOTE = """
set +e
echo "=== mn2/provision/exchange/multiping crons ==="
grep -rE "provision|exchange_master|multiping|mn2_" /etc/cron.d/ 2>/dev/null | grep -v "^#"

echo "=== rpc settings ==="
grep -E "rpc|server|listen|datadir" /var/www/html/config/mn2.conf 2>/dev/null | grep -v rpcpassword

echo "=== masternoder2-cli with datadir ==="
masternoder2-cli -datadir=/var/www/html/config getblockcount 2>&1
masternoder2-cli -datadir=/var/www/html/config getblockchaininfo 2>&1 | head -c 400
echo ""

RPCPORT=$(grep -E "^rpcport" /var/www/html/config/mn2.conf 2>/dev/null | cut -d= -f2 | tr -d ' ')
[ -z "$RPCPORT" ] && RPCPORT=8332
RPCUSER=$(grep -E "^rpcuser" /var/www/html/config/mn2.conf | cut -d= -f2 | tr -d ' ')
RPCPASS=$(grep -E "^rpcpassword" /var/www/html/config/mn2.conf | cut -d= -f2 | tr -d ' ')
echo "=== curl RPC port $RPCPORT ==="
curl -s --user "$RPCUSER:$RPCPASS" -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' -H 'content-type:text/plain;' "http://127.0.0.1:${RPCPORT}/" 2>&1 | head -c 300
echo ""

echo "=== free/mem ==="
free -h
echo "=== RESTART masternoder2d ==="
systemctl restart masternoder2d
sleep 30
systemctl is-active masternoder2d
masternoder2-cli -datadir=/var/www/html/config getblockcount 2>&1
curl -s --user "$RPCUSER:$RPCPASS" -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' -H 'content-type:text/plain;' "http://127.0.0.1:${RPCPORT}/" 2>&1 | head -c 300
echo ""
echo "=== HEALTH AFTER ==="
curl -s -w "\\nHTTP_CODE:%{http_code}\\n" http://127.0.0.1:5000/api/mn2/health 2>/dev/null | tail -20
"""

ssh, auth, _ = connect_deploy_ssh(timeout=60)
_, stdout, stderr = ssh.exec_command(REMOTE, timeout=180)
print(stdout.read().decode(errors="replace").encode("ascii","backslashreplace").decode())
e = stderr.read().decode(errors="replace")
if e.strip():
    print("STDERR:", e.encode("ascii","backslashreplace").decode())
ssh.close()
