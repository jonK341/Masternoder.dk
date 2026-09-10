#!/usr/bin/env python3
"""Deep collateral ownership analysis on production."""
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

python3 << "PY"
import json, subprocess
cli=["/opt/masternoder2d/masternoder2-cli","-datadir=/var/www/html/config"]

def rpc(*args):
    r=subprocess.run(cli+list(args), capture_output=True, text=True)
    if r.returncode!=0:
        return None, r.stderr.strip()
    try:
        return json.loads(r.stdout), None
    except Exception:
        return r.stdout.strip(), None

lines=[ln for ln in open("/var/www/html/config/masternode.conf") if ln.strip() and not ln.startswith("#")]
print(f"masternode.conf entries: {len(lines)}")
amounts=set()
for i, ln in enumerate(lines[:8]):
    p=ln.split()
    alias, tx, vout = p[0], p[3], int(p[4])
    out, err = rpc("gettxout", tx, str(vout))
    if not out:
        print(f"{alias}: gettxout fail {err}")
        continue
    amt = out.get("value")
    amounts.add(amt)
    spk = out.get("scriptPubKey", {})
    addr = spk.get("address") or (spk.get("addresses") or ["?"])[0]
    owned, _ = rpc("getaddressinfo", addr)
    in_wallet = owned.get("ismine") if isinstance(owned, dict) else False
    print(f"{alias}: amt={amt} addr={addr} ismine={in_wallet} conf={out.get('confirmations')}")

print("unique collateral amounts:", sorted(amounts))

# distribution of large utxos in wallet
utxos, _ = rpc("listunspent","1","9999999")
if isinstance(utxos, list):
    big=sorted([u for u in utxos if float(u.get("amount",0))>=1000], key=lambda u:-float(u["amount"]))
    print(f"wallet utxos >=1000 MN2: {len(big)}")
    for u in big[:10]:
        print(f"  {u['amount']} {u['txid'][:12]}:{u['vout']} conf={u.get('confirmations')}")

# pool addresses
for label in ["pool_1","pool_2","pool_3"]:
    a, _ = rpc("getaddressesbylabel", label)
    if a:
        print(f"label {label}: {list(a.keys())[:2]}")

wi, _ = rpc("getwalletinfo")
if wi:
    print(f"wallet balance={wi.get('balance')} txcount={wi.get('txcount')}")
PY

echo "== listaddressgroupings sample =="
/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config listaddressgroupings 2>/dev/null | python3 -c "
import json,sys
g=json.load(sys.stdin)
big=[]
for grp in g:
    bal=sum(float(x[1]) for x in grp)
    if bal>=5000: big.append((bal, grp[0][0] if grp else '?'))
big.sort(reverse=True)
print(f'groups >=5000: {len(big)}')
for b,a in big[:8]:
    print(f'  {b:.2f} {a}')
" 2>/dev/null
'
"""


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, stdout, _ = ssh.exec_command(CMD, timeout=90)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(stdout.read().decode(errors="replace"))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
