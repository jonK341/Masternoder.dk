#!/usr/bin/env python3
"""
Run a migration script and automatically record outcome in schema_migrations.

Example:
  python scripts/run_and_record_migration.py \
    --version phase5_20260224_test \
    --script scripts/communication_psychology_migration.py \
    --notes "rerun for verification"
"""
import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, text


def sha256_file(path: Path) -> str:
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


def record(
    db_url: str,
    version: str,
    script_name: str,
    checksum: str,
    status: str,
    notes: str,
) -> None:
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
                "version": version,
                "script_name": script_name,
                "checksum": checksum,
                "status": status,
                "notes": notes,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and record migration")
    parser.add_argument("--version", required=True, help="Unique migration version key")
    parser.add_argument("--script", required=True, help="Path to migration script")
    parser.add_argument("--notes", default="", help="Optional notes")
    parser.add_argument("--db-url", default="", help="Optional DB URL override")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use")
    parser.add_argument("--no-env-pass", action="store_true", help="Do not pass DATABASE_URL to subprocess")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///instance/database.db"
    script_path = Path(args.script)
    script_name = str(script_path).replace("\\", "/")
    checksum = sha256_file(script_path)

    env = os.environ.copy()
    if not args.no_env_pass:
        env["DATABASE_URL"] = db_url
    env.setdefault("PYTHONIOENCODING", "utf-8")

    cmd = [args.python, script_name]
    print(f"Running: {' '.join(cmd)}")
    print(f"DATABASE_URL={db_url}")
    completed = subprocess.run(cmd, env=env)

    status = "applied" if completed.returncode == 0 else "failed"
    note = args.notes or ""
    if completed.returncode != 0:
        note = (note + " | " if note else "") + f"exit_code={completed.returncode}"

    record(
        db_url=db_url,
        version=args.version,
        script_name=script_name,
        checksum=checksum,
        status=status,
        notes=note,
    )
    print(f"Recorded {args.version} as {status}")

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
