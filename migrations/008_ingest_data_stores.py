#!/usr/bin/env python3
"""Phase E -- generic data-store ingestion ("what else is useful in the DB?").

Walks data/** and materializes EVERY JSON / JSONL store into two tables:

  data_store_catalog   one row per file: shape, record count, field union, flags
  data_store_records   one row per record, full payload preserved + the common
                       fields (user_ref, mn2_address, amount, currency, status,
                       created_at) promoted to real, queryable columns.

This gives the database rows for all ~100 logical entities at once (camgirls,
agents, battles, staking, p2p, onramp, masternodes, achievements, ...) without
hand-guessing 100 brittle schemas. High-value domains are then promoted to typed
tables by later scripts (e.g. 009_camgirls.py).

SAFE: read-only on files, additive/idempotent on DB. Moves no funds, no RPC.

  python 008_ingest_data_stores.py --db instance/database.db --data-dir data
"""
import argparse
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

EXCLUDE_DIRS = {"backups", "logs", "node_modules", ".venv", "__pycache__", ".git", "avatars"}
USER_KEYS = ("user_id", "userId", "owner_user_id", "owner", "user", "seller_id",
             "buyer_id", "account_id", "uid", "to_user", "from_user", "performer_id")
STATUS_KEYS = ("status", "purchase_status", "state", "order_status")
DATE_KEYS = ("created_at", "timestamp", "date", "occurred_at", "ts", "updated_at")
# amount-like key -> currency hint ('' = unknown / infer from a 'currency' field)
AMOUNT_KEYS = {
    "amount": "", "mn2_amount": "mn2", "amount_mn2": "mn2", "mn2_total": "mn2",
    "coins_total": "coins", "coins": "coins", "usd_amount": "usd", "usd_total": "usd",
    "usd": "usd", "gross": "usd", "gross_usd": "usd", "net_usd": "usd", "price_usd": "usd",
    "amount_usd": "usd", "balance_usd": "usd", "price": "", "total": "", "value": "",
    "points": "points", "price_paid_coins": "coins", "price_paid_usd": "usd",
    "price_paid_points": "points", "tip": "usd", "usd_per_slot": "usd",
}


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root, include_archived, max_mb):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if include_archived or d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not (fn.endswith(".json") or fn.endswith(".jsonl")):
                continue
            full = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(full) > max_mb * 1024 * 1024:
                    continue
            except OSError:
                continue
            yield full, os.path.relpath(full, root)


def load_store(path):
    """Return (kind, records) where records is a list of (record_key, value)."""
    if path.endswith(".jsonl"):
        recs = []
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    recs.append((str(i), json.loads(line)))
                except json.JSONDecodeError:
                    continue
        return "jsonl", recs
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return "list", [(str(i), v) for i, v in enumerate(data)]
    if isinstance(data, dict):
        # single-wrapper dict holding a list of records, e.g. {entries:[...]}, {orders:[...]}
        list_keys = [k for k, v in data.items() if isinstance(v, list)]
        if len(data) == 1 and list_keys:
            k = list_keys[0]
            return "dict", [(str(i), v) for i, v in enumerate(data[k])]
        return "dict", [(str(k), v) for k, v in data.items()]
    return "scalar", [("0", data)]


def first_str_addr(value):
    """Find a checksum-valid MN2 address anywhere in a record's string leaves."""
    stack = [value]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
        elif isinstance(n, str):
            s = n.strip()
            if 26 <= len(s) <= 35 and s[0] == "J" and validate_address(s):
                return s
    return None


def extract(rec):
    """Pull common columns out of a record (best-effort, never raises)."""
    user_ref = mn2_address = status = created_at = currency = None
    amount = None
    if not isinstance(rec, dict):
        return user_ref, mn2_address, amount, currency, status, created_at
    for k in USER_KEYS:
        if k in rec and isinstance(rec[k], (str, int)):
            user_ref = str(rec[k])
            break
    for k in STATUS_KEYS:
        if k in rec and isinstance(rec[k], str):
            status = rec[k]
            break
    for k in DATE_KEYS:
        if k in rec and isinstance(rec[k], (str, int, float)):
            created_at = str(rec[k])
            break
    if isinstance(rec.get("currency"), str):
        currency = rec["currency"].lower()
    for k, cur in AMOUNT_KEYS.items():
        if k in rec and isinstance(rec[k], (int, float)) and not isinstance(rec[k], bool):
            amount = float(rec[k])
            currency = currency or (cur or None)
            break
    mn2_address = first_str_addr(rec)
    return user_ref, mn2_address, amount, currency, status, created_at


def field_union(records):
    fields = set()
    for _, v in records:
        if isinstance(v, dict):
            fields.update(v.keys())
    return sorted(fields)


