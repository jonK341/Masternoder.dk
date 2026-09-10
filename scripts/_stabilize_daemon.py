#!/usr/bin/env python3
"""Ensure single stable masternoder2d instance and final verification."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo "========== STABILIZE DAEMON $(date -u) =========="

echo "== processes =="
pgrep -af masternoder2d || echo none

echo "== if reindex running, let it finish or hand off to systemd =="
REIDX=$(pgrep -f 'masternoder2d.*-reindex' || true)
if [ -n "$REIDX" ]; then
  echo "reindex pid=$REIDX still running — checking RPC"
  RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
  RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
  BC=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null)
  echo "reindex block=$BC"
  if [ -n "$BC" ] && [ "$BC" -gt 0 ] 2>/dev/null; then
    echo "RPC OK via reindex — stopping reindex and starting systemd"
    /opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config stop 2>/dev/null || kill -TERM $REIDX 2>/dev/null
    sleep 10
    pkill -9 masternoder2d 2>/dev/null || true
    sleep 2
    rm -f /var/www/html/config/.lock
  fi
fi

echo "== ensure systemd owns daemon =="
systemctl stop masternoder2d 2>/dev/null
sleep 3
pkill -9 masternoder2d 2>/dev/null || true
sleep 2
rm -f /var/www/html/config/.lock
systemctl start masternoder2d

RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
OK=0
for i in $(seq 1 12); do
  sleep 10
  ACTIVE=$(systemctl is-active masternoder2d)
  BC=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null)
  INFO=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockchaininfo","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; d=json.load(sys.stdin).get('result',{}); print(f\"blocks={d.get('blocks')} headers={d.get('headers')} progress={round(float(d.get('verificationprogress',0))*100,2)}\")" 2>/dev/null)
  echo "poll $i: active=$ACTIVE block=$BC $INFO"
  if [ "$ACTIVE" = "active" ] && [ -n "$BC" ] && [ "$BC" -gt 0 ] 2>/dev/null; then OK=1; break; fi
done

echo "== sync pct vs ~989k tip =="
if [ -n "$BC" ] && [ "$BC" -gt 0 ] 2>/dev/null; then
  python3 -c "bc=int('$BC'); tip=989000; print(f'approx_sync_pct={round(100*bc/tip,2)}%')"
fi

echo "== journal last 3 =="
journalctl -u masternoder2d --no-pager -n 3 2>/dev/null

echo "RPC_OK=$OK BLOCK=$BC"
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, _ = ssh.exec_command(REMOTE, timeout=180)
    sys.stdout.buffer.write(stdout.read())
    ssh.close()

    print("\n=== PUBLIC ENDPOINTS ===")
    chain_tip = 989000
    for name, url in (
        ("network-overview", "https://masternoder.dk/api/mn2/network-overview"),
        ("balance", "https://masternoder.dk/api/mn2/balance?user_id=default_user"),
        ("explorer/status", "https://masternoder.dk/api/mn2/explorer/status"),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Stabilize/1.0"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                d = json.loads(resp.read().decode())
            if name == "network-overview":
                bh = d.get("block_height")
                daemon = d.get("daemon") or {}
                pct = round(100 * (bh or 0) / chain_tip, 2) if bh else None
                print(f"{name}: reachable={daemon.get('reachable')} block={bh} headers={daemon.get('headers')} sync~{pct}%")
            elif name == "explorer/status":
                checks = d.get("checks") or {}
                rpc = checks.get("rpc") or {}
                print(f"{name}: rpc.ok={rpc.get('ok')} block={rpc.get('block_height')}")
            else:
                print(f"{name}: success={d.get('success')}")
        except Exception as exc:
            print(f"{name}: FAIL {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
