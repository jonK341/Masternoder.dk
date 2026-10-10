#!/usr/bin/env python3
"""
Wait for MN2 chain tip, then mnsync-finish + startmasternode + DoD probe.

Usage:
  python scripts/mn2_watch_sync_then_enable_remote.py
  python scripts/mn2_watch_sync_then_enable_remote.py --tip 972000 --poll-sec 60
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

PEERS = (
    "192.46.237.230", "213.136.90.158", "85.10.148.5", "144.91.75.27",
    "34.42.67.197", "34.44.119.78", "34.172.145.22", "167.86.110.23",
)

REMOTE_TEMPLATE = r"""bash -s <<'ENDSCRIPT'
set +e
TIP=__TIP__
POLL=__POLL__
MAX_ROUNDS=__MAX_ROUNDS__
WEB=/var/www/html
D="-datadir=$WEB/config"
CLI=/opt/masternoder2d/masternoder2-cli
CONF=$WEB/config/masternoder2.conf
RPC_USER=$(grep '^MN2_RPC_USER=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
PEERS="__PEERS__"

log() { echo "[watch-enable] $*"; }
rpc() {
  curl -sS -m 12 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"1.0\",\"id\":\"t\",\"method\":\"$1\",\"params\":$2}" http://127.0.0.1:9332/
}

echo "========== WATCH SYNC THEN ENABLE $(date -u) tip=$TIP =========="
command -v pm2 >/dev/null && pm2 stop explorer 2>/dev/null || true

for i in $(seq 1 "$MAX_ROUNDS"); do
  BC=$($CLI $D getblockcount 2>/dev/null)
  HDR=$($CLI $D getblockchaininfo 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('headers',''))" 2>/dev/null)
  log "poll $i block=$BC headers=$HDR target=$TIP"
  if [ -n "$BC" ] && [ "$BC" -ge "$TIP" ] 2>/dev/null; then
    log "tip reached — starting enable pass"
    break
  fi
  sleep "$POLL"
done

BC=$($CLI $D getblockcount 2>/dev/null)
if [ -z "$BC" ] || [ "$BC" -lt "$TIP" ] 2>/dev/null; then
  log "WARN: tip not reached (block=$BC) — running enable pass anyway"
fi

for ip in $PEERS; do
  grep -q "^addnode=${ip}$" "$CONF" 2>/dev/null || echo "addnode=${ip}" >> "$CONF"
  rpc addnode "[\"$ip\", \"add\"]" >/dev/null 2>&1 || true
done
$CLI $D mnsync reset 2>/dev/null || true
sleep 2

for round in $(seq 1 24); do
  for ip in $PEERS; do rpc addnode "[\"$ip\", \"onetry\"]" >/dev/null 2>&1 || true; done
  sleep 10
  ST=$($CLI $D mnsync status 2>/dev/null)
  PARSED=$(echo "$ST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('RequestedMasternodeAssets'), d.get('countMasternodeList'))" 2>/dev/null)
  log "mnsync round $round $PARSED"
  ASSET=$(echo "$PARSED" | awk '{print $1}')
  MNCT=$(echo "$PARSED" | awk '{print $2}')
  [ "$ASSET" = "999" ] && break
  [ -n "$MNCT" ] && [ "$MNCT" -gt 0 ] 2>/dev/null && break
done

for step in $(seq 1 10); do $CLI $D mnsync next 2>/dev/null || true; sleep 2; done

if [ -f $WEB/scripts/mn2_fix_daemon_privkey.sh ]; then
  bash $WEB/scripts/mn2_fix_daemon_privkey.sh --primary=platformmn2 2>&1 | tail -3
fi
$CLI $D startmasternode local false 2>&1 | head -c 200; echo
$CLI $D startmasternode alias false platformmn2 2>&1 | head -c 200; echo

if [ -f $WEB/scripts/mn2_fleet_autostart.sh ]; then
  bash $WEB/scripts/mn2_fleet_autostart.sh 2>&1 | tail -15
fi

echo "== final =="
$CLI $D listmasternodes 2>/dev/null | python3 -c "
import sys,json
raw=sys.stdin.read().strip()
try: rows=json.loads(raw)
except: rows=[]
if isinstance(rows,int): print('ENABLED_count', rows); raise SystemExit()
if not isinstance(rows,list): rows=[rows] if rows else []
en=sum(1 for r in rows if isinstance(r,dict) and 'ENABLE' in str(r.get('status','')).upper())
a5=sum(1 for r in rows if isinstance(r,dict) and 'ENABLE' in str(r.get('status','')).upper() and int(r.get('activetime') or 0)>=5)
print('list_len', len(rows), 'ENABLED', en, 'ENABLED_act>=5', a5)
for r in rows[:5]:
    if isinstance(r,dict): print(' ', r.get('alias'), r.get('status'), r.get('activetime'))
"
curl -sS -m 15 -o /dev/null -w 'mn2_health %{http_code}\n' http://127.0.0.1:5000/api/mn2/health
command -v pm2 >/dev/null && pm2 start explorer 2>/dev/null || true
echo "========== WATCH DONE =========="
ENDSCRIPT"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tip", type=int, default=971500, help="Block height to treat as caught up")
    p.add_argument("--poll-sec", type=int, default=90)
    p.add_argument("--max-rounds", type=int, default=120, help="Max poll iterations (~3h at 90s)")
    args = p.parse_args()
    remote = (
        REMOTE_TEMPLATE.replace("__TIP__", str(args.tip))
        .replace("__POLL__", str(args.poll_sec))
        .replace("__MAX_ROUNDS__", str(args.max_rounds))
        .replace("__PEERS__", " ".join(PEERS))
    )
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth}) — watching up to {args.max_rounds * args.poll_sec // 60} min\n")
    timeout = args.max_rounds * args.poll_sec + 900
    _, stdout, stderr = ssh.exec_command(remote, timeout=timeout)
    out = (stdout.read() + stderr.read()).decode(errors="replace")
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    log_path = ROOT / "scripts" / "_tmp_watch_enable_out.txt"
    log_path.write_text(out, encoding="utf-8")
    print(f"\n(log: {log_path})")
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
