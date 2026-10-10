#!/usr/bin/env python3
"""Phase B backfill -- give MN2 a first-class, reconcilable home in the DB.

REAL data sources (discovered by probe on the server, /var/www/html/data):
  - mn2_ledger.json           : {entries:[{user_id,type,amount,txid,address,created_at,metadata}]}  (~1917)
  - mn2_order_payments.json   : {orders:[{payment_ref,user_id,address,amount_mn2,item_id,...}]}      (~78)
  - mn2_masternode_hosts.json : {hosts:[{id,collateral_address,collateral_txid,broadcast_address,owner_user_id,...}]}
  - mn2_treasury_addresses.json, mn2_user_addresses.json, mn2_address_book.json (if present)

Populates: mn2_wallets, mn2_addresses, mn2_address_quota, mn2_transactions,
mn2_reconciliation_log; links shop_purchases -> MN2 via payment_ref.

SAFE: additive + idempotent (content-hash dedupe). Never deletes. On shop_purchases
it only FILLS empty mn2_txid/mn2_address and flips onchain 0->1; never overwrites.

  probe (no writes):  python 002_backfill_mn2.py --db instance/database.db --probe
  real run         :  python 002_backfill_mn2.py --db instance/database.db
"""
import argparse
import glob
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mn2_addr import validate_address  # noqa: E402

IN_TYPES = {"deposit", "receive", "received", "in", "incoming", "reward",
            "staking_reward", "stake_reward", "airdrop", "refund", "sale_proceeds",
            "payout_received", "credit"}
