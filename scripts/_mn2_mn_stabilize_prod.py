#!/usr/bin/env python3
"""Stabilize masternoder2d and wait for RPC."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'E'
systemctl is-active masternoder2d
journalctl -u masternoder2d --no-pager -n 8
grep -i 'Loading wallet' /var/www/html/config/debug.log | tail -2
systemctl restart masternoder2d
U=$(grep ^MN2_RPC_USER= /var/www/html/.env|cut -d= -f2-|tr -d '\r"')
P=$(grep ^MN2_RPC_PASSWORD= /var/www/html/.env|cut -d= -f2-|tr -d '\r"')
for i in $(seq 1 48); do
  sleep 5
  OUT=$(curl -sS -m 5 -u "$U:$P" -H 'content-type: application/json' -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result'); print(r if isinstance(r,int) else '')" 2>/dev/null)
  if [ -n "$BC" ] && [ "$BC" -gt 1000 ] 2>/dev/null; then
    echo "RPC OK block=$BC poll=$i"
    /opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getmasternodecount
    exit 0
  fi
  echo "poll $i: waiting ($OUT)"
done
echo "FAIL RPC timeout"
tail -3 /var/www/html/config/debug.log
E
"""

def main():
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, _ = ssh.exec_command(REMOTE, timeout=300)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    ssh.close()

if __name__ == "__main__":
    main()
