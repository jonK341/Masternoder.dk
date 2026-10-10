#!/usr/bin/env python3
"""
Verify SQLite (or any SQLAlchemy URL) has all tables required by GET /api/health/database.

Usage (repo root):
  python scripts/verify_health_tables_sqlite.py

Loads .env from project root. Exit 0 if all tables respond to SELECT COUNT(*); else 1.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

TABLES = [
    "player_levels",
    "system_point_snapshots",
    "shop_purchases",
    "user_inventory",
    "shop_items",
    "schema_migrations",
    "rewards",
    "user_rewards",
]


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_root, ".env"))
    except ImportError:
        pass

    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not url:
        print("[FAIL] Set DATABASE_URL or SQLALCHEMY_DATABASE_URI")
        return 1

    from sqlalchemy import create_engine, text

    if url.startswith("sqlite") and "psycopg" not in url:
        engine = create_engine(url)
    elif "postgresql://" in url and "psycopg2" not in url:
        engine = create_engine(url.replace("postgresql://", "postgresql+psycopg2://", 1))
    else:
        engine = create_engine(url)

    missing = []
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("[OK] SELECT 1")
        for t in TABLES:
            try:
                conn.execute(text(f"SELECT COUNT(*) FROM {t} LIMIT 1"))
                print(f"[OK] {t}")
            except Exception as e:
                print(f"[MISS] {t}: {e}")
                missing.append(t)

    if missing:
        print(f"\n[ACTION] Missing or inaccessible: {missing}")
        print("  Run migrations: python scripts/shop_purchase_migration.py --standalone")
        print("  Or use db.create_all from app context if models cover these.")
        return 1
    print("\n[OK] All health-check tables present (same list as health_routes.database_health).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
