"""Idempotent startup schema for the points ledger and migration log.

Creates point_transactions and schema_migrations when they are missing, adds
any columns the write path expects, and records the run. Safe to call on every
app start. Failures are logged and do not stop the process.
"""
import logging
import os
import tempfile
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

try:
    import fcntl
except ImportError:  # pragma: no cover - non-Unix
    fcntl = None

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "20261010_point_transactions_schema_migrations"
MIGRATION_SCRIPT = "backend/services/schema_bootstrap.py"

_POINT_TRANSACTION_COLUMNS = (
    ("user_id", "VARCHAR(100)"),
    ("system_name", "VARCHAR(100)"),
    ("transaction_type", "VARCHAR(50)"),
    ("amount", "NUMERIC"),
    ("balance_before", "NUMERIC"),
    ("balance_after", "NUMERIC"),
    ("source", "VARCHAR(100)"),
    ("reference_id", "VARCHAR(100)"),
    ("metadata", "TEXT"),
    ("created_at", "TIMESTAMP"),
)

_SCHEMA_MIGRATION_COLUMNS = (
    ("version", "VARCHAR(64)"),
    ("script_name", "VARCHAR(255)"),
    ("checksum", "VARCHAR(128)"),
    ("status", "VARCHAR(32)"),
    ("applied_at", "TIMESTAMP"),
    ("notes", "TEXT"),
)

# Columns /api/health/data-schema reads. Keep the SELECT in lockstep with the table.
SCHEMA_MIGRATIONS_HEALTH_COLUMNS = ("script_name", "status", "applied_at")


def ensure_point_ledger_schema(engine: Optional[Engine] = None) -> bool:
    """Create or repair the ledger once per database, even when several workers boot."""
    try:
        if engine is None:
            from src.db.models import db
            engine = db.engine
        lock_path = _lock_path(engine)
        os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as handle:
            _acquire_lock(handle)
            try:
                if _migration_recorded(engine):
                    return True
                _create_tables(engine)
                _add_missing_columns(engine, "point_transactions", _POINT_TRANSACTION_COLUMNS)
                _add_missing_columns(engine, "schema_migrations", _SCHEMA_MIGRATION_COLUMNS)
                _ensure_indexes(engine)
                _record_migration(engine)
                return True
            finally:
                _release_lock(handle)
    except Exception:
        logger.exception("point ledger schema bootstrap failed")
        try:
            from src.db.models import db
            db.session.rollback()
        except Exception:
            pass
        return False


def _lock_path(engine: Engine) -> str:
    database = getattr(engine.url, "database", None)
    if database and database != ":memory:":
        return database + ".point_ledger.lock"
    return os.path.join(tempfile.gettempdir(), "masternoder_point_ledger.lock")


def _acquire_lock(handle) -> None:
    if fcntl is None:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release_lock(handle) -> None:
    if fcntl is None:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _migration_recorded(engine: Engine) -> bool:
    try:
        inspector = inspect(engine)
        if "schema_migrations" not in inspector.get_table_names():
            return False
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE version = :version LIMIT 1"),
                {"version": MIGRATION_VERSION},
            ).first()
        return row is not None
    except Exception:
        return False


def _create_tables(engine: Engine) -> None:
    from src.db.models import PointTransaction, SchemaMigration

    PointTransaction.__table__.create(bind=engine, checkfirst=True)
    SchemaMigration.__table__.create(bind=engine, checkfirst=True)


def _add_missing_columns(engine: Engine, table: str, columns) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    present = {col["name"] for col in inspector.get_columns(table)}
    missing = [(name, ddl) for name, ddl in columns if name not in present]
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def _ensure_indexes(engine: Engine) -> None:
    dialect = engine.dialect.name
    if dialect not in ("sqlite", "postgresql"):
        return
    statements = (
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON point_transactions (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_system ON point_transactions (system_name)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON point_transactions (created_at)",
        "CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at ON schema_migrations (applied_at)",
    )
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _record_migration(engine: Engine) -> None:
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE version = :version LIMIT 1"),
            {"version": MIGRATION_VERSION},
        ).first()
        if existing:
            return
        conn.execute(
            text(
                """
                INSERT INTO schema_migrations (version, script_name, checksum, status, notes)
                VALUES (:version, :script_name, :checksum, :status, :notes)
                """
            ),
            {
                "version": MIGRATION_VERSION,
                "script_name": MIGRATION_SCRIPT,
                "checksum": "",
                "status": "applied",
                "notes": "auto-applied on startup",
            },
        )
