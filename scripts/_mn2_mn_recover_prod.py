#!/usr/bin/env python3
"""Recover MN2 daemon RPC + wallet loading on production."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html
CONF=$WEB/config/masternoder2.conf
BACKUP=$WEB/config/wallet.dat.bak.$(date +%Y%m%d_%H%M%S)

echo "========== MN2 WALLET / RPC RECOVERY =========="
echo "== current wallet load state =="
grep -i 'Loading wallet' $WEB/config/debug.log 2>/dev/null | tail -3
echo "== process CPU/mem =="
ps -p $(pgrep -f 'masternoder2d -datadir' | head -1) -o pid,pcpu,pmem,etime,cmd 2>/dev/null
echo "== backup wallet.dat =="
if [ -f $WEB/config/wallet.dat ] && [ ! -f "${BACKUP}" ]; then
  cp -a $WEB/config/wallet.dat "$BACKUP"
  echo "OK backed up to $BACKUP ($(stat -c%s "$BACKUP" 2>/dev/null) bytes)"
else
  echo "skip or exists"
fi

echo "== tune RPC queue =="
for kv in "rpcworkqueue=256" "rpcthreads=8" "dbcache=128"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else
    echo "$kv" >> "$CONF"
  fi
done
grep -E '^(rpcworkqueue|rpcthreads|dbcache)=' "$CONF"

echo "== clean stale lock if any =="
if [ -f $WEB/config/.lock ] && ! pgrep -f 'masternoder2d -datadir=/var/www/html/config' >/dev/null 2>&1; then
  echo "removing stale .lock"
  rm -f $WEB/config/.lock
else
  echo "lock ok or daemon running"
fi

echo "== restart daemon =="
systemctl restart masternoder2d
sleep 8

echo "== wait for RPC (up to 3 min) =="
RPC_USER=$(grep '^MN2_RPC_USER=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PORT=$(grep '^rpcport=' $CONF | head -1 | cut -d= -f2-)
RPC_PORT=${RPC_PORT:-9332}
OK=0
for i in $(seq 1 36); do
  OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    "http://127.0.0.1:${RPC_PORT}/" 2>&1)
  BC=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('result',''))" 2>/dev/null)
  if [ -n "$BC" ] && [ "$BC" != "None" ] 2>/dev/null; then
    echo "poll $i: blockcount=$BC"
    OK=1
    break
  fi
  WAL=$(grep -i 'Loading wallet' $WEB/config/debug.log 2>/dev/null | tail -1)
  echo "poll $i: rpc_not_ready (${OUT:0:60}) wallet_line=${WAL: -80}"
  sleep 5
done

if [ "$OK" != "1" ]; then
  echo "WARN: RPC still not ready after wait"
  tail -5 $WEB/config/debug.log
  exit 2
fi

echo "== post-recovery RPC checks =="
$CLI getwalletinfo 2>&1 | head -c 800
echo ""
$CLI getmasternodecount 2>&1
echo ""
$CLI listunspent 1 9999999 2>/dev/null | python3 -c "
import json,sys
try:
    utxos=json.load(sys.stdin)
except Exception as e:
    print('utxo parse fail', e); sys.exit(0)
coll=[u for u in utxos if abs(float(u.get('amount',0))-5000.0)<0.01]
print(f'total utxos={len(utxos)} collateral_5000={len(coll)}')
bal=sum(float(u.get('amount',0)) for u in utxos)
print(f'sum unspent={bal:.4f} MN2')
for u in coll[:5]:
    print(f\"  {u.get('txid')}:{u.get('vout')} {u.get('amount')}\")
"
echo ""
$CLI listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
from collections import Counter
try:
    rows=json.load(sys.stdin)
except Exception as e:
    print('conf parse fail', e); sys.exit(0)
c=Counter((r.get('status') or '?').upper() for r in rows)
print('listmasternodeconf:', dict(c), 'total', len(rows))
"
echo ""
# on-chain collateral check for first masternode.conf entry
SAMPLE=$(awk 'NF==5 {print $4":"$5; exit}' $WEB/config/masternode.conf)
echo "sample on-chain txout $SAMPLE:"
TXID=$(echo "$SAMPLE" | cut -d: -f1)
VOUT=$(echo "$SAMPLE" | cut -d: -f2)
$CLI gettxout "$TXID" "$VOUT" 2>&1 | head -c 400
echo ""
ENDSCRIPT
"""


def sh(ssh, cmd: str, timeout: int = 300) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + (("\n[stderr] " + err) if err.strip() else "")


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    out = sh(ssh, REMOTE, timeout=300)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(out)
    ssh.close()
    return 0 if "blockcount=" in out and "RPC still not ready" not in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
