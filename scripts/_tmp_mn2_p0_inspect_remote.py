#!/usr/bin/env python3
"""Inspect MN2 conf / chain / hosts / liabilities on production."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = r"""
set +e
cd /var/www/html
echo '== masternode.conf lines =='
wc -l config/masternode.conf
awk 'NF>=5 && $0 !~ /^#/ {c++} END{print "valid_rows", c+0}' config/masternode.conf
echo '== first 8 conf aliases/txids =='
awk 'NF>=5 && $0 !~ /^#/ {print $1, $4, $5}' config/masternode.conf | head -8
echo '== overlap analysis =='
python3 <<'PY'
import json, subprocess, os
CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]

def cli(*args):
    try:
        out = subprocess.check_output(CLI + list(args), stderr=subprocess.STDOUT, timeout=60)
        return out.decode(errors="replace")
    except Exception as e:
        return f"ERR {e}"

raw = cli("listmasternodes")
try:
    data = json.loads(raw)
except Exception as e:
    print("listmasternodes_parse_fail", e, raw[:300])
    data = []
rows = data if isinstance(data, list) else (data.get("result") if isinstance(data, dict) else [])
rows = rows or []
chain = {str(r.get("txhash") or "") for r in rows}
print("chain_count", len(rows), "enabled", sum(1 for r in rows if str(r.get("status","")).upper()=="ENABLED"))
print("nonzero_lastpaid", sum(1 for r in rows if int(r.get("lastpaid") or 0) > 0))

conf = {}
for line in open("config/masternode.conf", encoding="utf-8", errors="replace"):
    line=line.strip()
    if not line or line.startswith("#"):
        continue
    parts=line.split()
    if len(parts) < 5:
        continue
    conf[parts[0]] = {"txid": parts[3], "vout": parts[4], "ip": parts[1]}
conf_tx = {v["txid"] for v in conf.values()}
print("conf_aliases", len(conf), "conf_txids", len(conf_tx), "overlap_conf_chain", len(conf_tx & chain))

hosts = json.load(open("data/mn2_masternode_hosts.json")).get("hosts") or []
ht = {str(h.get("collateral_txid") or "") for h in hosts if h.get("collateral_txid")}
print("hosts", len(hosts), "host_txids", len(ht), "overlap_hosts_chain", len(ht & chain), "overlap_hosts_conf", len(ht & conf_tx))

# conf aliases present on chain
on = [a for a,v in conf.items() if v["txid"] in chain]
off = [a for a,v in conf.items() if v["txid"] not in chain]
print("conf_on_chain", len(on), "conf_off_chain", len(off))
print("off_sample", off[:10])
print("on_sample", on[:10])

# getmasternodecount
print("getmasternodecount", cli("getmasternodecount")[:400])
print("getblockcount", cli("getblockcount")[:80])

# sporks relevant
raw = cli("spork", "show")
try:
    d = json.loads(raw)
    r = d.get("result", d) if isinstance(d, dict) else {}
    for k,v in sorted((r or {}).items()):
        ku = k.upper()
        if any(x in ku for x in ("PAY", "MASTER", "WIN", "NEW", "MN")):
            print("spork", k, v)
except Exception as e:
    print("spork_err", e, raw[:300])
PY

echo '== top liquid holders =='
python3 <<'PY'
import os, json
base = "logs/unified_points"
rows = []
for fn in os.listdir(base):
    if not fn.endswith(".json"):
        continue
    try:
        raw = json.load(open(os.path.join(base, fn), encoding="utf-8"))
    except Exception:
        continue
    syss = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
    liq = float(syss.get("mn2_balance") or 0)
    st = float(syss.get("mn2_staked") or 0)
    if liq + st > 0:
        rows.append((liq + st, liq, st, fn[:-5]))
rows.sort(reverse=True)
print("holders", len(rows))
for t, l, s, u in rows[:8]:
    print(round(t, 2), "liq", round(l, 2), "staked", round(s, 2), u[:48])
print("sum_total", round(sum(t for t,_,_,_ in rows), 2))
print("sum_liq", round(sum(l for _,l,_,_ in rows), 2))
PY
"""


def main() -> int:
    pw = require_deploy_pass(force_prompt=False)
    ssh, method, _ = connect_deploy_ssh(pw)
    print("auth", method)
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=180)
    print(stdout.read().decode(errors="replace"))
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("STDERR", err[:1500])
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
