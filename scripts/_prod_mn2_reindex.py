#!/usr/bin/env python3
"""Phase 2: kill RPC competitors, single-instance -reindex, restore services."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo "========== MN2 REINDEX $(date -u) =========="

echo "== kill memory hogs =="
pkill -9 -f 'exchange_master_daemon.py' 2>/dev/null && echo killed exchange || true
pkill -9 -f 'exchange_master_tick.sh' 2>/dev/null || true
systemctl stop masternoder2d 2>/dev/null
sleep 3
pkill -9 masternoder2d 2>/dev/null && echo killed stray mn2 || true
sleep 2
rm -f /var/www/html/config/.lock
free -h | head -2

echo "== pause explorer RPC (pm2) =="
pm2 stop explorer 2>/dev/null || true
sleep 2

echo "== patch systemd timeouts =="
UNIT=/etc/systemd/system/masternoder2d.service
grep -q TimeoutStopSec "$UNIT" || sed -i '/^\[Service\]/a TimeoutStopSec=300\nTimeoutStartSec=600' "$UNIT"
systemctl daemon-reload

echo "== conf low-memory =="
CONF=/var/www/html/config/masternoder2.conf
for kv in "dbcache=32" "par=1" "maxconnections=8" "maxmempool=5" "rpcthreads=2" "rpcworkqueue=32"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else echo "$kv" >> "$CONF"; fi
done

echo "== start -reindex (single instance, foreground log) =="
LOG=/var/log/mn2-reindex.log
: > "$LOG"
nohup /opt/masternoder2d/masternoder2d -datadir=/var/www/html/config -reindex -printtoconsole >>"$LOG" 2>&1 &
RPID=$!
echo "reindex pid=$RPID"

RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
OK=0
for i in $(seq 1 60); do
  sleep 15
  if ! kill -0 $RPID 2>/dev/null; then
    echo "reindex exited at poll $i"
    tail -8 "$LOG"
    break
  fi
  OUT=$(curl -sS -m 5 -u "$RPC_USER:$RPC_PASS" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | grep -oP '"result":\K[0-9]+' || echo "")
  MEM=$(free -m | awk '/Mem:/ {print $3}')
  tail -1 "$LOG" 2>/dev/null | head -c 120
  echo ""
  echo "poll $i: block=$BC mem=${MEM}Mi active=$(pgrep -c masternoder2d)"
  if [ -n "$BC" ] && [ "$BC" -gt 100000 ] 2>/dev/null; then OK=1; echo "RPC stable at $BC"; break; fi
done

if [ "$OK" != "1" ]; then
  echo "reindex not complete — check log"
  tail -30 "$LOG"
fi

echo "== hand off to systemd =="
/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config stop 2>/dev/null || kill $RPID 2>/dev/null
sleep 10
pkill -9 masternoder2d 2>/dev/null || true
sleep 3
rm -f /var/www/html/config/.lock
systemctl start masternoder2d
sleep 20
for i in 1 2 3 4 5; do
  OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | grep -oP '"result":\K[0-9]+' || echo "")
  echo "systemd poll $i: active=$(systemctl is-active masternoder2d) block=$BC"
  [ -n "$BC" ] && [ "$BC" -gt 100000 ] 2>/dev/null && OK=1 && break
  sleep 15
done

echo "== restore explorer + profit =="
pm2 start explorer 2>/dev/null || pm2 restart explorer 2>/dev/null || true
systemctl start masternoder-profit-daemon.service 2>/dev/null || true

echo "== eiquidus unlock + sync =="
cd /var/www/explorer
rm -f tmp/index.pid tmp/sync_index.lock 2>/dev/null
if [ "$OK" = "1" ]; then
  nohup node scripts/sync.js index update >>/var/log/eiquidus-index-sync.log 2>&1 &
fi

echo "== final probes =="
curl -sS -m 15 http://127.0.0.1:5000/api/mn2/explorer/status 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);c=d.get('checks',{});print('rpc.ok',c.get('rpc',{}).get('ok'),'block',c.get('rpc',{}).get('block_height'));print('rich',c.get('rich_list',{}))" 2>/dev/null
echo "RPC_OK=$OK"
ENDSCRIPT"""


def public_check() -> None:
    time.sleep(20)
    url = "https://masternoder.dk/api/mn2/explorer/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mn2Reindex/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read().decode())
        rpc = d.get("checks", {}).get("rpc", {})
        rl = d.get("checks", {}).get("rich_list", {})
        print(f"\nPUBLIC {url}")
        print(f"  status={d.get('status')} rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
        print(f"  rich_list ok={rl.get('ok')} synced={rl.get('index_synced')} note={rl.get('note','')[:80]}")
    except Exception as exc:
        print(f"PUBLIC check: {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=1200)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    public_check()
    return 0 if "RPC_OK=1" in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
