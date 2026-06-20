#!/usr/bin/env bash
# Safe collateral funding with lockunspent. Run on production as root.
#   bash scripts/mn2_fund_collateral_safe.sh --status
#   bash scripts/mn2_fund_collateral_safe.sh 1
set -euo pipefail

SEND_COUNT=1
if [[ "${1:-}" == "--status" ]]; then
  SEND_COUNT=0
elif [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  SEND_COUNT="$1"
fi

export MN2_FUND_SEND_COUNT="$SEND_COUNT"
python3 <<'PY'
import json, os, subprocess, sys

CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]
SEND_COUNT = int(os.environ.get("MN2_FUND_SEND_COUNT", "1"))
COLLATERAL = 5000.0
MIN_CONF = 10


def cli(*args):
    p = subprocess.run(CLI + list(args), capture_output=True, text=True, timeout=180)
    if p.returncode:
        raise SystemExit((p.stderr or p.stdout or "cli failed").strip())
    out = (p.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        if out.lower() in ("true", "false"):
            return out.lower() == "true"
        return out


def all_10k():
    rows = cli("listunspent", "1", "9999999") or []
    hits = {}
    for u in rows:
        if abs(float(u.get("amount") or 0) - COLLATERAL) < 1e-6:
            k = (u["txid"], int(u["vout"]))
            hits[k] = {**u, "locked": False}
    for item in cli("listlockunspent") or []:
        k = (item["txid"], int(item["vout"]))
        if k in hits:
            hits[k]["locked"] = True
            continue
        d = cli("gettxout", k[0], str(k[1]))
        if d and abs(float(d.get("value") or 0) - COLLATERAL) < 1e-6:
            hits[k] = {
                "txid": k[0], "vout": k[1],
                "confirmations": int(d.get("confirmations") or 0),
                "amount": float(d["value"]), "locked": True,
            }
    return list(hits.values())


def show(label):
    hits = all_10k()
    print(f"== {label} ==")
    for u in sorted(hits, key=lambda x: -int(x.get("confirmations") or 0)):
        lk = " locked" if u.get("locked") else ""
        print(u["txid"], "vout="+str(u["vout"]), "conf="+str(u.get("confirmations")), lk)
    ok = [u for u in hits if int(u.get("confirmations") or 0) >= MIN_CONF]
    print("ready:", len(ok), "/ 4 needed", "total_10k:", len(hits))
    return hits


show("10k UTXOs")
if SEND_COUNT == 0:
    sys.exit(0)

hits = all_10k()
locks = [{"txid": u["txid"], "vout": int(u["vout"])} for u in hits]
if locks:
    print("locking", len(locks), ":", cli("lockunspent", "false", json.dumps(locks)))

bal = float(cli("getbalance") or 0)
need = SEND_COUNT * COLLATERAL + 5
print("balance:", bal, "need ~", need)
if bal < need:
    raise SystemExit(f"insufficient balance: have {bal}, need ~{need}")

for i in range(SEND_COUNT):
    addr = cli("getnewaddress")
    txid = cli("sendtoaddress", str(addr), str(COLLATERAL))
    print(f"sent {i+1}/{SEND_COUNT}: txid={txid} addr={addr}")

show("after send")
PY
