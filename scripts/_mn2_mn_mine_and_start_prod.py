#!/usr/bin/env python3
"""Wait for mnsync, mine blocks if needed, start full fleet."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'E'
set +e
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html

wait_mnsync() {
  for i in $(seq 1 24); do
    sync=$($CLI mnsync status 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("IsBlockchainSynced"))' 2>/dev/null)
    echo "mnsync wait $i: synced=$sync"
    [ "$sync" = "True" ] && return 0
    sleep 10
  done
  return 1
}

wait_mnsync

bc1=$($CLI getblockcount 2>/dev/null)
echo "blockcount before=$bc1"

cols=$($CLI listunspent 0 9999999 2>/dev/null | python3 -c 'import json,sys; u=json.load(sys.stdin); c=[x for x in u if abs(float(x.get("amount",0))-5000)<0.01]; print(sum(1 for x in c if int(x.get("confirmations",0))>=10), len(c))')
echo "confirmed_ge10/total_5000: $cols"

need=$(echo $cols | awk '{print $1}')
total=$(echo $cols | awk '{print $2}')
if [ "${need:-0}" -lt 10 ] 2>/dev/null; then
  echo "== try generate 15 blocks for confirmations =="
  $CLI generate 15 2>&1 | head -c 800
  echo ""
  sleep 5
  bc2=$($CLI getblockcount 2>/dev/null)
  echo "blockcount after generate=$bc2"
  cols2=$($CLI listunspent 0 9999999 2>/dev/null | python3 -c 'import json,sys; u=json.load(sys.stdin); c=[x for x in u if abs(float(x.get("amount",0))-5000)<0.01]; print(sum(1 for x in c if int(x.get("confirmations",0))>=10), len(c), max([int(x.get("confirmations",0)) for x in c], default=0))')
  echo "after generate confirmed_ge10: $cols2"
fi

echo "== listmasternodeconf status =="
$CLI listmasternodeconf 2>/dev/null | python3 -c '
import json,sys
from collections import Counter
r=json.load(sys.stdin)
print(dict(Counter((x.get("status") or "?").upper() for x in r)))
'

LOCKED=$($CLI listlockunspent 2>/dev/null)
if [ "$LOCKED" != "[]" ] && [ -n "$LOCKED" ]; then $CLI lockunspent true "$LOCKED" 2>/dev/null; fi

echo "== fleet autostart =="
if [ -f $WEB/scripts/mn2_fleet_autostart.sh ]; then
  bash $WEB/scripts/mn2_fleet_autostart.sh 2>&1 | tail -40
else
  $CLI startmasternode local false 2>&1
  $CLI listmasternodeconf 2>/dev/null | python3 -c '
import json,sys
for r in json.load(sys.stdin):
    a=r.get("alias")
    if a: print(a)
' | while read a; do
    echo "start $a"
    $CLI startmasternode alias false "$a" 2>&1 | head -1
  done
fi

sleep 15
echo "== final =="
$CLI getmasternodecount 2>&1
$CLI listmasternodes 2>/dev/null | python3 -c '
import json,sys
raw=sys.stdin.read().strip()
if not raw: print("empty"); sys.exit(0)
rows=json.loads(raw)
if not isinstance(rows,list): rows=[rows]
en=sum(1 for r in rows if "ENABLE" in str(r.get("status","")).upper())
act=sum(1 for r in rows if "ACTIVE" in str(r.get("status","")).upper())
mis=sum(1 for r in rows if "MISSING" in str(r.get("status","")).upper())
print(f"ENABLED={en} ACTIVE={act} MISSING={mis} total={len(rows)}")
'

echo "== health API =="
curl -sS -m 10 http://127.0.0.1:5000/api/mn2/masternode/health 2>/dev/null | head -c 1200
echo ""
E
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, e = ssh.exec_command(REMOTE, timeout=600)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    err = e.read().decode(errors="replace")
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
