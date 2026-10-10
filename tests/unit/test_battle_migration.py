"""Stage 0: battle_matches migration is idempotent and creates the history table."""
from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine, inspect, text

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_battle_migration_standalone_creates_battle_matches(tmp_path, monkeypatch):
    db_file = tmp_path / "battle_test.db"
    url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(sys, "argv", ["battle_migration.py", "--standalone"])

    import importlib
    import scripts.battle_migration as bm

    importlib.reload(bm)
    applied = bm.run_migration()
    assert "battle_matches" in applied

    engine = create_engine(url)
    assert "battle_matches" in inspect(engine).get_table_names()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO battle_matches "
                "(user_id, battle_id, opponent_type, difficulty, result, points_delta) "
                "VALUES ('u1', 'b1', 'ai', 'balanced', 'win', 5)"
            )
        )
    with engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM battle_matches")).scalar()
        assert row == 1

    applied2 = bm.run_migration()
    assert "battle_matches" not in applied2
