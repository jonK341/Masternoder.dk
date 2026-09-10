#!/usr/bin/env python3
"""Investigate and fix MN2 RPC / daemon issues on production."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html
CONF=$WEB/config/masternoder2.conf

echo "========== RPC / DAEMON INVESTIGATION =========="
echo "== process =="
ps aux | grep -E '[m]asternoder2d' | head -5
echo "== systemd =="
systemctl status masternoder2d --no-pager | head -20
echo "== journal tail =="
journalctl -u masternoder2d --no-pager -n 25 2>/dev/null
echo "== debug.log tail =="
tail -40 $WEB/config/debug.log 2>/dev/null
echo "== rpc config (no secrets) =="
grep -E '^(server|rpcport|rpcbind|rpcallowip|rpcuser|testnet|regtest)=' $CONF 2>/dev/null
echo "== .cookie =="
ls -la $WEB/config/.cookie 2>/dev/null
echo "== CLI direct =="
$CLI getblockcount 2>&1
echo "== curl RPC from .env creds =="
RPC_USER=$(grep '^MN2_RPC_USER=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PORT=$(grep '^rpcport=' $CONF | head -1 | cut -d= -f2-)
RPC_PORT=${RPC_PORT:-9332}
echo "rpcport=$RPC_PORT user=${RPC_USER:0:4}..."
OUT=$(curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
  "http://127.0.0.1:${RPC_PORT}/" 2>&1)
echo "$OUT" | head -c 600
echo ""
echo "== wallet rescan state =="
grep -iE 'rescan|import|Loading wallet|Reindexing|Activating best chain' $WEB/config/debug.log 2>/dev/null | tail -10
echo "== masternode.conf first 3 lines =="
head -3 $WEB/config/masternode.conf 2>/dev/null
echo "== compare masternode.conf tx to wallet =="
# sample first collateral from masternode.conf
SAMPLE=$(awk 'NF==5 && index($2,":")>0 {print $2; exit}' $WEB/config/masternode.conf)
echo "sample collateral ref: $SAMPLE"
if [ -n "$SAMPLE" ]; then
  TXID=$(echo "$SAMPLE" | cut -d: -f1)
  VOUT=$(echo "$SAMPLE" | cut -d: -f2)
  $CLI gettxout "$TXID" "$VOUT" 2>&1 | head -c 400
  echo ""
fi
ENDSCRIPT
"""


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + (("\n[stderr] " + err) if err.strip() else "")


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    print(sh(ssh, REMOTE))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
