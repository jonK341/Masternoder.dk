#!/usr/bin/env python3
"""Phase C2 -- connect ALL the different user wallets across sub-apps ("sites") into
ONE canonical DB wallet identity. DB-LEVEL ONLY: moves NO coins.

Many sub-systems keep their own MN2 addresses in their own data/*.json (agent wallets,
camgirls payout addresses, crypto-exchange wallets, staking, p2p, treasury, ...). This
scans those files, extracts every checksum-valid MN2 address (version byte 43 / 'J'),
attributes it to the nearest user identifier in the same record, and upserts it into
mn2_wallets / mn2_addresses with source='harvest:<file>'. Re-run 005 afterwards to fold
the new addresses into canonical per-user stats.

SAFE: read-only on files, additive/idempotent on DB, never touches the chain or funds.
Excludes backups/logs by default (use --include-archived to scan them too).

  python 007_consolidate_wallets.py --db instance/database.db --data-dir data
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mn2_addr import validate_address  # noqa: E402

USER_KEYS = ("user_id", "userId", "owner_user_id", "owner", "user", "seller_id",
             "buyer_id", "account_id", "uid", "to_user", "from_user")
EXCLUDE_DIRS = {"backups", "logs", "node_modules", ".venv", "__pycache__", ".git"}
UNATTRIB = "__unattributed__"


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def upsert_wallet(conn, user_id, source):
    conn.execute(
        """INSERT INTO mn2_wallets (user_id, wallet_kind, source, created_at, updated_at)
           VALUES (?,?,?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at""",
        (str(user_id), "custodial", source, utcnow(), utcnow()),
    )
    return conn.execute("SELECT id FROM mn2_wallets WHERE user_id=?", (str(user_id),)).fetchone()[0]


def upsert_address(conn, address, wallet_id, user_id, label, source):
    conn.execute(
        """INSERT INTO mn2_addresses
             (address, wallet_id, user_id, label, is_valid, first_seen, source, created_at)
           VALUES (?,?,?,?,1,?, ?, ?)
           ON CONFLICT(address) DO UPDATE SET
             wallet_id = COALESCE(mn2_addresses.wallet_id, excluded.wallet_id)""",
        (address, wallet_id, str(user_id), label, utcnow(), source, utcnow()),
    )


def walk(node, user_ctx, top_key, field, hits):
    """Depth-first walk carrying the nearest user identifier as user_ctx."""
    if isinstance(node, dict):
        ctx = user_ctx
        for k in USER_KEYS:
            if k in node and isinstance(node[k], (str, int)):
                ctx = str(node[k])
                break
        for k, v in node.items():
            walk(v, ctx, top_key if top_key is not None else k, k, hits)
    elif isinstance(node, list):
        for v in node:
            walk(v, user_ctx, top_key, field, hits)
    elif isinstance(node, str):
        s = node.strip()
        if 26 <= len(s) <= 35 and s[0] == "J" and validate_address(s):
            attrib = user_ctx or (top_key if isinstance(top_key, str) and top_key.startswith("user_") else None)
            hits.append((s, attrib or UNATTRIB, field or top_key or "value"))


def scan_file(path, rel):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return []
    hits = []
    if isinstance(data, dict):
        for k, v in data.items():
            walk(v, None, k, None, hits)
    else:
        walk(data, None, None, None, hits)
    return [(addr, user, field, rel) for (addr, user, field) in hits]


def iter_json(root, include_archived, max_mb):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if include_archived or d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(full) > max_mb * 1024 * 1024:
                    continue
            except OSError:
                continue
            yield full, os.path.relpath(full, root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--include-archived", action="store_true",
                    help="also scan backups/ and logs/ (off by default)")
    ap.add_argument("--max-file-mb", type=float, default=20.0)
    args = ap.parse_args()

    dd = args.data_dir or os.path.join(os.getcwd(), "data")
    if not os.path.isdir(dd):
        dd = os.path.abspath(os.path.join(HERE, "..", "data"))

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=OFF")
    per_file = Counter()
    total_addr = 0
    new_addr = 0
    try:
        existing = {r[0] for r in conn.execute("SELECT address FROM mn2_addresses")}
        for full, rel in iter_json(dd, args.include_archived, args.max_file_mb):
            hits = scan_file(full, rel)
            if not hits:
                continue
            src = f"harvest:{rel}"
            for addr, user, field, _ in hits:
                wid = upsert_wallet(conn, user, "harvest")
                upsert_address(conn, addr, wid, user, field, src)
                per_file[rel] += 1
                total_addr += 1
                if addr not in existing:
                    new_addr += 1
                    existing.add(addr)
        # record per-source inventory as metrics
        for rel, n in per_file.items():
            conn.execute(
                """INSERT INTO mn2_metrics (metric_key, value_num, scope, scope_id, as_of, source, updated_at)
                   VALUES ('wallet_harvest.addresses', ?, 'source', ?, '', ?, ?)
                   ON CONFLICT(metric_key, scope, scope_id, as_of) DO UPDATE SET
                     value_num=excluded.value_num, updated_at=excluded.updated_at""",
                (n, rel, rel, utcnow()),
            )
        conn.execute(
            """INSERT INTO mn2_metrics (metric_key, value_num, scope, scope_id, as_of, source, updated_at)
               VALUES ('wallet_harvest.total_addresses', ?, 'global', '', '', 'consolidate', ?)
               ON CONFLICT(metric_key, scope, scope_id, as_of) DO UPDATE SET
                 value_num=excluded.value_num, updated_at=excluded.updated_at""",
            (total_addr, utcnow()),
        )
        conn.execute(
            """UPDATE mn2_wallets SET address_count =
                 (SELECT COUNT(*) FROM mn2_addresses a WHERE a.wallet_id = mn2_wallets.id)"""
        )
        conn.commit()
    finally:
        conn.close()

    print(f"[harvest] scanned {dd}; files with addresses={len(per_file)}; "
          f"address refs={total_addr} (new={new_addr})")
    for rel, n in per_file.most_common():
        print(f"   {rel:48} {n}")
    print("[harvest] re-run 005_compute_stats.py to fold new addresses into canonical stats")


if __name__ == "__main__":
    main()
