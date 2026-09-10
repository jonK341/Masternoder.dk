#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

TX = "41dee9badf4db13aef396f7ed44f91e3b72c2bfb4689ca3d27e99d6c6fd6bb3e"
REMOTE = f"""bash -s <<'E'
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
echo "== gettransaction {TX[:16]} =="
$CLI gettransaction {TX} 2>&1 | head -c 1200
echo ""
echo "== getrawmempool has tx =="
$CLI getrawmempool 2>/dev/null | python3 -c 'import json,sys; m=json.load(sys.stdin); print("{TX[:16]}" in m, "mempool_size", len(m))'
echo "== getblockchaininfo =="
$CLI getblockchaininfo 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("blocks",d.get("blocks"),"chain",d.get("chain"),"mediantime",d.get("mediantime"))'
echo "== sample utxo conf =="
$CLI listunspent 0 9999999 2>/dev/null | python3 -c 'import json,sys; u=json.load(sys.stdin); c=[x for x in u if abs(float(x.get("amount",0))-5000)<0.01]; print([(x.get("confirmations"), x.get("txid","")[:8]) for x in c[:5]])'
E
"""

def main():
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, _, _ = connect_deploy_ssh()
    _, o, _ = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    ssh.close()

if __name__ == "__main__":
    main()
