#!/usr/bin/env python3
"""
Backfill schema_migrations with Phase 2 migration executions.
Safe to run repeatedly (upserts by version).
"""
import os
import hashlib
from pathlib import Path
from sqlalchemy import create_engine, text


PHASE2_ENTRIES = [
    (
        "phase2_20260224_01_unified_points",
        "scripts/unified_points_database_migration.py",
        "applied",
        "Phase 2 execution on instance/database.db",
    ),
    (
        "phase2_20260224_02_missing_tables",
        "scripts/missing_tables_migration.py",
        "applied",
        "Phase 2 execution on instance/database.db (absolute DB URL rerun)",
    ),
    (
        "phase2_20260224_03_agent_technologies",
        "scripts/agent_technologies_database_migration.py",
        "applied",
        "Phase 2 execution on instance/database.db",
    ),
    (
        "phase2_20260224_04_hunters_rewards",
        "scripts/migrate_hunters_game_complete.py",
        "applied",
        "Script had cp1252 emoji print error; tables verified present",
    ),
    (
        "phase2_20260224_05_comm_psych",
        "scripts/communication_psychology_migration.py",
        "applied",
        "Phase 2 execution on instance/database.db",
    ),
    (
        "phase2_20260224_06_hunters_star_map",
        "scripts/hunters_star_map_migration.py",
        "applied",
        "Phase 2 execution on instance/database.db",
    ),
]


def checksum(path: Path) -> str:
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
    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///instance/database.db"
    root = Path(__file__).resolve().parent.parent
    engine = create_engine(db_url)

    with engine.begin() as conn:
        for version, script_name, status, notes in PHASE2_ENTRIES:
            script_path = root / script_name
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
                    "checksum": checksum(script_path),
                    "status": status,
                    "notes": notes,
                },
            )

    print(f"Backfilled {len(PHASE2_ENTRIES)} Phase 2 migration entries into {db_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
