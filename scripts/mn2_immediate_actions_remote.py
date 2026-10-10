#!/usr/bin/env python3
"""
MN2 immediate next actions + definition-of-done probe (ops).

Runs on production via SSH (same creds as deploy.py):
  python scripts/mn2_immediate_actions_remote.py
  python scripts/mn2_immediate_actions_remote.py --no-mnsync   # skip 12-round peer finish

Actions:
  1. Confirm no live -reindex (leave nohup -reindex alone if present)
  2. Set ops.multi_ping_enabled false (v1.2.3 binary)
  3. Free RAM + ensure RAM_RESIZE_TICKET.md on server
  4. Debug empty listmasternodes (peers + mnsync-finish style loop)
  5. Print DoD probe (systemd, /api/mn2/health, MN list, payment-health, RAM)
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
WEB=/var/www/html
D="-datadir=$WEB/config"
CLI=/opt/masternoder2d/masternoder2-cli
CONF=$WEB/config/masternoder2.conf
RPC_USER=$(grep '^MN2_RPC_USER=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' $WEB/.env | cut -d= -f2- | tr -d '\r"')
PEERS="__PEERS__"
DO_MNSYNC="__DO_MNSYNC__"

log() { echo "[immediate] $*"; }
rpc() {
  curl -sS -m 12 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"1.0\",\"id\":\"t\",\"method\":\"$1\",\"params\":$2}" http://127.0.0.1:9332/
}

echo "========== IMMEDIATE ACTIONS $(date -u) =========="

echo "== 1) No nohup -reindex; systemd only =="
REIDX=$(pgrep -af 'masternoder2d.*-reindex' | grep -v bash || true)
if [ -n "$REIDX" ]; then
  log "WARN: -reindex process present — leave alone until soft-stop trial"
  echo "$REIDX"
else
  log "OK: no -reindex daemon process"
fi
UNIT=$(systemctl is-active masternoder2d 2>/dev/null || echo unknown)
PROC=$(pgrep -af '/opt/masternoder2d/masternoder2d' | grep -v bash | head -2)
log "systemd=$UNIT"
echo "$PROC"
echo "$PROC" | grep -q '\-reindex' && log "FAIL: live cmdline has -reindex" || log "OK: no -reindex in cmdline"

echo "== 2) multi_ping_enabled false =="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/var/www/html/data/mn2_masternode_config.json")
d = json.loads(p.read_text(encoding="utf-8"))
ops = d.setdefault("ops", {})
before = ops.get("multi_ping_enabled")
ops["multi_ping_enabled"] = False
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
print("multi_ping_enabled", before, "->", False)
PY

echo "== 3) Free RAM + resize ticket =="
AVAIL_MB=$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
log "MemAvailable=${AVAIL_MB}MiB (DoD target >500)"
free -h | head -2
if [ "$AVAIL_MB" -lt 500 ] 2>/dev/null; then
  command -v pm2 >/dev/null && pm2 stop explorer 2>/dev/null || true
  sleep 3
  AVAIL_MB=$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
  log "After explorer pause: ${AVAIL_MB}MiB"
fi
test -f $WEB/docs/ops/RAM_RESIZE_TICKET.md && log "RAM ticket present" || log "WARN: RAM ticket missing"

if [ "$DO_MNSYNC" = "1" ]; then
  echo "== 4) Debug listmasternodes =="
  BC=$($CLI $D getblockcount 2>/dev/null)
  log "block=$BC"
  for ip in $PEERS; do
    grep -q "^addnode=${ip}$" "$CONF" 2>/dev/null || echo "addnode=${ip}" >> "$CONF"
    rpc addnode "[\"$ip\", \"add\"]" >/dev/null 2>&1 || true
  done
  $CLI $D mnsync reset 2>/dev/null || rpc mnsync '["reset"]' >/dev/null
  sleep 2
  for round in $(seq 1 12); do
    for ip in $PEERS; do rpc addnode "[\"$ip\", \"onetry\"]" >/dev/null 2>&1 || true; done
    sleep 10
    ST=$($CLI $D mnsync status 2>/dev/null)
    PARSED=$(echo "$ST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('RequestedMasternodeAssets'), d.get('countMasternodeList'), d.get('countMasternodeWinner'))" 2>/dev/null)
    CONN=$(rpc getconnectioncount '[]' | python3 -c "import sys,json; print(json.load(sys.stdin).get('result','?'))" 2>/dev/null)
    log "round $round conns=$CONN mnsync=$PARSED"
    MNCT=$(echo "$PARSED" | awk '{print $2}')
    ASSET=$(echo "$PARSED" | awk '{print $1}')
    [ "$ASSET" = "999" ] && break
    [ -n "$MNCT" ] && [ "$MNCT" -gt 0 ] 2>/dev/null && break
  done
  for step in $(seq 1 6); do $CLI $D mnsync next 2>/dev/null || true; sleep 2; done
  $CLI $D startmasternode local false 2>&1 | head -c 200; echo
fi

echo "== DEFINITION OF DONE =="
echo "DoD-1 systemd_no_reindex: $(echo "$PROC" | grep -q '\-reindex' && echo FAIL || echo PASS) active=$UNIT"
HC=$(curl -sS -m 15 -o /tmp/mn2health.json -w '%{http_code}' http://127.0.0.1:5000/api/mn2/health)
python3 - <<'PY'
import json
d=json.load(open('/tmp/mn2health.json'))
ds=d.get('components',{}).get('daemon_staking',{})
print('DoD-2 mn2_health http=%s status=%s daemon_staking=%s' % (
  open('/tmp/mn2health_http.txt').read().strip() if False else '', d.get('status'), ds))
PY
echo "DoD-2 mn2_health_http: $HC"
python3 -c "import json; d=json.load(open('/tmp/mn2health.json')); ds=d.get('components',{}).get('daemon_staking',{}); print('DoD-2 daemon_staking', ds)"

LIST=$($CLI $D listmasternodes 2>/dev/null)
python3 -c "
import json,sys
raw=sys.argv[1] if len(sys.argv)>1 else '[]'
try: rows=json.loads(raw)
except: rows=[]
if isinstance(rows,int): print('DoD-3 ENABLED', rows); sys.exit()
if not isinstance(rows,list): rows=[rows] if rows else []
en=sum(1 for r in rows if isinstance(r,dict) and 'ENABLE' in str(r.get('status','')).upper())
a5=sum(1 for r in rows if isinstance(r,dict) and 'ENABLE' in str(r.get('status','')).upper() and int(r.get('activetime') or 0)>=5)
print('DoD-3 list_len', len(rows), 'ENABLED', en, 'ENABLED_act>=5', a5)
" "$LIST"

curl -sS -m 15 http://127.0.0.1:5000/api/shop/payment-health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('DoD-4 payment-health', d.get('status'), 'block', (d.get('mn2_daemon') or {}).get('block_height'))" 2>/dev/null

AVAIL_MB=$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
echo "DoD-5 ram_avail_mib: $AVAIL_MB"

$CLI $D mnsync status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('mnsync', {k:d.get(k) for k in ('IsBlockchainSynced','RequestedMasternodeAssets','countMasternodeList')})" 2>/dev/null
command -v pm2 >/dev/null && pm2 start explorer 2>/dev/null || true
echo "========== DONE =========="
ENDSCRIPT"""


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 immediate actions + DoD probe")
    p.add_argument("--no-mnsync", action="store_true", help="Skip mnsync-finish loop (faster)")
    args = p.parse_args()
    remote = (
        REMOTE_TEMPLATE.replace("__PEERS__", " ".join(PEERS))
        .replace("__DO_MNSYNC__", "0" if args.no_mnsync else "1")
    )
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(remote, timeout=600)
    out = (stdout.read() + stderr.read()).decode(errors="replace")
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
