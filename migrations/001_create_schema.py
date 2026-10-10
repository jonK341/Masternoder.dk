#!/usr/bin/env python3
"""Phase A migration runner -- creates MN2 tables + site_pages, additively ALTERs shop_purchases.

NON-DESTRUCTIVE and IDEMPOTENT: safe to run repeatedly. Never drops/rewrites an
existing table. On the production server the real tables already exist, so the
--standins flag must be OFF there (it is only for building a local test replica).

Usage:
  local dry-run :  python 001_create_schema.py --db ../local_replica.db --standins
  server (real) :  python 001_create_schema.py            # reads DATABASE_URL from .env
"""
import argparse
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL = os.path.join(HERE, "schema_mn2.sql")

# Additive columns for the existing shop_purchases table (gap #2: link purchases on-chain).
SHOP_PURCHASE_ALTERS = [
    ("mn2_txid", "TEXT"),
    ("mn2_address", "TEXT"),
    ("onchain", "INTEGER NOT NULL DEFAULT 0"),
]

# Minimal stand-ins so the local replica can exercise the backfill. These use
# IF NOT EXISTS, so on a server that already has the real tables they are no-ops.
STANDIN_SQL = """
CREATE TABLE IF NOT EXISTS user_accounts (
  user_id    TEXT PRIMARY KEY,
  username   TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_profiles (
  user_id      TEXT PRIMARY KEY,
  display_name TEXT,
  updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS shop_purchases (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        TEXT NOT NULL,
  item_id        TEXT,
  amount         REAL NOT NULL DEFAULT 0,
  balance_before REAL,
  balance_after  REAL,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def resolve_db_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    url = os.environ.get("DATABASE_URL")
    if not url:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    m = re.match(r'\s*DATABASE_URL\s*=\s*["\']?(.+?)["\']?\s*$', line)
                    if m:
                        url = m.group(1)
                        break
    if not url:
        sys.exit("ERROR: no --db and no DATABASE_URL found. Pass --db <path>.")
    # strip sqlite:/// prefix if present
    return re.sub(r"^sqlite:///?", "", url)


def existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def run(db_path: str, standins: bool) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        if standins:
            conn.executescript(STANDIN_SQL)
            print("[standins] ensured local user_accounts / user_profiles / shop_purchases")

        with open(SCHEMA_SQL, "r", encoding="utf-8") as fh:
            conn.executescript(fh.read())
        print("[schema] applied schema_mn2.sql (MN2 tables + site_pages)")

        if table_exists(conn, "shop_purchases"):
            cols = existing_columns(conn, "shop_purchases")
            for name, decl in SHOP_PURCHASE_ALTERS:
                if name in cols:
                    print(f"[alter] shop_purchases.{name} already present -- skip")
                else:
                    conn.execute(f"ALTER TABLE shop_purchases ADD COLUMN {name} {decl}")
                    print(f"[alter] shop_purchases ADD COLUMN {name} {decl}")
        else:
            print("[alter] shop_purchases not found -- skipping ALTERs (run with --standins locally)")

        conn.commit()
    finally:
        conn.close()
    print(f"[done] migration applied to {db_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="explicit sqlite path (else DATABASE_URL)")
    ap.add_argument("--standins", action="store_true",
                    help="create minimal stand-in existing tables (LOCAL TEST ONLY)")
    ap.add_argument("--print-db", action="store_true",
                    help="print the resolved sqlite path and exit (no changes)")
    args = ap.parse_args()
    path = resolve_db_url(args.db)
    if args.print_db:
        print(path)
        return
    run(path, args.standins)


if __name__ == "__main__":
    main()