def ingest_file(conn, path, rel):
    store_name = rel.replace(os.sep, "__")
    for ext in (".jsonl", ".json"):
        if store_name.endswith(ext):
            store_name = store_name[: -len(ext)]
    try:
        kind, records = load_store(path)
    except Exception as e:  # noqa: BLE001
        return None, f"load-error: {e}"

    fields = field_union(records)
    fset = set(fields)
    has_user = int(bool(fset & set(USER_KEYS)))
    has_amt = int(bool(fset & set(AMOUNT_KEYS)))
    has_paypal = int(any("paypal" in f.lower() or f.lower() in {"capture_id", "gross"} for f in fields))
    has_addr = 0

    top_keys = fields[:12] if kind != "scalar" else []
    n = 0
    for rkey, value in records:
        user_ref, addr, amount, currency, status, created_at = extract(value)
        if addr:
            has_addr = 1
        payload = value if isinstance(value, str) else json.dumps(value, default=str)
        conn.execute(
            """INSERT INTO data_store_records
                 (store_name, record_key, user_ref, mn2_address, amount, currency,
                  status, created_at, payload_json, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(store_name, record_key) DO UPDATE SET
                 user_ref=excluded.user_ref, mn2_address=excluded.mn2_address,
                 amount=excluded.amount, currency=excluded.currency, status=excluded.status,
                 created_at=excluded.created_at, payload_json=excluded.payload_json,
                 ingested_at=excluded.ingested_at""",
            (store_name, rkey, user_ref, addr, amount, currency, status, created_at,
             payload, utcnow()),
        )
        n += 1

    chash = sha1_file(path)
    conn.execute(
        """INSERT INTO data_store_catalog
             (store_name, file_path, kind, record_count, top_keys_json, record_fields_json,
              has_user_ref, has_mn2_address, has_amount, has_paypal, byte_size, content_hash, ingested_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(store_name) DO UPDATE SET
             file_path=excluded.file_path, kind=excluded.kind, record_count=excluded.record_count,
             top_keys_json=excluded.top_keys_json, record_fields_json=excluded.record_fields_json,
             has_user_ref=excluded.has_user_ref, has_mn2_address=excluded.has_mn2_address,
             has_amount=excluded.has_amount, has_paypal=excluded.has_paypal,
             byte_size=excluded.byte_size, content_hash=excluded.content_hash,
             ingested_at=excluded.ingested_at""",
        (store_name, rel, kind, n, json.dumps(top_keys), json.dumps(fields),
         has_user, has_addr, has_amt, has_paypal,
         os.path.getsize(path), chash, utcnow()),
    )
    return {"store": store_name, "kind": kind, "n": n, "addr": has_addr,
            "user": has_user, "amt": has_amt, "paypal": has_paypal}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--include-archived", action="store_true",
                    help="also scan backups/ and logs/ (off by default)")
    ap.add_argument("--max-file-mb", type=float, default=20.0)
    ap.add_argument("--only", help="comma-separated store-name substrings to ingest")
    ap.add_argument("--reset", action="store_true",
                    help="clear data_store_catalog + data_store_records first")
    args = ap.parse_args()

    dd = args.data_dir or os.path.join(os.getcwd(), "data")
    if not os.path.isdir(dd):
        dd = os.path.abspath(os.path.join(HERE, "..", "data"))
    only = [s.strip().lower() for s in args.only.split(",")] if args.only else None

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")
    if args.reset:
        conn.execute("DELETE FROM data_store_records")
        conn.execute("DELETE FROM data_store_catalog")
        conn.commit()
        print("[ingest] reset data_store_catalog + data_store_records")

    ok = err = total_recs = 0
    addr_stores = []
    paypal_stores = []
    try:
        for full, rel in iter_files(dd, args.include_archived, args.max_file_mb):
            if only and not any(s in rel.lower() for s in only):
                continue
            info, e = ingest_file(conn, full, rel)
            if e:
                err += 1
                print(f"  [skip] {rel}: {e}")
                continue
            ok += 1
            total_recs += info["n"]
            if info["addr"]:
                addr_stores.append((info["store"], info["n"]))
            if info["paypal"]:
                paypal_stores.append((info["store"], info["n"]))
        conn.commit()
    finally:
        conn.close()

    print(f"\n[ingest] stores ok={ok} err={err} records={total_recs}  (root={dd})")
    print(f"[ingest] stores carrying MN2 addresses: {len(addr_stores)}")
    for s, n in sorted(addr_stores)[:40]:
        print(f"   addr  {s:52} {n}")
    print(f"[ingest] stores carrying paypal/revenue fields: {len(paypal_stores)}")
    for s, n in sorted(paypal_stores)[:40]:
        print(f"   paypal {s:51} {n}")
    print("[ingest] next: run 009_camgirls.py to promote camgirls_* into typed tables")


if __name__ == "__main__":
    main()
