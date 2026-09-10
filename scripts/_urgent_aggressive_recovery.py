#!/usr/bin/env python3
"""Aggressive MN2 recovery: stop competitors, tune memory, restart daemon, verify APIs."""
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
echo "========== AGGRESSIVE RECOVERY $(date -u) =========="

echo "== stop all memory competitors =="
systemctl stop masternoder-profit-daemon.service 2>/dev/null || true
pkill -f 'exchange_master_daemon.py' 2>/dev/null || true
pkill -f 'all_profit_daemons.py' 2>/dev/null || true
pkill -f 'scripts/sync.js index' 2>/dev/null || true
systemctl stop masternoder2d 2>/dev/null || true
sleep 5
free -h | head -2

CONF=/var/www/html/config/masternoder2.conf
touch "$CONF"
for kv in "dbcache=32" "par=1" "maxconnections=8" "rpcworkqueue=32" "rpcthreads=2"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$CONF" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$CONF"
  else
    echo "$kv" >> "$CONF"
  fi
done
grep -E '^(dbcache|par|maxconnections|rpcworkqueue|rpcthreads|server|rpcport)=' "$CONF"

echo "== debug.log tail =="
tail -30 /var/www/html/config/debug.log 2>/dev/null

echo "== chain integrity =="
ls -lh /var/www/html/config/blocks/blk*.dat 2>/dev/null
du -sh /var/www/html/config/blocks /var/www/html/config/chainstate /var/www/html/config/indexes 2>/dev/null

echo "== start daemon (systemd) =="
systemctl start masternoder2d
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
OK=0
BC=""
for i in $(seq 1 30); do
  sleep 10
  ACTIVE=$(systemctl is-active masternoder2d)
  if [ "$ACTIVE" != "active" ]; then
    echo "poll $i: daemon $ACTIVE"
    journalctl -u masternoder2d --no-pager -n 2 2>/dev/null
    continue
  fi
  OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',''))" 2>/dev/null || echo "")
  echo "poll $i: active=$ACTIVE block=$BC rpc_out=${OUT:0:120}"
  if [ -n "$BC" ] && [ "$BC" != "-1" ] && [ "$BC" != "None" ] 2>/dev/null; then
    python3 -c "assert int('$BC') > 0" 2>/dev/null && OK=1 && break
  fi
done

echo "== checkout quote test (correct path) =="
curl -sS -m 20 -X POST http://127.0.0.1:5000/api/mn2/masternode/checkout/quote \
  -H 'content-type: application/json' \
  -d '{"slots":1,"payment_rail":"paypal","user_id":"recovery-test"}' 2>&1 | head -c 800
echo

echo "== recent paid/pending orders =="
python3 <<'PY'
import json, os
p = "/var/www/html/data/mn2_masternode_orders.json"
if os.path.isfile(p):
    d = json.load(open(p))
    items = d if isinstance(d, list) else list(d.values())
    recent = sorted(items, key=lambda x: x.get("created_at",""), reverse=True)[:10]
    for o in recent:
        print(o.get("order_id"), o.get("status"), o.get("created_at","")[:19], o.get("user_id","")[:20])
PY

echo "== restart profit daemon =="
systemctl start masternoder-profit-daemon.service 2>/dev/null || true
sleep 2
systemctl is-active masternoder-profit-daemon.service 2>/dev/null

echo "RPC_OK=$OK BLOCK=$BC"
ENDSCRIPT"""


def public_checks() -> None:
    print("\n=== PUBLIC VERIFICATION ===")
    checks = [
        ("explorer", "https://masternoder.dk/api/mn2/explorer/status"),
        ("payment", "https://masternoder.dk/api/shop/payment-health"),
        ("service", "https://masternoder.dk/api/mn2/masternode/service"),
    ]
    for name, url in checks:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AggressiveRecovery/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read().decode())
            if name == "explorer":
                rpc = (d.get("checks") or {}).get("rpc") or {}
                print(f"explorer: status={d.get('status')} rpc_ok={rpc.get('ok')} block={rpc.get('block_height')}")
            elif name == "payment":
                mn2 = d.get("mn2_daemon") or {}
                print(f"payment-health: mn2={mn2.get('status')} block={mn2.get('block_height')}")
            else:
                hs = d.get("hosting_stats") or {}
                print(f"masternode service: pending={hs.get('pending_orders')} paid={hs.get('paid_orders')}")
        except Exception as exc:
            print(f"{name}: FAIL {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=420)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    time.sleep(5)
    public_checks()
    return 0 if "RPC_OK=1" in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
