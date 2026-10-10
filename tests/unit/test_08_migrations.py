"""
Unit tests for migration idempotency (nr 8): running migrations twice does not fail.
Run: pytest tests/unit/test_08_migrations.py -v
"""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_generator_migration_idempotent():
    """Run generator migration twice; second run should not raise and tables should exist."""
    from scripts.generator_migration import run_migration
    run_migration()
    applied2 = run_migration()
    assert applied2 is not None
    # Migration applies to the Flask app database (instance/database.db when
    # DATABASE_URL is unset), not a separate sqlite:///documentary_generator.db file.
    from sqlalchemy import inspect
    from src.app import create_app
    from src.db.models import db

    app = create_app()
    with app.app_context():
        tables = inspect(db.engine).get_table_names()
    assert 'video_generation_jobs' in tables
    assert 'job_artifacts' in tables
