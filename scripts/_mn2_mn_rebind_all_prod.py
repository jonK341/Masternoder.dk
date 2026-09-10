#!/usr/bin/env python3
"""Rebind all masternode.conf entries to wallet-owned collateral on production."""
from __future__ import annotations

import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE_PY = r'''
import json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone

WEB = "/var/www/html"
CONF = "/var/www/html/config/masternode.conf"
CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]
COLLATERAL = 5000.0
DRY_RUN = __DRY_RUN__
FUND = __FUND__
REBIND = __REBIND__
START = __START__
WAIT_MIN = __WAIT_MIN__
MIN_CONF = 10

cfg_path = os.path.join(WEB, "data", "mn2_masternode_config.json")
ops = {}
try:
    ops = (json.load(open(cfg_path)).get("ops") or {})
except Exception:
    pass
IP = (ops.get("external_ip") or "140.82.39.124").strip()
PORT = int(ops.get("masternode_port") or 17646)
MIN_CONF = int(ops.get("min_collateral_confirmations") or MIN_CONF)
IP_PORT = f"{IP}:{PORT}"


def cli(*args):
    p = subprocess.run(CLI + list(args), capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "cli failed").strip())
    out = (p.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def parse_conf():
    rows = []
    if not os.path.isfile(CONF):
        return rows
    for line in open(CONF, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) < 5:
            continue
        rows.append({
            "alias": p[0], "ip_port": p[1], "privkey": p[2],
            "txid": p[3], "vout": int(p[4]), "raw": line,
        })
    return rows


def wallet_keys():
    utxos = cli("listunspent", "0", "9999999")
    if not isinstance(utxos, list):
        return set()
    return {(str(u["txid"]), int(u["vout"])) for u in utxos if isinstance(u, dict)}


def collateral_5000():
    utxos = cli("listunspent", "0", "9999999")
    if not isinstance(utxos, list):
        return []
    out = []
    for u in utxos:
        if not isinstance(u, dict):
            continue
        if abs(float(u.get("amount") or 0) - COLLATERAL) > 1e-8:
            continue
        out.append({
            "txid": str(u["txid"]), "vout": int(u["vout"]),
            "confirmations": int(u.get("confirmations") or 0),
            "address": u.get("address"),
        })
    return out


def lock_existing_collateral():
    cols = collateral_5000()
    if not cols:
        return 0
    locks = [{"txid": c["txid"], "vout": c["vout"]} for c in cols]
    cli("lockunspent", "false", json.dumps(locks))
    return len(locks)


entries = parse_conf()
print(f"conf entries: {len(entries)}")
wkeys = wallet_keys()
need = []
ok = []
for e in entries:
    key = (e["txid"], e["vout"])
    if key in wkeys:
        ok.append(e)
    else:
        need.append(e)
print(f"in_wallet={len(ok)} need_rebind={len(need)}")
if need:
    for e in need[:5]:
        print(f"  missing: {e['alias']} {e['txid'][:12]}:{e['vout']}")

if not need:
    print("All collateral already in wallet")
    if START:
        subprocess.run(["systemctl", "restart", "masternoder2d"], check=False)
        time.sleep(15)
    sys.exit(0)

if FUND:
    balance = float(cli("getbalance") or 0)
    required = len(need) * COLLATERAL + len(need) * 0.5 + 10
    print(f"balance={balance:.2f} required~={required:.2f} for {len(need)} collaterals")
    if balance < required:
        print(f"FAIL insufficient balance", file=sys.stderr)
        sys.exit(1)
    if DRY_RUN:
        print(f"DRY_RUN would fund {len(need)} x {COLLATERAL}")
    else:
        locked = lock_existing_collateral()
        print(f"locked {locked} existing 5000 UTXOs")
        created = []
        for i, e in enumerate(need):
            addr = cli("getnewaddress")
            txid = cli("sendtoaddress", str(addr), str(COLLATERAL))
            created.append({"alias": e["alias"], "txid": txid, "vout": 0, "address": addr})
            print(f"fund {i+1}/{len(need)} {e['alias']}: {txid}")
            time.sleep(1)
        if REBIND:
            deadline = time.time() + WAIT_MIN * 60
            attempt = 0
            while time.time() < deadline:
                attempt += 1
                free = [u for u in collateral_5000() if u["confirmations"] >= MIN_CONF]
                print(f"wait {attempt}: confirmed_5000={len(free)}/{len(need)}")
                if len(free) >= len(need):
                    break
                time.sleep(30)
            else:
                print(f"WARN: only {len([u for u in collateral_5000() if u['confirmations'] >= MIN_CONF])} confirmed after {WAIT_MIN}m")
                print("Proceeding with available UTXOs (may need re-run after conf)", file=sys.stderr)

if not REBIND:
    print("FUND_ONLY done")
    sys.exit(0)

free = [u for u in collateral_5000() if u["confirmations"] >= MIN_CONF]
used = {(e["txid"], e["vout"]) for e in ok}
assignments = {}
for e in ok:
    assignments[e["alias"]] = (e["txid"], e["vout"])

for e in need:
    utxo = None
    for u in free:
        key = (u["txid"], u["vout"])
        if key in used:
            continue
        utxo = u
        used.add(key)
        break
    if not utxo:
        print(f"WARN no free UTXO for {e['alias']} yet", file=sys.stderr)
        assignments[e["alias"]] = (e["txid"], e["vout"])
    else:
        assignments[e["alias"]] = (utxo["txid"], utxo["vout"])
        print(f"rebind {e['alias']}: {e['txid'][:12]}:{e['vout']} -> {utxo['txid'][:12]}:{utxo['vout']} conf={utxo['confirmations']}")

if DRY_RUN:
    print("DRY_RUN rebind plan:", json.dumps(assignments, indent=2))
    sys.exit(0)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
shutil.copy2(CONF, CONF + f".bak-rebind-{ts}")
lines = []
for line in open(CONF, encoding="utf-8"):
    s = line.strip()
    if not s or s.startswith("#"):
        lines.append(line if line.endswith("\n") else line + "\n")
        continue
    p = s.split()
    if len(p) < 5:
        lines.append(line)
        continue
    alias = p[0]
    txid, vout = assignments.get(alias, (p[3], int(p[4])))
    ip_port = p[1] if p[1] else IP_PORT
    lines.append(f"{alias} {ip_port} {p[2]} {txid} {vout}\n")
with open(CONF, "w", encoding="utf-8") as f:
    f.writelines(lines)
print(f"updated {CONF} (backup .bak-rebind-{ts})")

if START:
    locked = cli("listlockunspent")
    if isinstance(locked, list) and locked:
        cli("lockunspent", "true", json.dumps(locked))
    subprocess.run(["systemctl", "restart", "masternoder2d"], check=False)
    for i in range(40):
        time.sleep(5)
        try:
            h = cli("getblockcount")
            if isinstance(h, int) and h > 0:
                print("RPC ready", h)
                break
        except Exception:
            pass
    sys.path.insert(0, WEB)
    from backend.services import mn2_masternode_service as mn
    mn._unlock_collateral_utxos()
    for e in parse_conf():
        alias = e["alias"]
        try:
            err = mn._start_masternode(alias, e["privkey"], conf_changed=True)
            print(f"start {alias}: {'OK' if not err else err}")
        except Exception as exc:
            print(f"start {alias}: ERROR {exc}")
    print("getmasternodecount:", json.dumps(cli("getmasternodecount")))
    rows = cli("listmasternodes")
    if isinstance(rows, list):
        en = sum(1 for r in rows if isinstance(r, dict) and "ENABLE" in str(r.get("status", "")).upper())
        print(f"ENABLED count from listmasternodes: {en}/{len(rows)}")
'''


