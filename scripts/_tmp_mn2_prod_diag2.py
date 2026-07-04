import sys
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

REMOTE = """
set +e
echo "=== datadir debug.log tail ==="
tail -60 /var/www/html/config/debug.log 2>/dev/null | grep -iE "queue|Work|error|RPC" | tail -25
echo "--- last 15 lines ---"
tail -15 /var/www/html/config/debug.log 2>/dev/null

echo "=== all crontabs ==="
for f in /etc/cron.d/* /etc/cron.daily/*; do [ -f "$f" ] && echo "### $f" && grep -v "^#" "$f" 2>/dev/null | grep .; done
crontab -u www-data -l 2>/dev/null
ls -la /var/www/html/cron/ 2>/dev/null | head -20

echo "=== systemd timers (mn2/exchange/provision/ping) ==="
systemctl list-timers --all 2>/dev/null | grep -iE "mn2|exchange|provision|ping|profit|master" || systemctl list-timers --all | head -30

echo "=== mn2.conf rpc ==="
grep -E "^rpc|^server|^listen" /var/www/html/config/mn2.conf 2>/dev/null | sed 's/rpcpassword=.*/rpcpassword=***/'

echo "=== curl direct RPC getblockcount ==="
RPCUSER=$(grep rpcuser /var/www/html/config/mn2.conf | cut -d= -f2)
RPCPASS=$(grep rpcpassword /var/www/html/config/mn2.conf | cut -d= -f2)
RPCPORT=$(grep rpcport /var/www/html/config/mn2.conf | cut -d= -f2)
curl -s --user "$RPCUSER:$RPCPASS" -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' -H 'content-type:text/plain;' "http://127.0.0.1:${RPCPORT}/" 2>&1 | head -c 500
echo ""
"""

ssh, auth, _ = connect_deploy_ssh(timeout=60)
_, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
print(stdout.read().decode(errors="replace").encode("ascii","backslashreplace").decode())
ssh.close()
