#!/usr/bin/env python3
"""
Re-collateralize spent masternode.conf aliases on production.

Creates new 5,000 MN2 UTXOs for aliases whose collateral is spent/missing
(or duplicated), rewrites masternode.conf, syncs hosts registry, restarts
daemon, and starts each alias.

Usage:
  python scripts/mn2_recollateralize_fleet_remote.py --dry-run
  python scripts/mn2_recollateralize_fleet_remote.py --limit 5
  python scripts/mn2_recollateralize_fleet_remote.py --limit 40 --wait-minutes 25
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

WEB = "/var/www/html"


def build_remote(*, dry_run: bool, limit: int, wait_minutes: int, fund: bool) -> str:
    return f"""
set -e
cd {WEB}
export PYTHONPATH={WEB}
python3 - <<'PY'
import json, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone

WEB = {WEB!r}
CONF = WEB + "/config/masternode.conf"
HOSTS_FILE = WEB + "/data/mn2_masternode_hosts.json"
CONFIG_FILE = WEB + "/data/mn2_masternode_config.json"
CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]
DRY_RUN = {str(dry_run)}
LIMIT = {int(limit)}
WAIT_MINUTES = {int(wait_minutes)}
FUND = {str(fund)}
COLLATERAL = 5000.0
MIN_CONF = 10
IP = "140.82.39.124"
PORT = 17646

def load_env(path=WEB + "/.env"):
    out = {{}}
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

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

env = load_env()
pw = (env.get("MN2_WALLET_PASSPHRASE") or "").strip()
cfg = {{}}
try:
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
except Exception:
    pass
ops = cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {{}}
IP = (ops.get("external_ip") or IP).strip() or IP
PORT = int(ops.get("masternode_port") or PORT)
MIN_CONF = int(ops.get("min_collateral_confirmations") or MIN_CONF)
COLLATERAL = float(cfg.get("collateral_mn2") or COLLATERAL)
IP_PORT = f"{{IP}}:{{PORT}}"

def unlock(spend=False, timeout=600):
    if not pw:
        print("WARN: MN2_WALLET_PASSPHRASE missing — assuming wallet already unlocked for spend")
        return
    # staking_only=false when spend=True
    args = ["walletpassphrase", pw, str(int(timeout))]
    if not spend:
        args.append("true")
    else:
        args.append("false")
    try:
        print("unlock", "spend" if spend else "staking", cli(*args))
    except Exception as e:
        print("unlock_err", e)

def parse_conf():
    rows = []
    if not os.path.isfile(CONF):
        return rows
    for line in open(CONF, encoding="utf-8", errors="replace"):
        raw = line.rstrip("\\n")
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 5:
            continue
        rows.append({{
            "alias": parts[0],
            "ip_port": parts[1],
            "privkey": parts[2],
            "txid": parts[3],
            "vout": int(parts[4]),
            "raw": raw,
        }})
    return rows

def utxo_alive(txid, vout):
    try:
        detail = cli("gettxout", str(txid), str(int(vout)))
    except Exception:
        return None
    if not isinstance(detail, dict):
        return None
    if abs(float(detail.get("value") or 0) - COLLATERAL) > 1e-8:
        return None
    return {{
        "txid": str(txid),
        "vout": int(vout),
        "confirmations": int(detail.get("confirmations") or 0),
        "amount": float(detail.get("value") or 0),
    }}

def list_10k():
    rows = cli("listunspent", "1", "9999999") or []
    out = []
    for u in rows:
        if not isinstance(u, dict):
            continue
        if abs(float(u.get("amount") or 0) - COLLATERAL) > 1e-8:
            continue
        out.append({{
            "txid": str(u["txid"]),
            "vout": int(u["vout"]),
            "confirmations": int(u.get("confirmations") or 0),
            "address": u.get("address"),
            "amount": float(u.get("amount") or 0),
        }})
    return out

def lock_all_10k():
    utxos = list_10k()
    if not utxos:
        return 0
    locks = [{{"txid": u["txid"], "vout": u["vout"]}} for u in utxos]
    try:
        cli("lockunspent", "false", json.dumps(locks))
    except Exception as e:
        print("lock_err", e)
    return len(locks)

