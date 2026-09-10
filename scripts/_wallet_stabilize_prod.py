#!/usr/bin/env python3
"""Stabilize masternoder2d on production and refill deposit address pool."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== STOP MEMORY HOGS =='
pkill -9 -f 'exchange_master_daemon.py' 2>/dev/null || true
systemctl stop masternoder2d 2>/dev/null
sleep 2
pkill -9 masternoder2d 2>/dev/null || true
rm -f /var/www/html/config/.lock
sleep 2

echo '== LOW-MEM CONF =='
CONF=/var/www/html/config/masternoder2.conf
for kv in "dbcache=32" "par=1" "maxconnections=8" "maxmempool=5" "rpcthreads=2" "rpcworkqueue=32"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else echo "$kv" >> "$CONF"; fi
done

echo '== START DAEMON =='
systemctl start masternoder2d
sleep 25

RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
OK=0
for i in 1 2 3 4 5 6 7 8; do
  echo "poll $i active=$(systemctl is-active masternoder2d)"
  OUT=$(curl -sS -m 6 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getwalletinfo","params":[]}' http://127.0.0.1:9332/ 2>&1)
  echo "getwalletinfo: ${OUT:0:200}"
  if echo "$OUT" | grep -q '"result"'; then
    if echo "$OUT" | grep -q '"error"'; then
      sleep 15
      continue
    fi
    OK=1
    break
  fi
  sleep 15
done

echo '== GETNEWADDRESS TEST =='
curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getnewaddress","params":[]}' http://127.0.0.1:9332/ 2>&1
echo

if [ "$OK" = "1" ]; then
  echo '== CREATE POOL ADDRESSES =='
  OPS=$(grep '^MN2_OPS_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
  if [ -n "$OPS" ]; then
    curl -sS -m 30 "http://127.0.0.1:5000/api/mn2/ops/create-addresses?count=10&token=$OPS" | head -c 800
    echo
  else
    echo 'skip pool (no MN2_OPS_SECRET)'
  fi
fi

echo '== DEPOSIT API EXISTING USER =='
curl -sS -m 12 'http://127.0.0.1:5000/api/mn2/deposit-address?user_id=user_jon_ulrik' | head -c 400
echo
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=600)
    sys.stdout.buffer.write((stdout.read() or b"").decode("utf-8", errors="replace").encode("utf-8", errors="replace"))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
