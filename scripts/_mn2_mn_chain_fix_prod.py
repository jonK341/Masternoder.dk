#!/usr/bin/bin/env python3
"""Fix MN2 chain read errors and restore RPC on production."""
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

echo "========== CHAIN / BLOCK FILE DIAGNOSTICS =========="
echo "== disk usage =="
du -sh $WEB/config/blocks $WEB/config/chainstate $WEB/config/indexes 2>/dev/null
echo "== blk files =="
ls -la $WEB/config/blocks/blk*.dat 2>/dev/null | tail -8
echo "== rev files =="
ls -la $WEB/config/blocks/rev*.dat 2>/dev/null | tail -4
echo "== OpenBlockFile errors =="
grep -i 'OpenBlockFile\|SEGV\|Corrupt\|CDB' $WEB/config/debug.log 2>/dev/null | tail -15
echo "== dmesg segfault =="
dmesg -T 2>/dev/null | grep -iE 'masternoder2|segfault' | tail -5

echo "== stop daemon =="
systemctl stop masternoder2d
sleep 5
pkill -9 -f 'masternoder2d -datadir=/var/www/html/config' 2>/dev/null || true
sleep 2
rm -f $WEB/config/.lock 2>/dev/null

echo "== try reindex-chainstate (one-shot) =="
/opt/masternoder2d/masternoder2d -datadir=$WEB/config -reindex-chainstate -daemon=1 2>&1 | head -3
REPID=$(pgrep -f 'masternoder2d -datadir=/var/www/html/config -reindex-chainstate' | head -1)
echo "reindex pid=$REPID"
for i in $(seq 1 60); do
  sleep 10
  if ! kill -0 $REPID 2>/dev/null; then
    echo "reindex process exited at loop $i"
    grep -iE 'OpenBlockFile|done loading|init message|Shutdown' $WEB/config/debug.log 2>/dev/null | tail -5
    break
  fi
  BC=$(curl -sS -m 5 -u "$(grep ^MN2_RPC_USER= $WEB/.env|cut -d= -f2-|tr -d '\r"')":"$(grep ^MN2_RPC_PASSWORD= $WEB/.env|cut -d= -f2-|tr -d '\r"')" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('result',''))" 2>/dev/null)
  echo "reindex wait $i: blockcount=$BC"
  if [ -n "$BC" ] && [ "$BC" -gt 1000 ] 2>/dev/null; then
    echo "chain RPC ready"
    break
  fi
done

echo "== stop reindex daemon, start systemd =="
$CLI stop 2>/dev/null || true
sleep 8
pkill -9 -f 'masternoder2d -datadir=/var/www/html/config' 2>/dev/null || true
sleep 2
rm -f $WEB/config/.lock 2>/dev/null
systemctl start masternoder2d
sleep 10

echo "== wait RPC after systemd start =="
U=$(grep ^MN2_RPC_USER= $WEB/.env|cut -d= -f2-|tr -d '\r"')
P=$(grep ^MN2_RPC_PASSWORD= $WEB/.env|cut -d= -f2-|tr -d '\r"')
for i in $(seq 1 30); do
  OUT=$(curl -sS -m 8 -u "$U:$P" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result'); print(r if r not in (None,'') else '')" 2>/dev/null)
  if [ -n "$BC" ] && [ "$BC" != "-1" ] 2>/dev/null; then
    echo "poll $i: blockcount=$BC OK"
    break
  fi
  echo "poll $i: waiting ($OUT)"
  sleep 5
done

echo "== final checks =="
$CLI getblockchaininfo 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('blocks',d.get('blocks'),'vprog',d.get('verificationprogress'))" 2>/dev/null
$CLI getwalletinfo 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('balance',d.get('balance'),'tx',d.get('txcount'))" 2>/dev/null || $CLI getwalletinfo 2>&1 | head -c 300
echo ""
grep -i 'Loading wallet' $WEB/config/debug.log 2>/dev/null | tail -2
ENDSCRIPT
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=720)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(stdout.read().decode(errors="replace"))
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
