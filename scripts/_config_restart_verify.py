#!/usr/bin/env python3
"""Merge upgraded MN2 config, restart daemon + services, verify RPC/APIs."""
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
echo "========== CONFIG MERGE + RESTART $(date -u) =========="

LIVE=/var/www/html/config/masternoder2.conf
EXAMPLE=/var/www/html/config/masternoder2.conf.example
UNIT_EX=/var/www/html/systemd/masternoder2d.service.example
UNIT=/etc/systemd/system/masternoder2d.service

echo "== merge example settings into live conf (preserve secrets) =="
touch "$LIVE"
# Low-memory + RPC tuning keys from upgraded example
for kv in \
  "dbcache=32" "par=1" "maxconnections=8" "maxmempool=5" \
  "rpcworkqueue=32" "rpcthreads=2" \
  "listen=1" "port=17646" "dns=1" "dnsseed=1" "discover=1"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$LIVE" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$LIVE"
  else
    echo "$kv" >> "$LIVE"
  fi
done
# addnode lines from example (skip duplicates)
if [ -f "$EXAMPLE" ]; then
  grep '^addnode=' "$EXAMPLE" | while read -r line; do
    grep -qxF "$line" "$LIVE" 2>/dev/null || echo "$line" >> "$LIVE"
  done
fi
chown root:www-data "$LIVE" && chmod 640 "$LIVE"
echo "--- live conf (non-secret keys) ---"
grep -E '^(server|rpcport|dbcache|par|maxconnections|maxmempool|rpcworkqueue|rpcthreads|listen|port|dns|dnsseed|discover|masternode|externalip|addnode)=' "$LIVE" | head -30

echo "== systemd unit timeouts =="
if [ -f "$UNIT_EX" ] && ! grep -q TimeoutStopSec "$UNIT" 2>/dev/null; then
  cp "$UNIT_EX" "$UNIT"
  systemctl daemon-reload
  echo "installed unit from example"
elif grep -q TimeoutStopSec "$UNIT" 2>/dev/null; then
  echo "timeouts already set"
else
  sed -i '/^\[Service\]/a TimeoutStopSec=300\nTimeoutStartSec=600' "$UNIT"
  systemctl daemon-reload
  echo "patched existing unit"
fi

echo "== stop RPC consumers =="
pm2 stop explorer 2>/dev/null || true
systemctl stop masternoder-profit-daemon.service 2>/dev/null || true
pkill -f 'scripts/sync.js index' 2>/dev/null || true

echo "== clean stop masternoder2d =="
systemctl stop masternoder2d 2>/dev/null
sleep 5
pkill -9 masternoder2d 2>/dev/null || true
pkill -9 -f 'bitcoin-http' 2>/dev/null || true
sleep 2
rm -f /var/www/html/config/.lock
pgrep -a masternoder2d || echo "no mn2 processes"
free -h | head -2

echo "== start masternoder2d =="
systemctl start masternoder2d
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')

OK=0
BC=""
for i in $(seq 1 18); do
  sleep 10
  ACTIVE=$(systemctl is-active masternoder2d)
  if [ "$ACTIVE" != "active" ]; then
    echo "poll $i: active=$ACTIVE"
    journalctl -u masternoder2d --no-pager -n 2 2>/dev/null
    continue
  fi
  if [ "$i" -lt 4 ]; then
    echo "poll $i: active=$ACTIVE (waiting for index load)"
    continue
  fi
  OUT=$(curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1)
  BC=$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null || echo "")
  echo "poll $i: active=$ACTIVE block=$BC"
  if [ -n "$BC" ] && [ "$BC" != "-1" ] && [ "$BC" != "None" ] 2>/dev/null; then
    python3 -c "assert int('$BC') >= 0" 2>/dev/null && OK=1 && break
  fi
done

echo "== RPC detail =="
if [ "$OK" = "1" ]; then
  curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getwalletinfo","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; w=json.load(sys.stdin).get('result',{}); print('balance',w.get('balance'),'txcount',w.get('txcount'))"
  curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getblockchaininfo","params":[]}' \
    http://127.0.0.1:9332/ | python3 -c "import sys,json; d=json.load(sys.stdin).get('result',{}); print('blocks',d.get('blocks'),'headers',d.get('headers'),'progress',round(float(d.get('verificationprogress',0))*100,2),'connections',d.get('connections'))"
  curl -sS -m 10 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"mnsync","params":["status"]}' \
    http://127.0.0.1:9332/ 2>/dev/null | head -c 200; echo
fi

echo "== restart uwsgi + profit + eiquidus =="
systemctl restart uwsgi-vidgenerator 2>/dev/null || systemctl restart uwsgi 2>/dev/null || true
sleep 4
systemctl start masternoder-profit-daemon.service 2>/dev/null || true
pm2 restart explorer 2>/dev/null || pm2 start explorer 2>/dev/null || true
sleep 3
systemctl is-active uwsgi-vidgenerator masternoder-profit-daemon.service masternoder2d 2>/dev/null

echo "== local API =="
curl -sS -m 15 'http://127.0.0.1:5000/api/mn2/balance?user_id=default_user' 2>/dev/null | head -c 300; echo
curl -sS -m 15 http://127.0.0.1:5000/api/mn2/network-overview 2>/dev/null | head -c 400; echo

echo "== debug tail =="
tail -3 /var/www/html/config/debug.log 2>/dev/null

if [ -n "$BC" ] && [ "$BC" -gt 0 ] 2>/dev/null; then
  python3 -c "bc=int('$BC'); tip=989000; print(f'approx_sync_pct={round(100*bc/tip,2)}%')"
fi

echo "RPC_OK=$OK BLOCK=$BC"
ENDSCRIPT"""


def public_checks() -> None:
    print("\n=== PUBLIC VERIFICATION ===")
    chain_tip = 989000
    for name, url in (
        ("balance", "https://masternoder.dk/api/mn2/balance?user_id=default_user"),
        ("network-overview", "https://masternoder.dk/api/mn2/network-overview"),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ConfigRestart/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read().decode())
            if name == "network-overview":
                bh = d.get("block_height")
                daemon = d.get("daemon") or {}
                pct = round(100 * (bh or 0) / chain_tip, 2) if bh else None
                print(
                    f"{name}: reachable={daemon.get('reachable')} block={bh} "
                    f"headers={daemon.get('headers')} connections={daemon.get('connections')} sync~{pct}%"
                )
            else:
                print(f"{name}: success={d.get('success')} mn2_balance={d.get('mn2_balance')}")
        except Exception as exc:
            print(f"{name}: FAIL {exc}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=360)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        sys.stdout.buffer.write(b"\nSTDERR: ")
        sys.stdout.buffer.write(err[:500].encode("utf-8", errors="replace"))

    print("\nWaiting 15s for uwsgi...")
    time.sleep(15)
    public_checks()
    return 0 if "RPC_OK=1" in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
