#!/usr/bin/env python3
"""Restart daemon to reload masternode.conf and start fleet via CLI."""
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

echo "== conf line 1 =="
head -1 $WEB/config/masternode.conf

echo "== restart daemon =="
systemctl restart masternoder2d
for i in $(seq 1 30); do
  sleep 5
  bc=$($CLI getblockcount 2>/dev/null)
  if [ -n "$bc" ] && [ "$bc" -gt 0 ] 2>/dev/null; then
    echo "RPC ready block=$bc"
    break
  fi
done

echo "== listmasternodeconf sample =="
$CLI listmasternodeconf 2>/dev/null | python3 -c '
import json,sys
rows=json.load(sys.stdin)
from collections import Counter
c=Counter((r.get("status") or "?").upper() for r in rows)
print("status", dict(c))
for r in rows[:3]:
    print(r.get("alias"), r.get("txHash","")[:16], r.get("status"))
'

echo "== unlock wallet if passphrase =="
PW=$(grep "^MN2_WALLET_PASSPHRASE=" $WEB/.env 2>/dev/null | cut -d= -f2- | tr -d "\r\"")
if [ -n "$PW" ]; then $CLI walletpassphrase "$PW" 600 2>/dev/null; fi

echo "== unlock locked utxos =="
LOCKED=$($CLI listlockunspent 2>/dev/null)
if [ "$LOCKED" != "[]" ] && [ -n "$LOCKED" ]; then
  $CLI lockunspent true "$LOCKED" 2>/dev/null
fi

echo "== fix privkey =="
bash $WEB/scripts/mn2_fix_daemon_privkey.sh --primary=platformmn2 2>/dev/null || true

echo "== start local =="
$CLI startmasternode local false 2>&1

echo "== start aliases (first 5) =="
for a in platformmn2 platformmn3 platformmn4 platformmn5 userSanderSb6296; do
  echo "--- $a ---"
  $CLI startmasternode alias false "$a" 2>&1
done

echo "== getmasternodecount =="
$CLI getmasternodecount 2>&1

echo "== listmasternodes =="
$CLI listmasternodes 2>/dev/null | python3 -c '
import json,sys
raw=sys.stdin.read().strip()
if not raw: print("(empty)"); sys.exit(0)
rows=json.loads(raw)
if not isinstance(rows,list): rows=[rows]
en=sum(1 for r in rows if "ENABLE" in str(r.get("status","")).upper())
print(f"ENABLED={en} total={len(rows)}")
for r in rows[:5]:
    print(r.get("status"), str(r.get("txhash",""))[:16])
'
E
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, e = ssh.exec_command(REMOTE, timeout=180)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    err = e.read().decode(errors="replace")
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
