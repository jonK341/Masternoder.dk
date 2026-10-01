#!/usr/bin/env python3
"""Block 16 / fiat settle schema: create fiat_payments for fiat_payment_service.

Idempotent. Mirrors DB path resolution used by backend.services.fiat_payment_service.
CLI:
  python scripts/mn2_settle_schema.py           # dry-run / plan
  python scripts/mn2_settle_schema.py apply     # dry-run unless --yes
  python scripts/mn2_settle_schema.py apply --yes
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from typing import List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fiat_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL DEFAULT 'paypal',
    order_id TEXT,
    capture_id TEXT NOT NULL,
    user_id TEXT,
    item_id TEXT,
    item_name TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    amount REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'captured',
    price_expected REAL,
    price_match INTEGER,
    granted_kind TEXT,
    granted_amount REAL,
    purchase_id INTEGER,
    webhook_verified INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(capture_id)
)
""".strip()

INDEX_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_fiat_payments_capture_id ON fiat_payments(capture_id)",
    "CREATE INDEX IF NOT EXISTS idx_fiat_payments_user_id ON fiat_payments(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_fiat_payments_order_id ON fiat_payments(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_fiat_payments_status ON fiat_payments(status)",
    "CREATE INDEX IF NOT EXISTS idx_fiat_payments_created_at ON fiat_payments(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_fiat_payments_provider ON fiat_payments(provider)",
]


def _db_path() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or ""
    if not url.startswith("sqlite"):
        env = os.path.join(REPO, ".env")
        try:
            with open(env, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    m = re.match(r'\s*DATABASE_URL\s*=\s*["\']?(.+?)["\']?\s*$', line)
                    if m:
                        url = m.group(1)
                        break
        except Exception:
            url = ""
    if url.startswith("sqlite"):
        p = re.sub(r"^sqlite:///?", "", url).split("?", 1)[0]
        if not p.startswith("/"):
            p = os.path.join(REPO, p.replace("/", os.sep))
        return os.path.abspath(p)
    fallback = os.path.join(REPO, "instance", "database.db")
    return fallback if os.path.exists(fallback) else None


def _has_table(c: sqlite3.Connection, name: str) -> bool:
    row = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _plan(c: sqlite3.Connection) -> List[Tuple[str, str]]:
    steps: List[Tuple[str, str]] = []
    if not _has_table(c, "fiat_payments"):
        steps.append(("CREATE TABLE fiat_payments", CREATE_TABLE_SQL))
    else:
        steps.append(("SKIP CREATE TABLE fiat_payments (exists)", ""))
    existing = {
        r[0]
        for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='fiat_payments'"
        ).fetchall()
    }
    for sql in INDEX_SQL:
        # name is third token after CREATE [UNIQUE] INDEX IF NOT EXISTS NAME
        parts = sql.split()
        if "UNIQUE" in parts:
            name = parts[parts.index("EXISTS") + 1]
        else:
            name = parts[parts.index("EXISTS") + 1]
        if name in existing:
            steps.append((f"SKIP INDEX {name} (exists)", ""))
        else:
            steps.append((f"CREATE INDEX {name}", sql))
    return steps


def apply(do_write: bool) -> int:
    path = _db_path()
    if not path:
        print("ERROR: could not resolve sqlite database path", file=sys.stderr)
        return 2
    if not os.path.exists(path):
        print(f"ERROR: database file not found: {path}", file=sys.stderr)
        return 2
    print(f"DB: {path}")
    print(f"Mode: {'APPLY' if do_write else 'DRY-RUN (plan only)'}")
    c = sqlite3.connect(path, timeout=30)
    try:
        steps = _plan(c)
        for label, sql in steps:
            print(f"  - {label}")
            if do_write and sql:
                c.execute(sql)
        if do_write:
            c.commit()
            print("Applied OK.")
        else:
            print("Dry-run complete. Re-run with: apply --yes")
        if _has_table(c, "fiat_payments") or do_write:
            cols = c.execute("PRAGMA table_info(fiat_payments)").fetchall()
            if cols:
                print("Columns:", ", ".join(f"{r[1]}:{r[2]}" for r in cols))
            idxs = c.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='fiat_payments' ORDER BY name"
            ).fetchall()
            print("Indexes:", ", ".join(r[0] for r in idxs) or "(none)")
        return 0
    except Exception as e:
        try:
            c.rollback()
        except Exception:
            pass
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        c.close()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Create fiat_payments settle schema (Block 16)")
    p.add_argument("command", nargs="?", default="plan", choices=["plan", "apply"])
    p.add_argument("--yes", action="store_true", help="Actually write (with apply)")
    args = p.parse_args(argv)
    do_write = args.command == "apply" and args.yes
    if args.command == "apply" and not args.yes:
        print("apply without --yes => dry-run")
    return apply(do_write=do_write)


if __name__ == "__main__":
    sys.exit(main())
