import sys
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

REMOTE = """
set +e
echo "=== HEALTH BEFORE (localhost) ==="
curl -s -w "\\nHTTP_CODE:%{http_code}\\n" http://127.0.0.1:5000/api/mn2/health 2>/dev/null | tail -25

echo "=== masternoder2d status ==="
systemctl is-active masternoder2d
systemctl status masternoder2d --no-pager -l 2>/dev/null | head -30

echo "=== find debug.log ==="
find /root /opt /var/lib /home -name debug.log 2>/dev/null | head -10
for d in /root/.masternoder2 /root/MasterNoder2 /opt/masternoder2* /var/lib/masternoder*; do
  [ -f "$d/debug.log" ] && echo "TAIL $d/debug.log" && tail -50 "$d/debug.log" | grep -iE "queue|Work queue|error" | tail -20
done

echo "=== crontab root ==="
crontab -l 2>/dev/null | grep -v "^#" | grep .

echo "=== masternoder2-cli ==="
command -v masternoder2-cli
masternoder2-cli getblockcount 2>&1
masternoder2-cli getnetworkinfo 2>&1 | head -5

echo "=== ps rpc heavy ==="
ps aux | grep -iE "masternoder|mn2|provision|exchange_master|multiping" | grep -v grep | head -25
"""

ssh, auth, _ = connect_deploy_ssh(timeout=60)
print(f"SSH via {auth}", flush=True)
_, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
print(stdout.read().decode(errors="replace").encode("ascii","backslashreplace").decode())
e = stderr.read().decode(errors="replace")
if e.strip():
    print("STDERR:", e)
ssh.close()