OUT_TYPES = {"withdrawal", "withdraw", "send", "sent", "out", "outgoing", "purchase",
             "fee", "payment", "stake", "burn", "debit", "transfer_out"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_data_dir(explicit):
    cands = []
    if explicit:
        cands.append(explicit)
    cands += [os.path.join(os.getcwd(), "data"), os.path.join(HERE, "..", "data")]
    for c in cands:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return os.path.abspath(cands[0])


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to read {path}: {exc}")
        return None


def as_list(obj, key):
    """Pull a list out of {key:[...]} or a bare list."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        v = obj.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return list(v.values())
    return []


def direction_for(type_str, amount):
    t = (type_str or "").lower()
    if t in IN_TYPES:
        return "in"
    if t in OUT_TYPES:
        return "out"
    if any(k in t for k in ("dep", "receiv", "reward", "credit", "incoming", "airdrop")):
        return "in"
    try:
        if amount is not None and float(amount) < 0:
            return "out"
    except (TypeError, ValueError):
        pass
    return "out"


def entry_hash(*parts) -> str:
    return hashlib.sha1("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# DB upserts (idempotent)
# ---------------------------------------------------------------------------
def upsert_wallet(conn, user_id, account_name=None, kind="custodial", source="backfill"):
    if not user_id:
        return None
    conn.execute(
        """INSERT INTO mn2_wallets (user_id, wallet_kind, account_name, source, created_at, updated_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             account_name = COALESCE(excluded.account_name, mn2_wallets.account_name),
             updated_at   = excluded.updated_at""",
        (str(user_id), kind, account_name, source, utcnow(), utcnow()),
    )
    return conn.execute("SELECT id FROM mn2_wallets WHERE user_id=?", (str(user_id),)).fetchone()[0]


def upsert_address(conn, address, wallet_id, user_id, label=None, balance=0.0,
                   account_name=None, source="ledger"):
    if not address:
        return None
    valid = 1 if validate_address(address) else 0
    conn.execute(
        """INSERT INTO mn2_addresses
             (address, wallet_id, user_id, account_name, label, is_valid, balance,
              first_seen, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(address) DO UPDATE SET
             wallet_id = COALESCE(mn2_addresses.wallet_id, excluded.wallet_id),
             balance   = CASE WHEN excluded.balance > 0 THEN excluded.balance ELSE mn2_addresses.balance END,
             is_valid  = excluded.is_valid""",
        (address, wallet_id, str(user_id) if user_id else None, account_name, label,
         valid, balance or 0.0, utcnow(), source, utcnow()),
    )
    return valid


def insert_tx(conn, *, dedupe_key, txid, direction, address, user_id, amount,
              kind, status, ref_type, ref_id, vout=None, fee=None, raw=None,
              created_at=None):
    """Insert a ledger tx once per dedupe_key (stored in ref_id when no natural id)."""
    exists = conn.execute(
        "SELECT 1 FROM mn2_transactions WHERE ref_type=? AND ref_id=? LIMIT 1",
        (ref_type, str(ref_id)),
    ).fetchone()
    if exists:
        return False
    conn.execute(
        """INSERT INTO mn2_transactions
             (txid, vout, direction, address, user_id, amount, fee, confirmations,
              status, kind, ref_type, ref_id, raw_json, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (txid or "", vout, direction, address, str(user_id) if user_id else None,
         float(amount or 0), fee, 0, status, kind, ref_type, str(ref_id),
         json.dumps(raw) if raw is not None else None, created_at or utcnow()),
    )
    return True


def log_recon(conn, scope, entity_id, db_value, chain_value, status, detail=""):
    drift = None
    if db_value is not None and chain_value is not None:
        drift = round((db_value or 0) - (chain_value or 0), 8)
    conn.execute(
        """INSERT INTO mn2_reconciliation_log
             (run_at, scope, entity_id, db_value, chain_value, drift, status, detail)
           VALUES (?,?,?,?,?,?,?,?)""",
        (utcnow(), scope, entity_id, db_value, chain_value, drift, status, detail),
    )


def refresh_wallet_counts(conn):
    conn.execute(
        """UPDATE mn2_wallets SET address_count =
             (SELECT COUNT(*) FROM mn2_addresses a WHERE a.wallet_id = mn2_wallets.id)"""
    )


def table_exists(conn, t):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None


def cols_of(conn, t):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}


# ---------------------------------------------------------------------------
# Source processors
# ---------------------------------------------------------------------------
def proc_ledger(conn, data, stats):
    entries = as_list(data, "entries")
    for e in entries:
        if not isinstance(e, dict):
            continue
        uid = e.get("user_id")
        addr = e.get("address")
        txid = e.get("txid") or ""
        amount = e.get("amount")
        etype = e.get("type")
        created = e.get("created_at")
        wid = upsert_wallet(conn, uid, source="ledger")
        if addr and wid:
            upsert_address(conn, addr, wid, uid, label=etype, source="ledger")
        key = entry_hash(uid, etype, amount, txid, addr, created)
        inserted = insert_tx(
            conn, dedupe_key=key, txid=txid,
            direction=direction_for(etype, amount), address=addr, user_id=uid,
            amount=amount, kind=etype, status=("confirmed" if txid else "pending"),
            ref_type="mn2_ledger", ref_id=key, raw=e, created_at=created,
        )
        stats["ledger"] += 1
        if inserted:
            stats["ledger_tx"] += 1


def proc_order_payments(conn, data, stats, purchase_index):
    orders = as_list(data, "orders")
    for o in orders:
        if not isinstance(o, dict):
            continue
        uid = o.get("user_id")
        addr = o.get("address")
        amount = o.get("amount_mn2", o.get("amount"))
        pref = o.get("payment_ref")
        txid = o.get("txid") or o.get("mn2_txid") or ""
        wid = upsert_wallet(conn, uid, source="order_payment")
        if addr and wid:
            upsert_address(conn, addr, wid, uid, label="order_payment", source="order_payment")
        key = pref or entry_hash(uid, addr, amount, o.get("item_id"), txid)
        inserted = insert_tx(
            conn, dedupe_key=key, txid=txid, direction="out", address=addr,
            user_id=uid, amount=amount, kind="purchase",
            status=("confirmed" if txid else "pending"),
            ref_type="order_payment", ref_id=key, raw=o,
        )
        stats["order_payments"] += 1
        if inserted:
            stats["order_tx"] += 1
        if not txid:
            if not conn.execute(
                "SELECT 1 FROM mn2_reconciliation_log WHERE scope='tx' AND entity_id=? AND status='mismatch' LIMIT 1",
                (f"order_payment:{key}",),
            ).fetchone():
                log_recon(conn, "tx", f"order_payment:{key}", amount, None,
                          "mismatch", "MN2 order payment recorded but no txid yet")
        # link shop_purchases by payment_ref
        if pref and pref in purchase_index:
            _link_purchase(conn, purchase_index[pref], addr, txid, stats)


def _link_purchase(conn, pid, addr, txid, stats):
    cols = cols_of(conn, "shop_purchases")
    if "mn2_address" in cols and addr:
        conn.execute("UPDATE shop_purchases SET mn2_address=COALESCE(NULLIF(mn2_address,''),?) WHERE id=?",
                     (addr, pid))
    if "mn2_txid" in cols and txid:
        conn.execute("UPDATE shop_purchases SET mn2_txid=COALESCE(NULLIF(mn2_txid,''),?) WHERE id=?",
                     (txid, pid))
    if "onchain" in cols:
        conn.execute("UPDATE shop_purchases SET onchain=1 WHERE id=?", (pid,))
    stats["purchases_linked"] += 1


def proc_masternode_hosts(conn, data, stats):
    hosts = as_list(data, "hosts")
    for h in hosts:
        if not isinstance(h, dict):
            continue
        uid = h.get("owner_user_id")
        wid = upsert_wallet(conn, uid, source="masternode")
        for field, label in (("collateral_address", "masternode_collateral"),
                             ("broadcast_address", "masternode_broadcast")):
            a = h.get(field)
            if a and wid:
                upsert_address(conn, a, wid, uid, label=label, source="masternode")
        ctx = h.get("collateral_txid")
        if ctx:
            insert_tx(conn, dedupe_key=h.get("id"), txid=ctx, direction="out",
                      address=h.get("collateral_address"), user_id=uid,
                      amount=h.get("collateral_mn2", 0), kind="masternode",
                      status="confirmed", ref_type="masternode_host",
                      ref_id=h.get("id"), vout=h.get("collateral_vout"), raw=h)
        stats["masternode_hosts"] += 1


def proc_treasury(conn, data, stats):
    addrs = []
    if isinstance(data, dict):
        for k in ("addresses", "treasury", "items"):
            if isinstance(data.get(k), list):
                addrs = data[k]
                break
        if not addrs:
            addrs = list(data.values())
    elif isinstance(data, list):
        addrs = data
    wid = upsert_wallet(conn, "__treasury__", kind="custodial", source="treasury")
    for a in addrs:
        addr = a if isinstance(a, str) else (a.get("address") if isinstance(a, dict) else None)
        label = a.get("label") if isinstance(a, dict) else None
        if addr and wid:
            upsert_address(conn, addr, wid, "__treasury__", label=label or "treasury",
                           source="treasury")
            stats["treasury_addresses"] += 1


def proc_user_addresses(conn, data, stats):
    """mn2_user_addresses.json / mn2_address_book.json: {user: addr|[addrs]|{...}}."""
    if not isinstance(data, dict):
        return
    for uid, val in data.items():
        addrs = []
        if isinstance(val, str):
            addrs = [val]
        elif isinstance(val, list):
            addrs = [x if isinstance(x, str) else (x.get("address") if isinstance(x, dict) else None) for x in val]
        elif isinstance(val, dict):
            inner = val.get("addresses") or val.get("address") or []
            if isinstance(inner, str):
                inner = [inner]
            addrs = [x if isinstance(x, str) else (x.get("address") if isinstance(x, dict) else None) for x in inner]
        wid = upsert_wallet(conn, uid, source="user_addresses")
        for a in addrs:
            if a and wid:
                upsert_address(conn, a, wid, uid, source="user_addresses")
                stats["user_addresses"] += 1


# ---------------------------------------------------------------------------
# Probe (read-only)
# ---------------------------------------------------------------------------
def probe(dd, conn):
    print(f"[probe] data dir = {dd}")
    ledger = read_json(os.path.join(dd, "mn2_ledger.json"))
    entries = as_list(ledger, "entries")
    print(f"\n-- mn2_ledger.json: {len(entries)} entries --")
    if entries:
        print("   elem keys:", sorted({k for e in entries if isinstance(e, dict) for k in e}))
        types = Counter((e.get("type") for e in entries if isinstance(e, dict)))
        print("   type taxonomy:", dict(types.most_common()))
        with_tx = sum(1 for e in entries if isinstance(e, dict) and e.get("txid"))
        with_addr = sum(1 for e in entries if isinstance(e, dict) and e.get("address"))
        valid_addr = sum(1 for e in entries if isinstance(e, dict) and validate_address(e.get("address") or ""))
        uids = {e.get("user_id") for e in entries if isinstance(e, dict)}
        print(f"   with txid={with_tx}  with address={with_addr}  valid MN2 addresses={valid_addr}  distinct users={len(uids)}")

    op = read_json(os.path.join(dd, "mn2_order_payments.json"))
    orders = as_list(op, "orders")
    print(f"\n-- mn2_order_payments.json: {len(orders)} orders --")
    if orders:
        print("   elem keys:", sorted({k for o in orders if isinstance(o, dict) for k in o}))
        with_tx = sum(1 for o in orders if isinstance(o, dict) and (o.get("txid") or o.get("mn2_txid")))
        print(f"   with txid={with_tx}")
        if conn and table_exists(conn, "shop_purchases") and "payment_ref" in cols_of(conn, "shop_purchases"):
            prefs = {o.get("payment_ref") for o in orders if isinstance(o, dict) and o.get("payment_ref")}
            qm = ",".join("?" * len(prefs)) if prefs else "''"
            matched = conn.execute(
                f"SELECT COUNT(DISTINCT payment_ref) FROM shop_purchases WHERE payment_ref IN ({qm})",
                tuple(prefs)).fetchone()[0] if prefs else 0
            print(f"   payment_ref join: {matched}/{len(prefs)} match shop_purchases")

    mh = read_json(os.path.join(dd, "mn2_masternode_hosts.json"))
    hosts = as_list(mh, "hosts")
    print(f"\n-- mn2_masternode_hosts.json: {len(hosts)} hosts --")
    if hosts:
        print("   elem keys:", sorted({k for h in hosts if isinstance(h, dict) for k in h}))

    for name in ("mn2_treasury_addresses.json", "mn2_user_addresses.json", "mn2_address_book.json"):
        p = os.path.join(dd, name)
        d = read_json(p)
        if d is None:
            print(f"\n-- {name}: NOT PRESENT --")
        else:
            n = len(d) if isinstance(d, (list, dict)) else 1
            sk = list(d)[:3] if isinstance(d, dict) else None
            print(f"\n-- {name}: present, top-level {type(d).__name__}({n}) sample_keys={sk} --")

    if conn and table_exists(conn, "shop_purchases"):
        c = cols_of(conn, "shop_purchases")
        print("\n-- shop_purchases --")
        print("   columns:", sorted(c))
        if "payment_method" in c:
            print("   payment_method values:",
                  dict(conn.execute("SELECT COALESCE(payment_method,'(null)'), COUNT(*) FROM shop_purchases GROUP BY 1").fetchall()))
        if "purchase_status" in c:
            print("   purchase_status values:",
                  dict(conn.execute("SELECT COALESCE(purchase_status,'(null)'), COUNT(*) FROM shop_purchases GROUP BY 1").fetchall()))


# ---------------------------------------------------------------------------
# Main backfill
# ---------------------------------------------------------------------------
def backfill(dd, conn):
    stats = Counter()
    # purchase payment_ref -> id index
    purchase_index = {}
    if table_exists(conn, "shop_purchases") and "payment_ref" in cols_of(conn, "shop_purchases"):
        for pid, pref in conn.execute(
                "SELECT id, payment_ref FROM shop_purchases WHERE payment_ref IS NOT NULL AND payment_ref<>''"):
            purchase_index.setdefault(pref, pid)

    proc_ledger(conn, read_json(os.path.join(dd, "mn2_ledger.json")), stats)
    proc_order_payments(conn, read_json(os.path.join(dd, "mn2_order_payments.json")), stats, purchase_index)
    proc_masternode_hosts(conn, read_json(os.path.join(dd, "mn2_masternode_hosts.json")), stats)
    proc_treasury(conn, read_json(os.path.join(dd, "mn2_treasury_addresses.json")), stats)
    for nm in ("mn2_user_addresses.json", "mn2_address_book.json"):
        proc_user_addresses(conn, read_json(os.path.join(dd, nm)), stats)

    refresh_wallet_counts(conn)
    log_recon(conn, "global", "backfill", None, None, "ok",
              f"ledger={stats['ledger']}(tx+{stats['ledger_tx']}) "
              f"order_payments={stats['order_payments']}(tx+{stats['order_tx']}) "
              f"masternodes={stats['masternode_hosts']} treasury={stats['treasury_addresses']} "
              f"user_addresses={stats['user_addresses']} purchases_linked={stats['purchases_linked']}")
    return stats


def reset_mn2(conn):
    """Clear ONLY the MN2 tables created by this migration (they are isolated and
    additive) and reset the shop_purchases MN2 columns this migration added.
    Used to re-run cleanly after refining the type->direction mapping. NEVER
    touches pre-existing app tables other than the 3 columns we added."""
    for t in ("mn2_transactions", "mn2_reconciliation_log", "mn2_addresses",
              "mn2_address_quota", "mn2_wallets"):
        if table_exists(conn, t):
            conn.execute(f"DELETE FROM {t}")
    if table_exists(conn, "shop_purchases"):
        c = cols_of(conn, "shop_purchases")
        if "onchain" in c:
            conn.execute("UPDATE shop_purchases SET onchain=0")
        for col in ("mn2_txid", "mn2_address"):
            if col in c:
                conn.execute(f"UPDATE shop_purchases SET {col}=NULL")
    print("[reset] cleared MN2 tables + shop_purchases MN2 columns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None, help="dir holding mn2_*.json (default: ./data)")
    ap.add_argument("--probe", action="store_true", help="report source shapes; write nothing")
    ap.add_argument("--reset", action="store_true",
                    help="clear MN2 tables (and the shop_purchases MN2 columns) before backfill")
    args = ap.parse_args()

    dd = resolve_data_dir(args.data_dir)
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")  # prod DB has pre-existing FK orphans; don't let them block
    try:
        if args.probe:
            probe(dd, conn)
            return
        if args.reset:
            reset_mn2(conn)
            conn.commit()
        stats = backfill(dd, conn)
        conn.commit()
        print("[done] " + " ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
