#!/usr/bin/env python3
"""One-shot production masternode diagnostics via SSH."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

DIAG = r"""bash -s <<'ENDSCRIPT'
set +e
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html

echo '========== MN2 MASTERNODE DIAGNOSTICS =========='
echo '== daemon =='
systemctl is-active masternoder2d
echo '== getblockcount =='
$CLI getblockcount 2>&1
echo '== getblockchaininfo sync =='
$CLI getblockchaininfo 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('verificationprogress:', d.get('verificationprogress')); print('blocks:', d.get('blocks')); print('headers:', d.get('headers'))" 2>/dev/null || $CLI getblockchaininfo 2>&1 | head -c 500
echo '== mnsync =='
$CLI mnsync status 2>&1 | head -c 800
echo ''
echo '== getwalletinfo =='
$CLI getwalletinfo 2>&1
echo '== getmasternodecount =='
$CLI getmasternodecount 2>&1
echo '== wallet.dat =='
ls -la $WEB/config/wallet.dat 2>&1
ls -la $WEB/config/wallets/ 2>&1 | head -5
echo '== listunspent 5000 MN2 =='
$CLI listunspent 1 9999999 2>/dev/null | python3 -c "
import json,sys
try:
    utxos=json.load(sys.stdin)
except Exception as e:
    print('parse fail', e); sys.exit(0)
coll=[u for u in utxos if abs(float(u.get('amount',0))-5000.0)<0.01]
print(f'total utxos: {len(utxos)}')
print(f'5000 MN2 collateral utxos: {len(coll)}')
for u in coll[:10]:
    print(f\"  {u.get('txid')}:{u.get('vout')} amount={u.get('amount')} conf={u.get('confirmations')}\")
"
echo '== listmasternodeconf summary =='
$CLI listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
try:
    rows=json.load(sys.stdin)
except Exception as e:
    print('parse error', e); sys.exit(0)
from collections import Counter
c=Counter()
for r in rows:
    st=(r.get('status') or 'unknown').upper()
    c[st]+=1
print(f'total entries: {len(rows)}')
for k,v in sorted(c.items()):
    print(f'  {k}: {v}')
miss=[r for r in rows if 'MISSING' in str(r.get('status','')).upper()]
print(f'--- first 5 MISSING (of {len(miss)}) ---')
for r in miss[:5]:
    print(f\"  {r.get('alias')}: addr={r.get('address')} tx={str(r.get('txhash',''))[:20]} status={r.get('status')}\")
"
echo '== masternode.conf line count =='
wc -l $WEB/config/masternode.conf 2>/dev/null
echo '== mn2_masternode_hosts.json summary =='
python3 << 'PY'
import json
from collections import Counter
p='/var/www/html/data/mn2_masternode_hosts.json'
try:
    d=json.load(open(p))
except Exception as e:
    print('load error', e)
    raise SystemExit
hosts = d.get('hosts', d) if isinstance(d, dict) else d
if not isinstance(hosts, list):
    hosts = list(hosts.values()) if isinstance(hosts, dict) else []
c = Counter()
for h in hosts:
    st = h.get('status') or h.get('state') or 'unknown'
    c[st] += 1
print(f'registry entries: {len(hosts)}')
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
print('--- provisioning / waiting slots ---')
for h in hosts:
    alias = h.get('alias') or h.get('name') or h.get('id') or '?'
    st = h.get('status') or h.get('state') or ''
    prov = h.get('provisioning_state') or h.get('provision') or h.get('provisioning') or ''
    updated = h.get('updated_at') or h.get('updated') or h.get('created_at') or ''
    blob = f'{st} {prov} {updated}'.lower()
    if any(x in blob for x in ('provision', 'wait', 'queued', '2026-07', 'pending')):
        print(f'  {alias}: status={st} prov={prov} updated={updated}')
PY
echo '== masternoder2.conf masternode lines =='
grep -nE '^(masternode|masternodeprivkey|masternodeaddr|externalip)=' $WEB/config/masternoder2.conf 2>/dev/null | head -20
echo '== getbalance =='
$CLI getbalance 2>&1
echo '== listmasternodes ENABLED summary =='
$CLI listmasternodes 2>/dev/null | python3 -c "
import json,sys
raw=sys.stdin.read().strip()
if not raw:
    print('(empty)'); sys.exit(0)
try:
    rows=json.loads(raw)
except Exception as e:
    print('parse error', e); print(raw[:1500]); sys.exit(0)
if not isinstance(rows, list):
    rows=[rows]
enabled=active=missing=0
for r in rows:
    st=str(r.get('status','')).upper()
    if 'ENABLE' in st: enabled+=1
    if 'ACTIVE' in st: active+=1
    if 'MISSING' in st: missing+=1
print(f'ENABLED={enabled} ACTIVE={active} MISSING={missing} total={len(rows)}')
"
ENDSCRIPT
"""


def sh(ssh, cmd: str, timeout: int = 180) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + (("\n[stderr] " + err) if err.strip() else "")


def main() -> int:
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    print(sh(ssh, DIAG))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