def unlock_all_locked():
    locked = cli("listlockunspent") or []
    if isinstance(locked, list) and locked:
        cli("lockunspent", "true", json.dumps(locked))
        return len(locked)
    return 0

def alias_for_host(host_id: str) -> str:
    alias = re.sub(r"[^a-zA-Z0-9]", "", (host_id or "").strip())[:16]
    return alias or (host_id or "host").replace("-", "")[:16]

conf = parse_conf()
print("conf_aliases", len(conf))

# Classify each conf row; force unique UTXOs (duplicates need new collateral).
seen_alive = set()
keep = []
need = []
for row in conf:
    alive = utxo_alive(row["txid"], row["vout"])
    key = (row["txid"], row["vout"])
    if alive and key not in seen_alive:
        seen_alive.add(key)
        keep.append({{**row, "utxo": alive, "action": "keep"}})
    else:
        reason = "spent" if not alive else "duplicate_utxo"
        need.append({{**row, "action": "replace", "reason": reason}})

print("keep", len(keep), "need_replace", len(need))
print("need_sample", [{{"alias": n["alias"], "reason": n["reason"]}} for n in need[:8]])

need_all = list(need)
if LIMIT > 0:
    need = need_all[:LIMIT]
    print("limited_need", len(need), "deferred", len(need_all) - len(need))

if not need:
    print("OK nothing to re-collateralize")
    sys.exit(0)

balance = float(cli("getbalance") or 0)
required = len(need) * COLLATERAL + max(10.0, len(need) * 0.5)
print("balance", balance, "required_approx", required)
if balance < required:
    print("FAIL insufficient balance", file=sys.stderr)
    sys.exit(1)

if DRY_RUN:
    print("DRY_RUN — would fund", len(need), "new collaterals and rewrite conf")
    sys.exit(0)

if not FUND:
    print("FAIL --no-fund set but funding required", file=sys.stderr)
    sys.exit(1)

unlock(spend=True, timeout=max(600, WAIT_MINUTES * 60))
locked_n = lock_all_10k()
print("locked_existing_10k", locked_n)

created = []
for i, row in enumerate(need):
    addr = cli("getnewaddress")
    txid = cli("sendtoaddress", str(addr), str(COLLATERAL))
    created.append({{"alias": row["alias"], "address": addr, "txid": txid, "privkey": row["privkey"], "ip_port": row.get("ip_port") or IP_PORT}})
    print(f"funded {{i+1}}/{{len(need)}} alias={{row['alias']}} txid={{txid}}")
    time.sleep(1.5)

# Wait for confirmations on created outs (vout usually 0 for self-send; scan listunspent)
deadline = time.time() + WAIT_MINUTES * 60
ready = {{}}
while time.time() < deadline:
    tenk = {{(u["txid"], u["vout"]): u for u in list_10k()}}
    ready = {{}}
    for c in created:
        # Prefer vout 0, else any matching txid
        hit = None
        for vout in range(0, 8):
            key = (c["txid"], vout)
            if key in tenk and tenk[key]["confirmations"] >= MIN_CONF:
                hit = tenk[key]
                break
        if hit is None:
            # unconfirmed still ok to track
            for vout in range(0, 8):
                key = (c["txid"], vout)
                if key in tenk:
                    hit = tenk[key]
                    break
        if hit and hit["confirmations"] >= MIN_CONF:
            ready[c["alias"]] = hit
    print(f"wait confirmed {{len(ready)}}/{{len(created)}} (min_conf={{MIN_CONF}})")
    if len(ready) >= len(created):
        break
    time.sleep(20)

if len(ready) < len(created):
    print("FAIL timed out waiting for confirmations; partial ready", len(ready), file=sys.stderr)
    print(json.dumps({{"ready": list(ready.keys()), "pending": [c['alias'] for c in created if c['alias'] not in ready]}}, indent=2))
    sys.exit(2)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
if os.path.isfile(CONF):
    shutil.copy2(CONF, CONF + f".bak-recollateral-{{ts}}")

# Rewrite conf: keep + replacements + deferred (unselected when --limit)
new_rows = []
for row in keep:
    new_rows.append({{
        "alias": row["alias"],
        "ip_port": row.get("ip_port") or IP_PORT,
        "privkey": row["privkey"],
        "txid": row["utxo"]["txid"],
        "vout": row["utxo"]["vout"],
    }})
