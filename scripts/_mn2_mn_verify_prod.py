#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'E'
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
echo blockcount: $($CLI getblockcount 2>&1)
echo masternodecount: $($CLI getmasternodecount 2>&1)
$CLI listunspent 0 9999999 2>/dev/null | python3 -c 'import json,sys; u=json.load(sys.stdin); c=[x for x in u if abs(float(x.get("amount",0))-5000)<0.01]; print("5000_utxos",len(c),"ge10",sum(1 for x in c if int(x.get("confirmations",0))>=10))'
$CLI listmasternodeconf 2>/dev/null | python3 -c 'import json,sys; from collections import Counter; r=json.load(sys.stdin); print("conf",Counter((x.get("status") or "?").upper() for x in r))'
head -2 /var/www/html/config/masternode.conf
E
"""

def main():
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, e = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    if e.read().strip():
        print("[stderr]", e.read())
    ssh.close()

if __name__ == "__main__":
    main()
