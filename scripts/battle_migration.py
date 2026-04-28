#!/usr/bin/env python3
"""Battle System DB Migration. Creates battle_matches.

Usage:
  python scripts/battle_migration.py --standalone
Uses DATABASE_URL / SQLALCHEMY_DATABASE_URI or defaults to sqlite:///documentary_generator.db

In-app (Flask context):
  python scripts/battle_migration.py
"""
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
from sqlalchemy import text, inspect, create_engine
USE_STANDALONE = '--standalone' in sys.argv

def run_migration():
    db = None
    if USE_STANDALONE:
        url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///documentary_generator.db'
        engine = create_engine(url)
        conn = engine.connect()
        inspector = inspect(engine)
    else:
        from src.app import create_app
        from src.db.models import db
        create_app().app_context().push()
        conn = db.engine.connect()
        inspector = inspect(db.engine)
    applied = []
    def execute(stmt, params=None):
        if params:
            conn.execute(text(stmt), params)
        else:
            conn.execute(text(stmt))
        # SQLAlchemy Connection in standalone mode may not expose commit();
        # app-context mode should commit via Flask-SQLAlchemy session.
        if USE_STANDALONE:
            tx = getattr(conn, "commit", None)
            if callable(tx):
                tx()
        elif db is not None:
            db.session.commit()
    tables = inspector.get_table_names()
    if 'battle_matches' not in tables:
        print("Creating battle_matches...")
        execute("""CREATE TABLE battle_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(100) NOT NULL,
            battle_id VARCHAR(50) NOT NULL,
            opponent_type VARCHAR(20) DEFAULT 'ai',
            difficulty VARCHAR(20) DEFAULT 'balanced',
            result VARCHAR(10) NOT NULL CHECK(result IN ('win', 'loss', 'draw')),
            points_delta INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        applied.append("battle_matches")
    for name, table, col in [("idx_battle_matches_user_id", "battle_matches", "user_id"),
                             ("idx_battle_matches_created_at", "battle_matches", "created_at")]:
        if table not in inspector.get_table_names():
            continue
        existing = [i['name'] for i in inspector.get_indexes(table)]
        if name not in existing:
            try:
                execute("CREATE INDEX %s ON %s(%s)" % (name, table, col))
                applied.append(name)
            except Exception as e:
                print("Warn:", e)
    if USE_STANDALONE:
        conn.close()
    print("Battle migration done. Applied:", applied or ["none"])
    return applied

if __name__ == '__main__':
    run_migration()
