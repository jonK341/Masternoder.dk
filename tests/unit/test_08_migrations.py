"""
Unit tests for migration idempotency (nr 8): running migrations twice does not fail.
Run: pytest tests/unit/test_08_migrations.py -v
"""
import os

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_generator_migration_idempotent():
    """Run generator migration twice; second run should not raise and tables should exist."""
    from scripts.generator_migration import run_migration
    run_migration()
    applied2 = run_migration()
    assert applied2 is not None
    from sqlalchemy import create_engine, inspect
    url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///documentary_generator.db'
    engine = create_engine(url)
    tables = inspect(engine).get_table_names()
    assert 'video_generation_jobs' in tables
    assert 'job_artifacts' in tables
