import sys, time
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

REMOTE = """
set +e
echo "=== find mn2.conf ==="
find /var/www/html -name "mn2.conf" -o -name "masternoder2.conf" 2>/dev/null | head -5
ls -la /var/www/html/config/ 2>/dev/null | head -15

echo "=== systemd unit datadir ==="
grep ExecStart /etc/systemd/system/masternoder2d.service

sleep 45
echo "=== after 45s sync ==="
masternoder2-cli -datadir=/var/www/html/config getblockcount 2>&1
tail -8 /var/www/html/config/debug.log 2>/dev/null

CONF=$(find /var/www/html -name mn2.conf 2>/dev/null | head -1)
if [ -n "$CONF" ]; then
  DD=$(dirname "$CONF")
  masternoder2-cli -datadir="$DD" getblockcount 2>&1
fi

echo "=== health localhost + public path via curl localhost ==="
curl -s -w "\\nHTTP:%{http_code}\\n" http://127.0.0.1:5000/api/mn2/health | tail -5
"""

ssh, auth, _ = connect_deploy_ssh(timeout=60)
_, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
print(stdout.read().decode(errors="replace").encode("ascii","backslashreplace").decode())
ssh.close()
