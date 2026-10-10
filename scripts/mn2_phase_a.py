#!/usr/bin/env python3
"""
MN2 wallet consolidation -- Phase A (catalog + reconcile).

WHAT THIS DOES
  Brings the scattered off-chain MN2 state into the app SQLite DB so it can be
  joined, audited and reconciled against the chain. It MOVES NO COINS and, by
  default, WRITES NOTHING (dry-run). Phases B/C/D (HD wallets, on-chain purchase
  settlement, legacy sweep) are separate and gated.

SOURCES (read-only)
  data/mn2_user_addresses.json   -> wallets + addresses  ({primary, wallet_type, addresses[]})
  logs/unified_points/<uid>.json -> balances             (systems.mn2_balance / mn2_staked)
  data/mn2_ledger.json           -> transactions         ({entries:[{user_id,type,amount,txid,address,created_at,metadata}]})
  masternoder2-cli (chain)       -> reconciliation       (getbalance / listaddressgroupings / listunspent)

TARGET (same SQLite DB, WAL)
  mn2_wallets, mn2_addresses, mn2_address_quota, mn2_transactions,
  mn2_reconciliation_log  +  ALTER shop_purchases ADD (mn2_txid, mn2_from_address,
  mn2_to_address, onchain)

USAGE (run from /var/www/html with the app venv)
  .venv/bin/python scripts/mn2_phase_a.py report            # read-only summary + reconcile (DEFAULT)
  .venv/bin/python scripts/mn2_phase_a.py schema            # idempotent DDL only (no data)
  .venv/bin/python scripts/mn2_phase_a.py migrate --yes     # catalog backfill (needs schema first)
  .venv/bin/python scripts/mn2_phase_a.py reconcile         # chain-vs-DB report only
  add --db /abs/path.sqlite to override DATABASE_URL resolution

SAFETY
  * No private keys are read, printed or stored. No dumpprivkey. No coin movement.
  * report/reconcile are strictly read-only. schema is additive/idempotent.
  * migrate requires --yes, runs in a single transaction, INSERT OR IGNORE (re-runnable).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /var/www/html
MN2_CLI = os.environ.get("MN2_CLI", "/opt/masternoder2d/masternoder2-cli")
MN2_DATADIR = os.environ.get("MN2_DATADIR", os.path.join(REPO, "config"))
ADDR_FILE = os.path.join(REPO, "data", "mn2_user_addresses.json")
LEDGER_FILE = os.path.join(REPO, "data", "mn2_ledger.json")
POINTS_DIR = os.path.join(REPO, "logs", "unified_points")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def eprint(*a):
    print(*a, file=sys.stderr)


# --------------------------------------------------------------------------- #
# config / db-path resolution (mirror src/app/__init__.py:156-169)
# --------------------------------------------------------------------------- #
def load_dotenv() -> str:
    env = os.path.join(REPO, ".env")
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(env)
        return "python-dotenv"
    except Exception:
        pass
    # manual parse (values never printed)
    try:
        with open(env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        return "manual"
    except Exception as e:
        return f"none({e})"


def resolve_db_path(override: str | None) -> tuple[str, str, bool]:
    """Return (abs_path, url, existed)."""
    if override:
        p = os.path.abspath(override)
        return p, f"sqlite:///{p}", os.path.exists(p)
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or ""
    if not url.startswith("sqlite"):
        return "", url, False
    path = url.split("sqlite:///", 1)[-1] if "sqlite:///" in url else url.split("sqlite://", 1)[-1]
    path = path.split("?", 1)[0]  # strip any ?mode=/query params
    if path.startswith("/"):
        pass  # absolute (sqlite:////abs/path)
    else:
        path = os.path.abspath(os.path.join(REPO, path.replace("/", os.sep)))
    return path, url, os.path.exists(path)


def connect(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(path, timeout=30)
    c.row_factory = sqlite3.Row
    return c


# --------------------------------------------------------------------------- #
# chain reads via CLI (best-effort; never fatal)
# --------------------------------------------------------------------------- #
def mn2_cli(method: str, *params):
    if not os.path.exists(MN2_CLI):
        return None, f"cli missing: {MN2_CLI}"
    cmd = [MN2_CLI, f"-datadir={MN2_DATADIR}", method, *[str(p) for p in params]]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except Exception as e:
        return None, f"cli error: {e}"
    if out.returncode != 0:
        return None, (out.stderr or out.stdout).strip()[:200]
    try:
        return json.loads(out.stdout), None
    except Exception:
        # some methods (getbalance) print a bare number
        try:
            return float(out.stdout.strip()), None
        except Exception:
            return out.stdout.strip(), None


def chain_snapshot() -> dict:
    snap = {"ok": False}
    bal, err = mn2_cli("getbalance")
    if err:
        wi, err2 = mn2_cli("getwalletinfo")
        bal = (wi or {}).get("balance") if isinstance(wi, dict) else None
        if bal is None:
            snap["balance_error"] = err or err2
    snap["node_balance"] = float(bal) if isinstance(bal, (int, float)) else None

    groupings, err = mn2_cli("listaddressgroupings")
    addrs, per_addr = set(), {}
    if isinstance(groupings, list):
        for group in groupings:
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, list) and item and isinstance(item[0], str):
                        addrs.add(item[0])
                        try:
                            per_addr[item[0]] = float(item[1]) if len(item) > 1 else 0.0
                        except Exception:
                            per_addr[item[0]] = 0.0
    snap["node_addr_count"] = len(addrs)
    snap["node_addrs"] = addrs
    snap["node_per_addr"] = per_addr
    if err:
        snap["groupings_error"] = err

    utxos, err = mn2_cli("listunspent", 0, 9999999)
    if isinstance(utxos, list):
        snap["utxo_count"] = len(utxos)
        snap["utxo_sum"] = round(sum(float(u.get("amount", 0)) for u in utxos), 8)
    elif err:
        snap["listunspent_error"] = err
    snap["ok"] = snap.get("node_balance") is not None or snap.get("node_addr_count")
    return snap


# --------------------------------------------------------------------------- #
# source readers
# --------------------------------------------------------------------------- #
def entity_kind(key: str) -> str:
    k = str(key)
    if k.startswith("agent:"):
        return "agent"
    if k.startswith("pool_"):
        return "pool"
    return "user"


def read_addresses() -> list[dict]:
    """-> [{user_id, entity_kind, wallet_type, primary, addresses:[str,...]}]"""
    out = []
    if not os.path.exists(ADDR_FILE):
        return out
    raw = json.load(open(ADDR_FILE, "r", encoding="utf-8"))
    if not isinstance(raw, dict):
        return out
    for uid, v in raw.items():
        rec = {"user_id": str(uid), "entity_kind": entity_kind(uid),
               "wallet_type": None, "primary": None, "addresses": []}
        if isinstance(v, str):
            rec["primary"] = v
            rec["addresses"] = [v]
        elif isinstance(v, dict):
            rec["wallet_type"] = v.get("wallet_type")
            rec["primary"] = v.get("primary")
            addrs = v.get("addresses") or []
            norm = []
            for a in addrs:
                if isinstance(a, str):
                    norm.append(a)
                elif isinstance(a, dict):
                    norm.append(a.get("address") or a.get("addr") or a.get("primary"))
            rec["addresses"] = [a for a in norm if a]
            if rec["primary"] and rec["primary"] not in rec["addresses"]:
                rec["addresses"].insert(0, rec["primary"])
        out.append(rec)
    return out


def read_balances() -> dict:
    """-> {user_id: {mn2_balance, mn2_staked}} from logs/unified_points/*.json"""
    bals: dict[str, dict] = {}
    for f in glob.glob(os.path.join(POINTS_DIR, "*.json")):
        uid = os.path.splitext(os.path.basename(f))[0]
        try:
            j = json.load(open(f, "r", encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(j, dict):
            continue
        sysd = j.get("systems") if isinstance(j.get("systems"), dict) else {}
        mb = float(sysd.get("mn2_balance", j.get("mn2_balance", 0)) or 0)
        ms = float(sysd.get("mn2_staked", j.get("mn2_staked", 0)) or 0)
        if mb or ms:
            bals[uid] = {"mn2_balance": round(mb, 8), "mn2_staked": round(ms, 8)}
    return bals


LEDGER_IN = {"deposit", "staking_reward", "micro_tx_reward", "treasury_deposit",
             "aggregator_mn2_earn", "generator_mn2_earn", "reward", "earn"}
LEDGER_OUT = {"shop_payment", "masternode_hosting_payment", "withdrawal", "purchase", "fee"}


def ledger_direction(t: str) -> str:
    t = (t or "").lower()
    if t in LEDGER_IN:
        return "in"
    if t in LEDGER_OUT:
        return "out"
    if t == "stake":
        return "internal"
    return "unknown"


def read_ledger() -> list[dict]:
    if not os.path.exists(LEDGER_FILE):
        return []
    raw = json.load(open(LEDGER_FILE, "r", encoding="utf-8"))
    entries = raw.get("entries") if isinstance(raw, dict) else raw
    return entries if isinstance(entries, list) else []


# --------------------------------------------------------------------------- #
# schema (idempotent, additive)
# --------------------------------------------------------------------------- #
DDL = [
    """CREATE TABLE IF NOT EXISTS mn2_wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        entity_kind TEXT NOT NULL DEFAULT 'user',
        wallet_kind TEXT NOT NULL DEFAULT 'custodial',
        account_name TEXT,
        wallet_type TEXT,
        primary_address TEXT,
        addr_count INTEGER NOT NULL DEFAULT 0,
        mn2_balance REAL NOT NULL DEFAULT 0,
        mn2_staked REAL NOT NULL DEFAULT 0,
        hd_xpub TEXT, hd_seed_enc BLOB, hd_seed_nonce BLOB, hd_path_prefix TEXT,
        addr_index_next INTEGER NOT NULL DEFAULT 0, key_enc_alg TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        last_reconciled_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS mn2_addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_id INTEGER REFERENCES mn2_wallets(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        address TEXT NOT NULL UNIQUE,
        derivation_path TEXT,
        is_primary INTEGER NOT NULL DEFAULT 0,
        is_change INTEGER NOT NULL DEFAULT 0,
        wallet_type TEXT,
        imported_to_node INTEGER,
        node_balance REAL NOT NULL DEFAULT 0,
        received_total REAL NOT NULL DEFAULT 0,
        tx_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )""",
    "CREATE INDEX IF NOT EXISTS ix_mn2_addresses_user ON mn2_addresses(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_mn2_addresses_wallet ON mn2_addresses(wallet_id)",
    """CREATE TABLE IF NOT EXISTS mn2_address_quota (
        user_id TEXT NOT NULL,
        day TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, day)
    )""",
    """CREATE TABLE IF NOT EXISTS mn2_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dedup_key TEXT NOT NULL UNIQUE,
        txid TEXT, vout INTEGER,
        blockhash TEXT, block_height INTEGER, confirmations INTEGER,
        direction TEXT, category TEXT,
        user_id TEXT, from_user_id TEXT, to_user_id TEXT,
        from_address TEXT, to_address TEXT, address TEXT,
        amount REAL, fee REAL, status TEXT,
        ref_type TEXT, ref_id TEXT,
        ledger_created_at TEXT, metadata TEXT,
        imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )""",
    "CREATE INDEX IF NOT EXISTS ix_mn2_tx_user ON mn2_transactions(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_mn2_tx_txid ON mn2_transactions(txid)",
    "CREATE INDEX IF NOT EXISTS ix_mn2_tx_cat ON mn2_transactions(category)",
    """CREATE TABLE IF NOT EXISTS mn2_reconciliation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        scope TEXT, mode TEXT,
        node_balance REAL, db_balance_sum REAL, delta REAL,
        node_addr_count INTEGER, db_addr_count INTEGER,
        ledger_entries INTEGER, tx_rows INTEGER,
        details TEXT
    )""",
]

SHOP_COLS = [("mn2_txid", "TEXT"), ("mn2_from_address", "TEXT"),
             ("mn2_to_address", "TEXT"), ("onchain", "INTEGER NOT NULL DEFAULT 0")]


def apply_schema(path: str) -> dict:
    res = {"tables_created": 0, "shop_cols_added": [], "journal_mode": None}
    c = connect(path)
    try:
        c.execute("PRAGMA journal_mode=WAL")
        res["journal_mode"] = c.execute("PRAGMA journal_mode").fetchone()[0]
        before = {r[0] for r in c.execute(
            "select name from sqlite_master where type='table' and name like 'mn2_%'")}
        for stmt in DDL:
            c.execute(stmt)
        after = {r[0] for r in c.execute(
            "select name from sqlite_master where type='table' and name like 'mn2_%'")}
        res["tables_created"] = len(after - before)
        res["mn2_tables"] = sorted(after)
        # shop_purchases additive ALTERs (guarded)
        try:
            have = {r[1] for r in c.execute("PRAGMA table_info(shop_purchases)")}
            if have:
                for col, typ in SHOP_COLS:
                    if col not in have:
                        c.execute(f"ALTER TABLE shop_purchases ADD COLUMN {col} {typ}")
                        res["shop_cols_added"].append(col)
            else:
                res["shop_cols_added"] = ["(shop_purchases table not found)"]
        except Exception as e:
            res["shop_cols_added"] = [f"ERR {e}"]
        c.commit()
    finally:
        c.close()
    return res


# --------------------------------------------------------------------------- #
# catalog (dry-run compute + optional commit)
# --------------------------------------------------------------------------- #
def build_catalog() -> dict:
    addrs = read_addresses()
    bals = read_balances()
    ledger = read_ledger()
    wallets, addresses, txs = [], [], []
    seen_addr = set()
    for rec in addrs:
        uid = rec["user_id"]
        b = bals.get(uid, {})
        wallets.append({
            "user_id": uid, "entity_kind": rec["entity_kind"],
            "wallet_kind": "custodial", "wallet_type": rec["wallet_type"],
            "primary_address": rec["primary"], "addr_count": len(rec["addresses"]),
            "mn2_balance": b.get("mn2_balance", 0.0), "mn2_staked": b.get("mn2_staked", 0.0),
        })
        for a in rec["addresses"]:
            if a in seen_addr:
                continue
            seen_addr.add(a)
            addresses.append({
                "user_id": uid, "address": a,
                "is_primary": 1 if a == rec["primary"] else 0,
                "wallet_type": rec["wallet_type"], "derivation_path": None,
            })
    # balances for users that have a balance but no address yet
    for uid, b in bals.items():
        if not any(w["user_id"] == uid for w in wallets):
            wallets.append({
                "user_id": uid, "entity_kind": entity_kind(uid), "wallet_kind": "custodial",
                "wallet_type": None, "primary_address": None, "addr_count": 0,
                "mn2_balance": b.get("mn2_balance", 0.0), "mn2_staked": b.get("mn2_staked", 0.0),
            })
    for e in ledger:
        if not isinstance(e, dict):
            continue
        typ = e.get("type")
        amt = e.get("amount")
        try:
            amt = round(float(amt), 8)
        except Exception:
            amt = None
        txid_v = e.get("txid") or ""
        meta = e.get("metadata")
        meta_h = (hashlib.sha1(json.dumps(meta, sort_keys=True, default=str).encode()).hexdigest()[:12]
                  if meta is not None else "")
        key_src = "|".join([str(txid_v), str(typ or ""), str(e.get("user_id") or ""),
                            str(e.get("address") or ""), (f"{amt:.8f}" if amt is not None else ""),
                            str(e.get("created_at") or ""), meta_h])
        txs.append({
            "dedup_key": hashlib.sha1(key_src.encode("utf-8")).hexdigest(),
            "txid": e.get("txid") or None, "vout": e.get("vout"),
            "direction": ledger_direction(typ), "category": typ,
            "user_id": e.get("user_id"), "address": e.get("address"),
            "to_address": e.get("address"), "amount": amt,
            "status": "confirmed" if e.get("txid") else "pending",
            "ledger_created_at": e.get("created_at"),
            "metadata": json.dumps(meta) if meta is not None else None,
        })
    return {"wallets": wallets, "addresses": addresses, "txs": txs,
            "balances": bals, "ledger_count": len(ledger)}


def commit_catalog(path: str, cat: dict, chain: dict) -> dict:
    node_addrs = chain.get("node_addrs", set()) or set()
    per_addr = chain.get("node_per_addr", {}) or {}
    c = connect(path)
    res = {}
    try:
        c.execute("BEGIN")
        w_ins = 0
        for w in cat["wallets"]:
            cur = c.execute(
                """INSERT INTO mn2_wallets
                   (user_id, entity_kind, wallet_kind, wallet_type, primary_address,
                    addr_count, mn2_balance, mn2_staked, last_reconciled_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     entity_kind=excluded.entity_kind, wallet_type=excluded.wallet_type,
                     primary_address=excluded.primary_address, addr_count=excluded.addr_count,
                     mn2_balance=excluded.mn2_balance, mn2_staked=excluded.mn2_staked,
                     last_reconciled_at=excluded.last_reconciled_at""",
                (w["user_id"], w["entity_kind"], w["wallet_kind"], w["wallet_type"],
                 w["primary_address"], w["addr_count"], w["mn2_balance"], w["mn2_staked"], now_iso()))
            w_ins += 1 if cur.rowcount > 0 else 0
        a_ins = 0
        for a in cat["addresses"]:
            wid = c.execute("select id from mn2_wallets where user_id=?", (a["user_id"],)).fetchone()
            imported = 1 if a["address"] in node_addrs else (0 if node_addrs else None)
            nb = per_addr.get(a["address"], 0.0)
            cur = c.execute(
                """INSERT INTO mn2_addresses
                   (wallet_id, user_id, address, derivation_path, is_primary, is_change,
                    wallet_type, imported_to_node, node_balance)
                   VALUES (?,?,?,?,?,0,?,?,?)
                   ON CONFLICT(address) DO UPDATE SET
                     wallet_id=excluded.wallet_id, user_id=excluded.user_id,
                     is_primary=excluded.is_primary, wallet_type=excluded.wallet_type,
                     imported_to_node=excluded.imported_to_node, node_balance=excluded.node_balance""",
                (wid[0] if wid else None, a["user_id"], a["address"], a["derivation_path"],
                 a["is_primary"], a["wallet_type"], imported, nb))
            a_ins += 1 if cur.rowcount > 0 else 0
        t_ins = 0
        for t in cat["txs"]:
            cur = c.execute(
                """INSERT OR IGNORE INTO mn2_transactions
                   (dedup_key, txid, vout, direction, category, user_id, address, to_address,
                    amount, status, ledger_created_at, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (t["dedup_key"], t["txid"], t["vout"], t["direction"], t["category"], t["user_id"],
                 t["address"], t["to_address"], t["amount"], t["status"],
                 t["ledger_created_at"], t["metadata"]))
            t_ins += cur.rowcount
        c.execute("COMMIT")
        res = {"wallets_upserted": w_ins, "addresses_upserted": a_ins, "tx_rows_inserted": t_ins}
    except Exception as e:
        c.execute("ROLLBACK")
        res = {"error": str(e)}
    finally:
        c.close()
    return res


# --------------------------------------------------------------------------- #
# reconciliation report
# --------------------------------------------------------------------------- #
def db_totals(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    c = connect(path)
    try:
        t = {}
        for name, q in [
            ("wallets", "select count(*) from mn2_wallets"),
            ("addresses", "select count(*) from mn2_addresses"),
            ("txs", "select count(*) from mn2_transactions"),
            ("bal_sum", "select round(coalesce(sum(mn2_balance),0),8) from mn2_wallets"),
            ("staked_sum", "select round(coalesce(sum(mn2_staked),0),8) from mn2_wallets"),
            ("tx_with_txid", "select count(*) from mn2_transactions where txid is not null"),
        ]:
            try:
                t[name] = c.execute(q).fetchone()[0]
            except Exception:
                t[name] = None
        return t
    finally:
        c.close()


def print_report(path: str, existed: bool, cat: dict, chain: dict, dbt: dict):
    line = "-" * 66
    print(line)
    print("MN2 PHASE A -- READ-ONLY REPORT", now_iso())
    print(line)
    print(f"DB path        : {path}")
    print(f"DB exists      : {existed}")
    print(f"mn2 tables     : {dbt.get('wallets') is not None}")
    print()
    print("[SOURCES]")
    print(f"  user_addresses.json : {len(cat['wallets'])} wallet entities "
          f"({sum(1 for w in cat['wallets'] if w['entity_kind']=='user')} user, "
          f"{sum(1 for w in cat['wallets'] if w['entity_kind']=='agent')} agent), "
          f"{len(cat['addresses'])} distinct addresses")
    print(f"  unified_points files: {len(cat['balances'])} users with mn2_balance>0")
    print(f"  mn2_ledger.json     : {cat['ledger_count']} entries -> {len(cat['txs'])} tx rows "
          f"({sum(1 for t in cat['txs'] if t['txid'])} with txid)")
    tot_bal = round(sum(w['mn2_balance'] for w in cat['wallets']), 8)
    tot_stk = round(sum(w['mn2_staked'] for w in cat['wallets']), 8)
    print(f"  ledger bal sum      : mn2_balance={tot_bal}  mn2_staked={tot_stk}")
    print()
    print("[CHAIN] (via masternoder2-cli)")
    if chain.get("ok"):
        print(f"  node getbalance     : {chain.get('node_balance')}")
        print(f"  node addresses      : {chain.get('node_addr_count')} (listaddressgroupings)")
        print(f"  node UTXOs          : {chain.get('utxo_count')} sum={chain.get('utxo_sum')}")
    else:
        print(f"  chain unavailable   : {chain.get('balance_error') or chain.get('groupings_error')}")
    print()
    print("[RECONCILE]")
    nb = chain.get("node_balance")
    if isinstance(nb, (int, float)):
        delta = round(nb - tot_bal, 8)
        flag = "OK (claims <= node)" if tot_bal <= nb else "!! INSOLVENT: claims > node balance"
        print(f"  node balance {nb}  vs  user claims {tot_bal}  -> unallocated {delta}  [{flag}]")
    if chain.get("node_addrs"):
        cat_set = {a['address'] for a in cat['addresses']}
        in_node = len(cat_set & chain['node_addrs'])
        print(f"  cataloged addresses owned by node (ismine): {in_node}/{len(cat_set)}")
        missing = list(cat_set - chain['node_addrs'])[:5]
        if missing:
            print(f"    sample NOT in node groupings: {missing}")
    if dbt.get("wallets") is not None:
        print(f"  DB rows: wallets={dbt.get('wallets')} addresses={dbt.get('addresses')} "
              f"txs={dbt.get('txs')} (txid={dbt.get('tx_with_txid')}) "
              f"bal_sum={dbt.get('bal_sum')} staked_sum={dbt.get('staked_sum')}")
    print(line)


def write_recon_log(path: str, mode: str, cat: dict, chain: dict, dbt: dict):
    if not os.path.exists(path):
        return
    try:
        c = connect(path)
        tot_bal = round(sum(w['mn2_balance'] for w in cat['wallets']), 8)
        nb = chain.get("node_balance")
        c.execute(
            """INSERT INTO mn2_reconciliation_log
               (scope, mode, node_balance, db_balance_sum, delta,
                node_addr_count, db_addr_count, ledger_entries, tx_rows, details)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("phase_a", mode, nb, dbt.get("bal_sum"),
             round(nb - dbt.get("bal_sum", 0), 8) if isinstance(nb, (int, float)) and dbt.get("bal_sum") is not None else None,
             chain.get("node_addr_count"), dbt.get("addresses"),
             cat["ledger_count"], dbt.get("txs"),
             json.dumps({"source_wallets": len(cat["wallets"]), "source_addrs": len(cat["addresses"]),
                         "claims_sum": tot_bal, "utxo_sum": chain.get("utxo_sum")})[:4000]))
        c.commit()
        c.close()
    except Exception as e:
        eprint("recon log write failed:", e)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_report(args):
    loader = load_dotenv()
    path, url, existed = resolve_db_path(args.db)
    print(f"# .env loader: {loader}")
    cat = build_catalog()
    chain = chain_snapshot()
    dbt = db_totals(path) if existed else {}
    print_report(path, existed, cat, chain, dbt)
    return 0


def cmd_schema(args):
    load_dotenv()
    path, url, existed = resolve_db_path(args.db)
    if not path:
        eprint("could not resolve DB path; pass --db /abs/path.sqlite")
        return 2
    if not existed and not args.allow_create:
        eprint(f"DB not found at {path}; refusing to create. Use --db or --allow-create.")
        return 2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    res = apply_schema(path)
    print("SCHEMA applied ->", path)
    print(json.dumps(res, indent=2, default=str))
    return 0


def cmd_migrate(args):
    load_dotenv()
    path, url, existed = resolve_db_path(args.db)
    if not existed:
        eprint(f"DB not found at {path}. Run 'schema' first / check --db.")
        return 2
    if not args.yes:
        eprint("refusing to migrate without --yes (this writes rows; still no coin movement).")
        return 2
    # ensure schema
    apply_schema(path)
    cat = build_catalog()
    chain = chain_snapshot()
    print("Pre-migrate DB totals:", db_totals(path))
    res = commit_catalog(path, cat, chain)
    print("MIGRATE result:", json.dumps(res, indent=2, default=str))
    dbt = db_totals(path)
    print_report(path, True, cat, chain, dbt)
    write_recon_log(path, "commit", cat, chain, dbt)
    return 0 if "error" not in res else 1


def cmd_reconcile(args):
    load_dotenv()
    path, url, existed = resolve_db_path(args.db)
    cat = build_catalog()
    chain = chain_snapshot()
    dbt = db_totals(path) if existed else {}
    print_report(path, existed, cat, chain, dbt)
    if existed and dbt.get("wallets") is not None:
        write_recon_log(path, "reconcile", cat, chain, dbt)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="MN2 Phase A migration (catalog + reconcile; no coin movement)")
    ap.add_argument("command", nargs="?", default="report",
                    choices=["report", "schema", "migrate", "reconcile"])
    ap.add_argument("--db", help="absolute path to app SQLite DB (overrides DATABASE_URL)")
    ap.add_argument("--yes", action="store_true", help="required for 'migrate'")
    ap.add_argument("--allow-create", action="store_true", help="allow 'schema' to create a missing DB file")
    args = ap.parse_args(argv)
    os.chdir(REPO)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "schema":
        return cmd_schema(args)
    if args.command == "migrate":
        return cmd_migrate(args)
    if args.command == "reconcile":
        return cmd_reconcile(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
