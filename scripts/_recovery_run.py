import sys
sys.path.insert(0, r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk")
from deploy_ssh_env import connect_deploy_ssh

RECOVERY = r"""
set -e
echo "=== SYSTEMCTL STATUS (before) ==="
systemctl status uwsgi-vidgenerator uwsgi-vidgenerator-5001 nginx masternoder2d --no-pager -l 2>&1 | head -80 || true
echo ""
echo "=== RESTART UWSGI ==="
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
sleep 3
echo ""
echo "=== SYSTEMCTL STATUS (after restart) ==="
for s in uwsgi-vidgenerator uwsgi-vidgenerator-5001 nginx masternoder2d; do
  st=$(systemctl is-active $s 2>/dev/null || echo unknown)
  echo "$s: $st"
done
echo ""
echo "=== CURL LOCAL 5000 ==="
curl -s -m 10 -w "\nLOCAL_HTTP:%{http_code}\n" http://127.0.0.1:5000/api/mn2/health || echo LOCAL_CURL_FAILED
echo ""
echo "=== CURL LOCAL HTTPS (nginx) ==="
curl -s -m 10 -k -w "\nHTTPS_LOCAL_HTTP:%{http_code}\n" https://127.0.0.1/api/mn2/health -H "Host: masternoder.dk" || echo HTTPS_LOCAL_FAILED
echo ""
echo "=== CURL PUBLIC HTTPS from server ==="
curl -s -m 15 -w "\nPUBLIC_HTTP:%{http_code}\n" https://masternoder.dk/api/mn2/health || echo PUBLIC_CURL_FAILED
echo ""
echo "=== EXCHANGE MASTER LOG (tail 25) ==="
tail -n 25 /var/log/masternoder-exchange-master.log 2>/dev/null || echo "no exchange log"
echo ""
echo "=== LOAD / MEM ==="
uptime
free -h 2>/dev/null | head -3 || true
"""

ssh, auth, _ = connect_deploy_ssh(timeout=60)
print(f"SSH via {auth}", flush=True)
_, stdout, stderr = ssh.exec_command(RECOVERY, timeout=120)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
print(out)
if err.strip():
    print("STDERR:", err, file=sys.stderr)
code = stdout.channel.recv_exit_status()
print(f"REMOTE_EXIT: {code}")
ssh.close()