replaced_aliases = set()
for c in created:
    u = ready[c["alias"]]
    new_rows.append({{
        "alias": c["alias"],
        "ip_port": c.get("ip_port") or IP_PORT,
        "privkey": c["privkey"],
        "txid": u["txid"],
        "vout": u["vout"],
        "address": c.get("address") or u.get("address"),
    }})
    replaced_aliases.add(c["alias"])
for row in need_all:
    if row["alias"] in replaced_aliases:
        continue
    # Preserve old (spent) line until a later run replaces it
    new_rows.append({{
        "alias": row["alias"],
        "ip_port": row.get("ip_port") or IP_PORT,
        "privkey": row["privkey"],
        "txid": row["txid"],
        "vout": row["vout"],
    }})

lines = [
    f"# Masternode config — re-collateralized {{ts}}\\n",
    "# Format: alias IP:port masternodeprivkey collateral_txid collateral_vout\\n",
]
for r in new_rows:
    lines.append(f"{{r['alias']}} {{r['ip_port']}} {{r['privkey']}} {{r['txid']}} {{r['vout']}}\\n")
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
print("wrote_conf", len(new_rows))

# Sync hosts registry by alias (only keep + newly funded)
try:
    doc = json.load(open(HOSTS_FILE, encoding="utf-8"))
except Exception:
    doc = {{"hosts": []}}
hosts = [h for h in (doc.get("hosts") or []) if isinstance(h, dict)]
sync_rows = [r for r in new_rows if r["alias"] in ({{x["alias"] for x in keep}} | replaced_aliases)]
by_alias = {{r["alias"]: r for r in sync_rows}}
updated = 0
for h in hosts:
    alias = alias_for_host(str(h.get("id") or ""))
    row = by_alias.get(alias)
    if not row:
        continue
    h["collateral_txid"] = row["txid"]
    h["collateral_vout"] = row["vout"]
    if row.get("address"):
        h["collateral_address"] = row["address"]
    h["broadcast_address"] = row.get("ip_port") or IP_PORT
    h["status"] = "active"
    h.pop("collateral_missing_at", None)
    h["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    h["notes"] = f"Re-collateralized {{ts}}"
    updated += 1
doc["hosts"] = hosts
doc["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(HOSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\\n")
print("hosts_updated", updated)

print("unlock_locked", unlock_all_locked())
print("restart_daemon")
subprocess.run(["systemctl", "restart", "masternoder2d"], check=False)
for i in range(48):
    time.sleep(5)
    try:
        h = cli("getblockcount")
        if isinstance(h, int) and h > 0:
            print("rpc_ready", h)
            break
    except Exception:
        pass
else:
    raise RuntimeError("daemon did not return after restart")

unlock(spend=False, timeout=0)  # staking unlock until restart
sys.path.insert(0, WEB)
from backend.services import mn2_masternode_service as mn
start_aliases = {{r["alias"] for r in keep}} | replaced_aliases
started_ok = 0
started_n = 0
for r in new_rows:
    if r["alias"] not in start_aliases:
        continue
    started_n += 1
    err = mn._start_masternode(r["alias"], r["privkey"])
    print("start", r["alias"], "OK" if not err else err)
    if not err:
        started_ok += 1

print("getmasternodecount", json.dumps(cli("getmasternodecount")))
print("refresh_collateral", mn.refresh_collateral_liveness(limit=500))
print("DONE started_ok", started_ok, "of", started_n, "conf_rows", len(new_rows))
PY
"""


def main() -> int:
    p = argparse.ArgumentParser(description="Re-collateralize spent MN2 fleet aliases")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="Max aliases to replace (0=all)")
    p.add_argument("--wait-minutes", type=int, default=25)
    p.add_argument("--no-fund", action="store_true")
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh, method, _ = connect_deploy_ssh(pw)
    print("auth", method)
    remote = build_remote(
        dry_run=args.dry_run,
        limit=args.limit,
        wait_minutes=args.wait_minutes,
        fund=not args.no_fund,
    )
    _, stdout, stderr = ssh.exec_command(remote, timeout=max(900, args.wait_minutes * 60 + 300))
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    ssh.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
