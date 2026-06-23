#!/usr/bin/env python3
"""
Fund missing 10k MN2 collateral UTXOs and reinstall platform-mn-2..5 with wallet-verified txids.

Usage (from repo root):
  python scripts/mn2_masternode_reinstall_remote.py --ask-pass
  python scripts/mn2_masternode_reinstall_remote.py --ask-pass --dry-run
  python scripts/mn2_masternode_reinstall_remote.py --ask-pass --fund-only
  python scripts/mn2_masternode_reinstall_remote.py --ask-pass --skip-fund
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"
DEFAULT_HOSTS = ["platform-mn-2", "platform-mn-3", "platform-mn-4", "platform-mn-5"]


def sh(ssh, cmd: str, timeout: int = 900) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


REMOTE_PY = r'''
import json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone

WEB = "/var/www/html"
CONF = "/var/www/html/config/masternode.conf"
HOSTS_FILE = os.path.join(WEB, "data", "mn2_masternode_hosts.json")
CONFIG_FILE = os.path.join(WEB, "data", "mn2_masternode_config.json")
CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]
HOST_IDS = __HOST_IDS__
DRY_RUN = __DRY_RUN__
FUND_MISSING = __FUND_MISSING__
REINSTALL = __REINSTALL__
WAIT_MINUTES = __WAIT_MINUTES__
COLLATERAL = 5000.0
IP = "140.82.39.124"
PORT = 17646
MIN_CONF = 10

cfg = {}
try:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    pass
ops = cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {}
IP = (ops.get("external_ip") or IP).strip() or IP
PORT = int(ops.get("masternode_port") or PORT)
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
        if out.lower() in ("true", "false"):
            return out.lower() == "true"
        return out


def all_10k_utxos():
    rows = cli("listunspent", "1", "9999999")
    if not isinstance(rows, list):
        rows = []
    hits = {}
    for u in rows:
        if not isinstance(u, dict):
            continue
        if abs(float(u.get("amount") or 0) - COLLATERAL) > 1e-8:
            continue
        key = (str(u["txid"]), int(u["vout"]))
        hits[key] = {
            "txid": key[0],
            "vout": key[1],
            "address": u.get("address"),
            "confirmations": int(u.get("confirmations") or 0),
            "amount": float(u.get("amount") or 0),
            "locked": False,
        }
    locked = cli("listlockunspent")
    if isinstance(locked, list):
        for item in locked:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("txid")), int(item.get("vout")))
            if key in hits:
                hits[key]["locked"] = True
                continue
            detail = cli("gettxout", key[0], str(key[1]))
            if not isinstance(detail, dict):
                continue
            val = float(detail.get("value") or 0)
            if abs(val - COLLATERAL) > 1e-8:
                continue
            hits[key] = {
                "txid": key[0],
                "vout": key[1],
                "address": None,
                "confirmations": int(detail.get("confirmations") or 0),
                "amount": val,
                "locked": True,
            }
    return list(hits.values())


def wallet_10k_utxos():
    return all_10k_utxos()


def alias_for(host_id: str) -> str:
    import re
    alias = re.sub(r"[^a-zA-Z0-9]", "", (host_id or "").strip())[:16]
    return alias or host_id.replace("-", "")[:16]


def load_hosts_doc():
    try:
        with open(HOSTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"hosts": []}


def save_hosts_doc(doc):
    doc["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(HOSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


def parse_conf(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            rows.append({
                "alias": parts[0],
                "privkey": parts[2],
                "txid": parts[3],
                "vout": int(parts[4]),
            })
    return rows


def on_chain_collateral_keys():
    keys = set()
    try:
        rows = cli("listmasternodes")
        if isinstance(rows, list):
            for mn in rows:
                if not isinstance(mn, dict):
                    continue
                txhash = mn.get("txhash") or mn.get("collateralHash")
                idx = mn.get("outputidx") if mn.get("outputidx") is not None else mn.get("index")
                if txhash is not None and idx is not None:
                    keys.add((str(txhash), int(idx)))
    except Exception:
        pass
    return keys


def lock_collateral_utxos():
    """Lock all 10k wallet UTXOs so sendtoaddress uses other balance, not collateral."""
    utxos = wallet_10k_utxos()
    if not utxos:
        return 0
    locks = [{"txid": u["txid"], "vout": u["vout"]} for u in utxos]
    cli("lockunspent", "false", json.dumps(locks))
    return len(locks)


def free_confirmed_utxos(reserved):
    utxos = wallet_10k_utxos()
    free = []
    for u in utxos:
        key = (u["txid"], u["vout"])
        if key in reserved:
            continue
        if u["confirmations"] < MIN_CONF:
            continue
        free.append(u)
    return free


def ensure_collateral_pool(needed: int, reserved):
    free = free_confirmed_utxos(reserved)
    print(f"== collateral pool: need {needed}, free confirmed {len(free)} (min_conf={MIN_CONF}) ==")
    if len(free) >= needed:
        return free

    missing = needed - len(free)
    if not FUND_MISSING:
        print(f"FAIL need {missing} more confirmed 10k UTXOs (use --fund or free wallet MN2)", file=sys.stderr)
        sys.exit(1)

    balance = float(cli("getbalance") or 0)
    required = missing * COLLATERAL + max(5.0, missing * 0.5)
    print(f"== wallet balance {balance} MN2; creating {missing} x {COLLATERAL} sends (need ~{required}) ==")
    if balance < required:
        print(f"FAIL insufficient MN2: have {balance}, need ~{required} for {missing} collaterals", file=sys.stderr)
        sys.exit(1)

    if DRY_RUN:
        print(f"DRY_RUN would send {missing} x {COLLATERAL} MN2 to new addresses")
        return free

    created = []
    locked = lock_collateral_utxos()
    print(f"== locked {locked} existing 10k UTXO(s) before funding ==")
    for i in range(missing):
        addr = cli("getnewaddress")
        txid = cli("sendtoaddress", str(addr), str(COLLATERAL))
        created.append({"txid": txid, "address": addr})
        print(f"sent collateral {i + 1}/{missing}: txid={txid} addr={addr}")
        time.sleep(2)

    deadline = time.time() + WAIT_MINUTES * 60
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        free = free_confirmed_utxos(reserved)
        pending = [u for u in wallet_10k_utxos()
                   if (u["txid"], u["vout"]) not in reserved and u["confirmations"] < MIN_CONF]
        print(f"wait {attempt}: confirmed_free={len(free)}/{needed}, pending_10k={len(pending)}")
        if len(free) >= needed:
            return free
        time.sleep(30)

    print(f"FAIL timed out after {WAIT_MINUTES}m waiting for {MIN_CONF} confirmations", file=sys.stderr)
    print("Re-run later with: python scripts/mn2_masternode_reinstall_remote.py --ask-pass --skip-fund", file=sys.stderr)
    sys.exit(2)


reserved = on_chain_collateral_keys()
print("== on-chain collateral reserved ==")
print(json.dumps(list(reserved)))

print("== all wallet 10k UTXOs ==")
print(json.dumps({"count": len(wallet_10k_utxos()), "outputs": wallet_10k_utxos()}, indent=2))

needed = len(HOST_IDS)
free_utxos = ensure_collateral_pool(needed, reserved)

if not REINSTALL:
    print("FUND_ONLY done")
    sys.exit(0)

if len(free_utxos) < needed:
    print(f"FAIL only {len(free_utxos)} confirmed UTXOs available", file=sys.stderr)
    sys.exit(1)

old_by_alias = {r["alias"]: r for r in parse_conf(CONF)}
print("== current masternode.conf ==")
print(open(CONF, encoding="utf-8").read() if os.path.isfile(CONF) else "(missing)")

doc = load_hosts_doc()
hosts = [h for h in (doc.get("hosts") or []) if isinstance(h, dict)]
host_by_id = {h.get("id"): h for h in hosts}

assignments = []
used_keys = set(reserved)
for hid in HOST_IDS:
    alias = alias_for(hid)
    old = old_by_alias.get(alias) or {}
    privkey = old.get("privkey") or cli("createmasternodekey")
    if not isinstance(privkey, str):
        raise RuntimeError(f"createmasternodekey failed for {hid}")
    utxo = None
    for u in free_utxos:
        key = (u["txid"], u["vout"])
        if key in used_keys:
            continue
        utxo = u
        used_keys.add(key)
        break
    if not utxo:
        print(f"FAIL no free 10k UTXO for {hid}", file=sys.stderr)
        sys.exit(1)
    assignments.append({
        "host_id": hid,
        "alias": alias,
        "privkey": privkey,
        "txid": utxo["txid"],
        "vout": utxo["vout"],
        "address": utxo.get("address"),
        "confirmations": utxo.get("confirmations"),
        "old_txid": old.get("txid"),
        "old_vout": old.get("vout"),
    })

print("== planned assignments ==")
print(json.dumps(assignments, indent=2))

if DRY_RUN:
    print("DRY_RUN — no conf/registry/broadcast changes")
    sys.exit(0)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
if os.path.isfile(CONF):
    shutil.copy2(CONF, CONF + f".bak-{ts}")

lines = [
    f"# Masternode config file — reinstalled {ts}\n",
    "# Format: alias IP:port masternodeprivkey collateral_output_txid collateral_output_index\n",
]
for a in assignments:
    lines.append(f"{a['alias']} {IP_PORT} {a['privkey']} {a['txid']} {a['vout']}\n")
with open(CONF, "w", encoding="utf-8") as f:
    f.writelines(lines)
os.chmod(CONF, 0o664)
try:
    import pwd
    uid = pwd.getpwnam("www-data").pw_uid
    gid = pwd.getpwnam("www-data").pw_gid
    os.chown(CONF, uid, gid)
except Exception:
    pass

for a in assignments:
    hid = a["host_id"]
    idx = next((i for i, h in enumerate(hosts) if h.get("id") == hid), None)
    row = {
        "id": hid,
        "label": (host_by_id.get(hid) or {}).get("label") or hid,
        "status": "provisioning",
        "collateral_txid": a["txid"],
        "collateral_vout": a["vout"],
        "collateral_address": a.get("address"),
        "broadcast_address": IP_PORT,
        "notes": f"Reinstalled {ts} with wallet-verified collateral",
    }
    if idx is None:
        row["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        hosts.append(row)
    else:
        prev = hosts[idx]
        row["created_at"] = prev.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row["owner_user_id"] = prev.get("owner_user_id")
        hosts[idx] = row

doc["hosts"] = hosts
save_hosts_doc(doc)

print("== unlock collateral UTXOs (required before startmasternode) ==")
locked = cli("listlockunspent")
if isinstance(locked, list) and locked:
    print("unlocking", len(locked), ":", cli("lockunspent", "true", json.dumps(locked)))
else:
    print("none locked")

print("== restart daemon to reload masternode.conf ==")
subprocess.run(["systemctl", "restart", "masternoder2d"], check=False)
for i in range(36):
    time.sleep(5)
    try:
        h = cli("getblockcount")
        if isinstance(h, int) and h > 0:
            print("RPC ready, blockcount", h)
            break
    except Exception:
        pass
else:
    raise RuntimeError("daemon did not come back after restart")

print("== listmasternodeconf (after restart) ==")
print(json.dumps(cli("listmasternodeconf"), indent=2))

print("== startmasternode local first (alias fallback) ==")
sys.path.insert(0, WEB)
from backend.services import mn2_masternode_service as mn

for a in assignments:
    alias = a["alias"]
    privkey = a["privkey"]
    print(f"--- {alias} ---")
    try:
        err = mn._start_masternode(alias, privkey)
        if err:
            print("ERROR", err)
        else:
            print("OK")
    except Exception as exc:
        print("ERROR", exc)

print("== getmasternodecount ==")
print(json.dumps(cli("getmasternodecount"), indent=2))
'''


def build_remote(
    host_ids: list[str],
    *,
    dry_run: bool,
    fund_missing: bool,
    reinstall: bool,
    wait_minutes: int,
) -> str:
    py = (
        REMOTE_PY.replace("__HOST_IDS__", json.dumps(host_ids))
        .replace("__DRY_RUN__", "True" if dry_run else "False")
        .replace("__FUND_MISSING__", "True" if fund_missing else "False")
        .replace("__REINSTALL__", "True" if reinstall else "False")
        .replace("__WAIT_MINUTES__", str(wait_minutes))
    )
    py_b64 = __import__("base64").b64encode(py.encode("utf-8")).decode("ascii")
    return f'''bash -s <<'ENDSCRIPT'
set -e
cd {WEB}
python3 <<'PY'
import base64
exec(base64.b64decode("{py_b64}").decode("utf-8"))
PY
ENDSCRIPT
'''


def main() -> int:
    p = argparse.ArgumentParser(description="Fund + reinstall MN2 masternode fleet")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fund-only", action="store_true", help="Create missing 10k UTXOs only")
    p.add_argument("--skip-fund", action="store_true", help="Do not send new collateral")
    p.add_argument("--wait-minutes", type=int, default=45, help="Wait for confirmations after funding")
    p.add_argument("--hosts", default=",".join(DEFAULT_HOSTS))
    args = p.parse_args()

    host_ids = [h.strip() for h in args.hosts.split(",") if h.strip()]
    if not host_ids:
        print("No host ids", file=sys.stderr)
        return 1

    fund_missing = not args.skip_fund
    reinstall = not args.fund_only
    timeout = max(900, args.wait_minutes * 60 + 120)

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    print(f"== Connected {deploy_user()}@{deploy_host()} ==")
    print(f"== Hosts: {', '.join(host_ids)} | fund={fund_missing} reinstall={reinstall} ==\n")

    out = sh(
        ssh,
        build_remote(
            host_ids,
            dry_run=args.dry_run,
            fund_missing=fund_missing,
            reinstall=reinstall,
            wait_minutes=args.wait_minutes,
        ),
        timeout=timeout,
    )
    print(out)
    ssh.close()

    if "FAIL" in out:
        return 1 if "timed out" not in out.lower() else 2
    if args.dry_run:
        return 0 if "planned assignments" in out or "DRY_RUN" in out else 1
    return 0 if "getmasternodecount" in out or "FUND_ONLY done" in out else 1


if __name__ == "__main__":
    sys.exit(main())