def build_remote(*, dry_run: bool, fund: bool, rebind: bool, start: bool, wait_min: int) -> str:
    py = (
        REMOTE_PY.replace("__DRY_RUN__", "True" if dry_run else "False")
        .replace("__FUND__", "True" if fund else "False")
        .replace("__REBIND__", "True" if rebind else "False")
        .replace("__START__", "True" if start else "False")
        .replace("__WAIT_MIN__", str(wait_min))
    )
    b64 = base64.b64encode(py.encode()).decode()
    return f"""bash -s <<'ENDSCRIPT'
cd /var/www/html
python3 <<'PY'
import base64
exec(base64.b64decode('{b64}').decode())
PY
ENDSCRIPT
"""


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fund-only", action="store_true")
    p.add_argument("--skip-fund", action="store_true")
    p.add_argument("--no-start", action="store_true")
    p.add_argument("--wait-min", type=int, default=20)
    args = p.parse_args()

    fund = not args.skip_fund
    rebind = not args.fund_only
    start = not args.no_start and not args.dry_run and not args.fund_only
    timeout = max(600, args.wait_min * 60 + 300)

    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    cmd = build_remote(dry_run=args.dry_run, fund=fund, rebind=rebind, start=start, wait_min=args.wait_min)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0 if "FAIL" not in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
