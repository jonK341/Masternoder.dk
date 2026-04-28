#!/usr/bin/env python3
"""
Bootstrap schema_migrations ledger table in the configured database.
Safe to run multiple times.
"""
import os
from sqlalchemy import create_engine, text


def main() -> int:
    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///instance/database.db"
    engine = create_engine(db_url)

    create_sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version VARCHAR(64) NOT NULL UNIQUE,
        script_name VARCHAR(255) NOT NULL,
        checksum VARCHAR(128),
        status VARCHAR(32) NOT NULL DEFAULT 'applied',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )
    """

    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
    ON schema_migrations(applied_at)
    """

    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(text(index_sql))

    print(f"schema_migrations ready in {db_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
