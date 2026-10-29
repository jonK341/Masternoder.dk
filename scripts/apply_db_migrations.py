#!/usr/bin/env python3
"""
Run idempotent DB migrations on the live server after git pull. <!-- pragma: allowlist secret -->

Safe for live server: additive schema only; backs up SQLite before MN2 DDL.
Does not run heavy MN2 backfill unless RUN_MN2_BACKFILL=1.

Usage (on server):
  cd /var/www/html && python3 scripts/apply_db_migrations.py
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT, ".env"))
except Exception:
    pass


def _python() -> str:
    venv = os.path.join(_ROOT, ".venv", "bin", "python")
    if os.path.isfile(venv) and os.access(venv, os.X_OK):
        return venv
    return sys.executable


def _run(label: str, argv: list[str], *, timeout: int = 600) -> None:
    print(f"\n--- {label} ---")
    proc = subprocess.run(
        argv,
        cwd=_ROOT,
        timeout=timeout,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{label} failed (exit {proc.returncode})")


def main() -> int:
    py = _python()
    print("=" * 60)
    print("SERVER DB MIGRATIONS")
    print("=" * 60)
    print(f"python: {py}")
    print(f"root:   {_ROOT}")

    _run("Feature migrations (battle, shop, generator, …)", [py, "scripts/run_all_migrations.py"])

    print("\n--- Point ledger bootstrap (schema_migrations + point_transactions) ---")
    from src.app import create_app
    from backend.services.schema_bootstrap import ensure_point_ledger_schema

    app = create_app()
    with app.app_context():
        if not ensure_point_ledger_schema():
            raise SystemExit("point ledger schema bootstrap failed")

    migrations_dir = os.path.join(_ROOT, "migrations")
    schema_script = os.path.join(migrations_dir, "001_create_schema.py")
    db_path = os.path.join(_ROOT, "instance", "database.db")
    if os.path.isfile(schema_script):
        backup = os.path.join(migrations_dir, "000_safety_backup.py")
        if os.path.isfile(backup) and os.path.isfile(db_path):
            _run("SQLite safety backup", [py, backup, db_path], timeout=120)
        _run("MN2 additive schema (001_create_schema)", [py, schema_script, "--db", db_path], timeout=300)

    platform_script = os.path.join(migrations_dir, "010_platform_wallet_nft_payments.py")
    if os.path.isfile(platform_script):
        _run(
            "Platform wallets, NFT, payment slots (010)",
            [py, platform_script, "--db", db_path, "--data-dir", os.path.join(_ROOT, "data")],
            timeout=600,
        )

    if os.environ.get("RUN_MN2_BACKFILL", "").strip().lower() in ("1", "true", "yes"):
        runner = os.path.join(migrations_dir, "run_server_migration.sh")
        if os.path.isfile(runner):
            _run("MN2 backfill (apply)", ["bash", runner, "apply"], timeout=3600)
        else:
            print("[WARN] RUN_MN2_BACKFILL set but migrations/run_server_migration.sh missing")

    print("\n" + "=" * 60)
    print("SERVER DB MIGRATIONS COMPLETE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
