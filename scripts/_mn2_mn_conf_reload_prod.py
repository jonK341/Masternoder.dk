#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'E'
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
CONF=/var/www/html/config/masternode.conf

echo "== file vs daemon =="
echo "file platformmn2 tx:" $(awk '/^platformmn2 / {print $4}' $CONF)
echo "daemon platformmn2 tx:" $($CLI listmasternodeconf 2>/dev/null | python3 -c 'import json,sys; r=json.load(sys.stdin); print([x.get("txHash") for x in r if x.get("alias")=="platformmn2"][0][:16])')

echo "== conf file mtime =="
stat $CONF

echo "== other masternode.conf =="
find /var/www/html /root -name 'masternode.conf' 2>/dev/null

echo "== masternoder2.conf masternode lines =="
grep -E '^(masternode|masternodeconf|datadir)=' /var/www/html/config/masternoder2.conf 2>/dev/null

echo "== stop daemon hard reload =="
systemctl stop masternoder2d
sleep 5
pkill -9 masternoder2d 2>/dev/null || true
sleep 2
systemctl start masternoder2d
for i in $(seq 1 24); do
  sleep 5
  bc=$($CLI getblockcount 2>/dev/null)
  [ -n "$bc" ] && [ "$bc" -gt 0 ] 2>/dev/null && echo "ready $bc" && break
done

echo "== after hard restart =="
echo "file:" $(awk '/^platformmn2 / {print $4}' $CONF | cut -c1-16)
$CLI listmasternodeconf 2>/dev/null | python3 -c 'import json,sys; r=json.load(sys.stdin); x=[a for a in r if a.get("alias")=="platformmn2"][0]; print("daemon:", x.get("txHash","")[:16], x.get("status"))'

echo "== mnsync =="
$CLI mnsync status 2>&1 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d)' 2>/dev/null
E
"""

def main():
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, _ = ssh.exec_command(REMOTE, timeout=180)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    ssh.close()

if __name__ == "__main__":
    main()
