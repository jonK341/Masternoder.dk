#!/usr/bin/env python3
"""Force clean MN2 daemon restart with low-memory config and full verification."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo "========== FORCE CLEAN RESTART $(date -u) =========="

echo "== force stop all mn2 =="
systemctl stop masternoder2d 2>/dev/null
sleep 3
pkill -9 masternoder2d 2>/dev/null && echo killed || echo none
pkill -9 -f 'bitcoin-http' 2>/dev/null || true
sleep 2
rm -f /var/www/html/config/.lock
pgrep -a masternoder2d || echo "no mn2 processes"

echo "== stop RPC consumers =="
pm2 stop explorer 2>/dev/null || true
systemctl stop masternoder-profit-daemon.service 2>/dev/null || true
pkill -f 'scripts/sync.js index' 2>/dev/null || true
sleep 2
free -h | head -2

echo "== low-memory config =="
CONF=/var/www/html/config/masternoder2.conf
for kv in "dbcache=32" "par=1" "maxconnections=8" "maxmempool=5" "rpcthreads=2" "rpcworkqueue=32"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else echo "$kv" >> "$CONF"; fi
done
grep -E '^(dbcache|par|maxconnections|maxmempool|rpcworkqueue|rpcthreads|server|rpcport|txindex)=' "$CONF"

echo "== systemd timeout patch =="
UNIT=/etc/systemd/system/masternoder2d.service
if ! grep -q TimeoutStopSec "$UNIT" 2>/dev/null; then
  sed -i '/^\[Service\]/a TimeoutStopSec=300\nTimeoutStartSec=600' "$UNIT"
  systemctl daemon-reload
fi

echo "== debug.log tail =="
tail -15 /var/www/html/config/debug.log 2>/dev/null

echo "== start masternoder2d =="
systemctl start masternoder2d
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')

echo "== wait for block index load =="
OK=0
BC=-1
for i in $(seq 1 36); do
  sleep 10
  ACTIVE=$(systemctl is-active masternoder2d)
  MEM=$(free -m | awk '/Mem:/ {print $3}')
  LOGTAIL=$(tail -1 /var/www/html/config/debug.log 2>/dev/null | head -c 100)
  echo "wait $i active=$ACTIVE mem=${MEM}Mi log=$LOGTAIL"
  if [ "$ACTIVE" != "active" ]; then
    journalctl -u masternoder2d --no-pager -n 3 2>/dev/null
    continue
  fi
  if [ "$i" -ge 6 ]; then
    OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" \
      -H 'content-type: application/json' \
      -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
      http://127.0.0.1:9332/ 2>&1)
    BC=$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',''))" 2>/dev/null || echo "")
    echo "  rpc block=$BC"
    if [ -n "$BC" ] && [ "$BC" != "-1" ] && [ "$BC" != "None" ] 2>/dev/null; then
      python3 -c "assert int('$BC') >= 0" 2>/dev/null && OK=1 && break
    fi
  fi
done

echo "== RPC probes =="
if [ "$OK" = "1" ]; then
  for method in getblockcount getwalletinfo getnetworkinfo; do
    curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
      -d "{\"jsonrpc\":\"1.0\",\"id\":\"t\",\"method\":\"$method\",\"params\":[]}" \
      http://127.0.0.1:9332/ | head -c 300; echo
  done
fi

echo "== sync progress =="
TIP=$(curl -sS -m 8 http://127.0.0.1:3000/ext/getblockcount 2>/dev/null || echo "")
echo "eiquidus tip=$TIP local=$BC"
if [ -n "$BC" ] && [ "$BC" != "-1" ] && [ -n "$TIP" ] && [ "$TIP" -gt 0 ] 2>/dev/null; then
  python3 -c "bc=int('$BC'); tip=int('$TIP'); pct=round(100*bc/tip,2) if tip else 0; print(f'sync_pct={pct}%')"
fi

echo "== restart uwsgi =="
systemctl restart uwsgi-vidgenerator 2>/dev/null || systemctl restart uwsgi 2>/dev/null || true
sleep 5
systemctl is-active uwsgi-vidgenerator 2>/dev/null || systemctl is-active uwsgi 2>/dev/null

echo "== restart pm2 explorer =="
pm2 start explorer 2>/dev/null || pm2 restart explorer 2>/dev/null || true
sleep 3

echo "== local API probes =="
curl -sS -m 15 http://127.0.0.1:5000/api/mn2/explorer/status 2>/dev/null | head -c 600; echo
curl -sS -m 15 'http://127.0.0.1:5000/api/mn2/balance?user_id=default_user' 2>/dev/null | head -c 400; echo
curl -sS -m 15 http://127.0.0.1:5000/api/mn2/network-overview 2>/dev/null | head -c 500; echo

echo "== eiquidus unlock + nudge =="
cd /var/www/explorer 2>/dev/null
rm -f tmp/index.pid tmp/sync_index.lock 2>/dev/null
if [ "$OK" = "1" ] && ! pgrep -f 'scripts/sync.js index update' >/dev/null 2>&1; then
  nohup node scripts/sync.js index update >>/var/log/eiquidus-index-sync.log 2>&1 &
  echo "eiquidus sync pid=$!"
fi

echo "== profit daemon =="
systemctl start masternoder-profit-daemon.service 2>/dev/null || true

echo "RPC_OK=$OK BLOCK=$BC"
ENDSCRIPT"""


def public_checks() -> None:
    print("\n=== PUBLIC VERIFICATION ===")
    urls = [
        ("explorer/status", "https://masternoder.dk/api/mn2/explorer/status"),
        ("balance", "https://masternoder.dk/api/mn2/balance?user_id=default_user"),
        ("network-overview", "https://masternoder.dk/api/mn2/network-overview"),
    ]
    for name, url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ForceRestart/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read().decode("utf-8", errors="replace"))
            print(f"\n{name}:")
            if name == "explorer/status":
                rpc = (d.get("checks") or d.get("rpc") or {})
                if isinstance(rpc, dict) and "ok" in rpc:
                    print(f"  rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
                else:
                    checks = d.get("checks") or {}
                    rpc = checks.get("rpc") or {}
                    print(f"  status={d.get('status')} rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
            elif name == "network-overview":
                daemon = d.get("daemon") or {}
                print(f"  daemon.reachable={daemon.get('reachable')} block={daemon.get('block_height')}")
            else:
                print(f"  keys={list(d.keys())[:6]} success={d.get('success')}")
        except Exception as exc:
            print(f"{name}: FAIL {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=480)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        sys.stdout.buffer.write(b"\nSTDERR: ")
        sys.stdout.buffer.write(err[:500].encode("utf-8", errors="replace"))

    print("\nWaiting 20s for uwsgi...")
    time.sleep(20)
    public_checks()
    ok = "RPC_OK=1" in out
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
