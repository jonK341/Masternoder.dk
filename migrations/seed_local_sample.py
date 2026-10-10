#!/usr/bin/env python3
"""LOCAL SAMPLE DATA ONLY -- builds a representative test fixture for the dry-run.

Generates:
  - data/mn2_address_book.json  (shape: {user_id: {addresses:[...], balance, account}})
  - user_accounts / user_profiles rows
  - shop_purchases rows (some already linked to a txid, most NOT -- to exercise the gap)

Addresses are real, checksum-valid MN2 base58check strings (version byte 43) so the
backfill's validator passes. NOTHING here is production data. Do not run on server.
"""
import hashlib
import json
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mn2_addr import hash160_to_address  # noqa: E402

DB = os.path.join(HERE, "..", "local_replica.db")
BOOK = os.path.join(HERE, "..", "data", "mn2_address_book.json")

random.seed(20260926)  # deterministic fixture


def gen_address(seed_int: int) -> str:
    h160 = hashlib.sha256(str(seed_int).encode()).digest()[:20]
    return hash160_to_address(h160)


def gen_txid(seed_int: int) -> str:
    return hashlib.sha256(f"tx{seed_int}".encode()).hexdigest()


def main():
    n_users = 12
    users = [f"user_{1000 + i}" for i in range(n_users)]

    # ---- address book ----
    book = {}
    counter = 0
    for i, uid in enumerate(users):
        addrs = []
        for _ in range(random.randint(1, 4)):
            addrs.append(gen_address(counter))
            counter += 1
        book[uid] = {
            "account": f"acct_{i:03d}",
            "balance": round(random.uniform(0, 250), 4),
            "addresses": addrs,
        }
    os.makedirs(os.path.dirname(BOOK), exist_ok=True)
    with open(BOOK, "w", encoding="utf-8") as fh:
        json.dump(book, fh, indent=2)
    print(f"[seed] wrote {BOOK}: {len(book)} users, {counter} addresses")

    # ---- existing stand-in tables ----
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys=ON")
    for uid in users:
        conn.execute(
            "INSERT OR IGNORE INTO user_accounts (user_id, username) VALUES (?,?)",
            (uid, uid.replace("user_", "mn_user_")),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id, display_name) VALUES (?,?)",
            (uid, f"Tester {uid[-3:]}"),
        )
    # purchases: ~40 rows across users; only 6 carry a txid (linked), rest are the gap
    conn.execute("DELETE FROM shop_purchases")
    pid = 0
    for uid in users:
        for _ in range(random.randint(2, 5)):
            pid += 1
            amount = round(random.uniform(1, 99), 2)
            conn.execute(
                """INSERT INTO shop_purchases (user_id, item_id, amount, balance_before, balance_after)
                   VALUES (?,?,?,?,?)""",
                (uid, f"item_{random.randint(1,9)}", amount, 100.0, round(100.0 - amount, 2)),
            )
    # link a handful with a fake txid via the new column
    rows = conn.execute("SELECT id FROM shop_purchases ORDER BY id LIMIT 6").fetchall()
    for idx, (rid,) in enumerate(rows):
        conn.execute(
            "UPDATE shop_purchases SET mn2_txid=?, onchain=1 WHERE id=?",
            (gen_txid(9000 + idx), rid),
        )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0]
    print(f"[seed] shop_purchases={total} (6 pre-linked with txid, {total-6} unlinked = the gap)")
    conn.close()


if __name__ == "__main__":
    main()
