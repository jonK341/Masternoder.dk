#!/usr/bin/env python3
"""
Record a migration execution row in schema_migrations.

Usage:
  python scripts/record_migration.py --version v20260224_01 --script scripts/foo.py
"""
import argparse
import os
import hashlib
from pathlib import Path
from sqlalchemy import create_engine, text


def file_checksum(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Record migration in schema_migrations")
    parser.add_argument("--version", required=True, help="Unique migration version")
    parser.add_argument("--script", required=True, help="Migration script path")
    parser.add_argument("--status", default="applied", help="applied/failed/skipped")
    parser.add_argument("--notes", default="", help="Optional notes")
    parser.add_argument("--db-url", default="", help="Override DATABASE_URL")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///instance/database.db"
    script_path = Path(args.script)
    checksum = file_checksum(script_path)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO schema_migrations(version, script_name, checksum, status, notes)
                VALUES (:version, :script_name, :checksum, :status, :notes)
                ON CONFLICT(version) DO UPDATE SET
                    script_name = excluded.script_name,
                    checksum = excluded.checksum,
                    status = excluded.status,
                    notes = excluded.notes
                """
            ),
            {
                "version": args.version,
                "script_name": str(script_path).replace("\\", "/"),
                "checksum": checksum,
                "status": args.status,
                "notes": args.notes,
            },
        )

    print(f"Recorded migration {args.version} ({args.status}) in {db_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
