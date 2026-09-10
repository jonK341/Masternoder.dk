#!/usr/bin/env python3
"""Quick MN2 status check on production."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

CMD = r"""bash -lc '
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html
echo "== daemon =="; systemctl is-active masternoder2d
echo "== wallet load tail =="; grep -i "Loading wallet" $WEB/config/debug.log 2>/dev/null | tail -2
echo "== debug tail =="; tail -8 $WEB/config/debug.log 2>/dev/null
echo "== rpc curl ==";
U=$(grep ^MN2_RPC_USER= $WEB/.env|cut -d= -f2-|tr -d "\r\"")
P=$(grep ^MN2_RPC_PASSWORD= $WEB/.env|cut -d= -f2-|tr -d "\r\"")
curl -sS -m 8 -u "$U:$P" -H "content-type: application/json" -d "{\"jsonrpc\":\"1.0\",\"id\":\"t\",\"method\":\"getblockcount\",\"params\":[]}" http://127.0.0.1:9332/
echo ""
echo "== cli blockcount =="; $CLI getblockcount 2>&1
echo "== walletinfo =="; $CLI getwalletinfo 2>&1 | head -c 500
echo ""
echo "== masternodecount =="; $CLI getmasternodecount 2>&1
echo "== collateral 5000 utxos =="
$CLI listunspent 1 9999999 2>/dev/null | python3 -c 'import json,sys; u=json.load(sys.stdin); c=[x for x in u if abs(float(x.get("amount",0))-5000)<0.01]; print(len(c),"x5000", sum(1 for x in c if int(x.get("confirmations",0))>=10),"confirmed_ge_10", max((int(x.get("confirmations",0)) for x in c), default=0))'
echo "== backup files =="; ls -la $WEB/config/wallet.dat.bak.* 2>/dev/null | tail -3
'
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, stdout, stderr = ssh.exec_command(CMD, timeout=60)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(stdout.read().decode(errors="replace"))
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
