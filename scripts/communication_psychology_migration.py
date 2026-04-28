#!/usr/bin/env python3
"""Communication Psychology DB migration: theory unlocks and activity log. Run after trophies_migration."""
import os
import sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except Exception:
    pass
from sqlalchemy import text, inspect

USE_STANDALONE = '--standalone' in sys.argv


def run_migration():
    if USE_STANDALONE:
        from sqlalchemy import create_engine
        url = os.getenv('DATABASE_URL') or 'sqlite:///documentary_generator.db'
        engine = create_engine(url)
        inspector = inspect(engine)
        conn_context = engine.begin()
    else:
        from src.app import create_app
        from src.db.models import db
        create_app().app_context().push()
        inspector = inspect(db.engine)
        conn_context = db.engine.begin()

    applied = []
    with conn_context as conn:
        t = inspector.get_table_names()

        if 'comm_psych_theory_unlocks' not in t:
            conn.execute(text("""
                CREATE TABLE comm_psych_theory_unlocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    theory_id VARCHAR(80) NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    UNIQUE(user_id, theory_id)
                )
            """))
            applied.append("comm_psych_theory_unlocks")

        if 'comm_psych_activity_log' not in t:
            conn.execute(text("""
                CREATE TABLE comm_psych_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    activity_type VARCHAR(50) NOT NULL,
                    theory_id VARCHAR(80),
                    amount REAL DEFAULT 0,
                    source VARCHAR(100),
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            applied.append("comm_psych_activity_log")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comm_psych_unlocks_user ON comm_psych_theory_unlocks(user_id)"))
            applied.append("idx_comm_psych_unlocks_user")
        except Exception:
            pass
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comm_psych_activity_user ON comm_psych_activity_log(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comm_psych_activity_created ON comm_psych_activity_log(created_at)"))
            applied.append("idx_comm_psych_activity")
        except Exception:
            pass

    print("Communication psychology migration done.", applied)
    return applied


if __name__ == '__main__':
    run_migration()
