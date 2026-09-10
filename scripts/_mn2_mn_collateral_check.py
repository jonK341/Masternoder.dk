#!/usr/bin/env python3
"""Check collateral UTXOs and masternode conf on production."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

CMD = r"""bash -lc '
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html
systemctl start masternoder2d 2>/dev/null
sleep 3
echo "== systemd =="; systemctl is-active masternoder2d
echo "== listunspent 5000 =="
$CLI listunspent 1 9999999 2>/dev/null | python3 -c "
import json,sys
utxos=json.load(sys.stdin)
coll=[u for u in utxos if abs(float(u.get(\"amount\",0))-5000.0)<0.01]
print(f\"total={len(utxos)} collateral_5000={len(coll)}\")
for u in coll[:15]:
    print(f\"  {u[\"txid\"]}:{u[\"vout\"]} conf={u.get(\"confirmations\")}\")
"
echo "== listmasternodeconf =="
$CLI listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
from collections import Counter
rows=json.load(sys.stdin)
c=Counter((r.get(\"status\") or \"?\").upper() for r in rows)
print(\"status:\", dict(c), \"total\", len(rows))
for r in rows[:5]:
    print(f\"  {r.get(\"alias\")} {r.get(\"status\")} {str(r.get(\"txhash\",\"\"))[:16]}\")
"
echo "== cross-check conf vs wallet =="
python3 << PY
import json, subprocess
conf="/var/www/html/config/masternode.conf"
cli=["/opt/masternoder2d/masternoder2-cli","-datadir=/var/www/html/config"]
lines=open(conf).read().splitlines()
wallet=json.loads(subprocess.check_output(cli+["listunspent","1","9999999"], text=True))
wset={(u["txid"], u["vout"]) for u in wallet}
coll500={(u["txid"], u["vout"]) for u in wallet if abs(float(u["amount"])-5000)<0.01}
in_wallet=on_chain=missing=0
for ln in lines:
    p=ln.split()
    if len(p)<5: continue
    tx,vout=p[3],int(p[4])
    key=(tx,vout)
    out=subprocess.run(cli+["gettxout",tx,str(vout)], capture_output=True, text=True)
    on = out.stdout.strip() not in ("","null")
    if on: on_chain+=1
    if key in wset: in_wallet+=1
    else: missing+=1
print(f"conf_entries={len(lines)} on_chain={on_chain} in_wallet={in_wallet} not_in_wallet={missing} free_5000={len(coll500)}")
PY
echo "== mnsync =="
$CLI mnsync status 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d)" 2>/dev/null || $CLI mnsync status 2>&1 | head -c 400
'
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, stdout, _ = ssh.exec_command(CMD, timeout=120)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(stdout.read().decode(errors="replace"))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
