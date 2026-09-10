#!/usr/bin/env python3
"""Production MN2 daemon recovery: memory tuning, cron cleanup, safe restart, explorer sync."""
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
OUT=/tmp/mn2_recovery_$(date +%s).log
exec > >(tee "$OUT") 2>&1

echo "========== MN2 PRODUCTION RECOVERY $(date -u) =========="

echo "== memory / load =="
uptime
free -h
echo "top memory:"
ps aux --sort=-%mem | head -12

echo "== OOM / segfault dmesg =="
dmesg -T 2>/dev/null | grep -iE 'oom|killed process|segfault|masternoder2' | tail -12

echo "== blocks / chainstate =="
du -sh /var/www/html/config/blocks /var/www/html/config/chainstate /var/www/html/config/indexes 2>/dev/null
ls -la /var/www/html/config/blocks/ 2>/dev/null | tail -8
echo "blk count: $(ls /var/www/html/config/blocks/blk*.dat 2>/dev/null | wc -l)"

echo "== config tuning (no secrets) =="
CONF=/var/www/html/config/masternoder2.conf
touch "$CONF"
for kv in "dbcache=64" "par=1" "maxconnections=16" "rpcworkqueue=64" "rpcthreads=4"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else
    echo "$kv" >> "$CONF"
  fi
done
grep -E '^(dbcache|par|maxconnections|rpcworkqueue|rpcthreads|txindex|server|rpcport)=' "$CONF"

echo "== stop memory competitors (safe) =="
systemctl stop masternoder-profit-daemon.service 2>/dev/null || true
pkill -f 'exchange_master_daemon.py' 2>/dev/null || true
pkill -f 'scripts/sync.js index update' 2>/dev/null || true
sleep 2
free -h | head -2

echo "== exchange cron dedupe check =="
echo "--- /etc/cron.d ---"
grep -l exchange_master /etc/cron.d/* 2>/dev/null | while read f; do echo "$f:"; cat "$f"; done
DUP=$(grep -rl exchange_master /etc/cron.d/ 2>/dev/null | wc -l)
if [ "$DUP" -gt 1 ]; then
  echo "WARN: multiple exchange cron files — keeping masternoder-exchange-master only"
  for f in /etc/cron.d/*exchange*; do
    [ "$f" = "/etc/cron.d/masternoder-exchange-master" ] && continue
    [ -f "$f" ] && mv "$f" "${f}.disabled.$(date +%Y%m%d)" && echo "disabled $f"
  done
fi
echo "--- root crontab exchange lines ---"
crontab -l 2>/dev/null | grep exchange || echo "(none in root crontab)"

echo "== profit daemon =="
systemctl is-enabled masternoder-profit-daemon.service 2>/dev/null
systemctl is-active masternoder-profit-daemon.service 2>/dev/null
HB=/var/www/html/logs/profit_daemon_heartbeat.json
if [ -f "$HB" ]; then
  echo "heartbeat mtime: $(stat -c %y "$HB" 2>/dev/null)"
  head -c 200 "$HB"; echo
fi

echo "== restart masternoder2d (clean) =="
systemctl stop masternoder2d
sleep 5
# If still crash-looping on block load, try chainstate reindex once
if journalctl -u masternoder2d --no-pager -n 5 2>/dev/null | grep -q 'SEGV\|OpenBlockFile'; then
  echo "prior SEGV/OpenBlockFile — starting with -reindex-chainstate (one-shot)"
  systemctl stop masternoder2d
  sleep 3
  /opt/masternoder2d/masternoder2d -datadir=/var/www/html/config -reindex-chainstate -daemon=1 2>&1 | head -5 &
  REPID=$!
  echo "reindex-chainstate pid=$REPID"
  for i in $(seq 1 24); do
    sleep 10
    BC=$(/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getblockcount 2>/dev/null)
    echo "wait $i: blockcount=$BC mem=$(free -m | awk '/Mem:/ {print $3}')Mi"
    [ -n "$BC" ] && [ "$BC" != "-1" ] && break
    if ! kill -0 $REPID 2>/dev/null; then
      echo "reindex process exited early"
      break
    fi
  done
  /opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config stop 2>/dev/null || true
  sleep 8
fi
systemctl start masternoder2d
echo "waiting for RPC..."
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
OK=0
for i in $(seq 1 18); do
  sleep 10
  ACTIVE=$(systemctl is-active masternoder2d)
  OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | grep -oP '"result":\K[0-9]+' || echo "")
  echo "poll $i active=$ACTIVE block=$BC"
  if [ "$ACTIVE" != "active" ]; then
    journalctl -u masternoder2d --no-pager -n 3 2>/dev/null
  fi
  if [ -n "$BC" ] && [ "$BC" -gt 0 ] 2>/dev/null; then OK=1; break; fi
done

echo "== post-restart status =="
systemctl is-active masternoder2d
journalctl -u masternoder2d --no-pager -n 8 2>/dev/null
tail -5 /var/www/html/config/debug.log 2>/dev/null

echo "== enable/start profit daemon =="
systemctl enable masternoder-profit-daemon.service 2>/dev/null || true
systemctl start masternoder-profit-daemon.service 2>/dev/null || true
sleep 3
systemctl is-active masternoder-profit-daemon.service 2>/dev/null

echo "== eiquidus sync unlock =="
cd /var/www/explorer 2>/dev/null || true
pkill -f 'sync.js index check' 2>/dev/null || true
rm -f tmp/index.pid tmp/sync_index.lock 2>/dev/null
if [ "$OK" = "1" ]; then
  if ! pgrep -f 'scripts/sync.js index update' >/dev/null 2>&1; then
    nohup node scripts/sync.js index update >>/var/log/eiquidus-index-sync.log 2>&1 &
    echo "eiquidus index sync started pid=$!"
  fi
fi

echo "== explorer probes =="
curl -sS -m 12 http://127.0.0.1:5000/api/mn2/explorer/status 2>/dev/null | head -c 1200; echo
curl -sS -m 12 http://127.0.0.1:3000/ext/getrichlist?page=0 2>/dev/null | head -c 200; echo

echo "== recovery log: $OUT =="
echo "RPC_OK=$OK"
ENDSCRIPT"""


def public_status() -> None:
    print("\n=== Public verification ===")
    for url in (
        "https://masternoder.dk/api/mn2/explorer/status",
        "https://masternoder.dk/api/mn2/health",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mn2Recovery/1.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                d = json.loads(resp.read().decode("utf-8", errors="replace"))
            print(f"\n{url}")
            if "rpc" in d:
                rpc = d.get("rpc") or {}
                print(f"  rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
            if "components" in d:
                probe = (d.get("components") or {}).get("explorer_probe") or {}
                rl = ((probe.get("detail") or {}).get("checks") or {}).get("rich_list") or {}
                print(f"  explorer={probe.get('status')} rich_list.ok={rl.get('ok')}")
            else:
                print(f"  keys: {list(d.keys())[:8]}")
        except Exception as exc:
            print(f"{url}: FAIL {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=600)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        sys.stdout.buffer.write(b"\nSTDERR: ")
        sys.stdout.buffer.write(err[:500].encode("utf-8", errors="replace"))

    print("\nWaiting 30s for eiquidus sync...")
    time.sleep(30)
    public_status()
    ok = "RPC_OK=1" in out or '"result":' in out
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
