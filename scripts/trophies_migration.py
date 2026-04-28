#!/usr/bin/env python3
"""Trophies DB Migration. Use --standalone for direct DB."""
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
    if USE_STANDALONE:
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
        if 'trophy_definitions' not in t:
            conn.execute(text("""CREATE TABLE trophy_definitions (
                id VARCHAR(100) PRIMARY KEY, name VARCHAR(200) NOT NULL, description TEXT,
                category VARCHAR(50), icon VARCHAR(20) DEFAULT '🏆', rarity VARCHAR(20) DEFAULT 'common',
                criteria_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""))
            applied.append("trophy_definitions")
        if 'user_trophy_unlocks' not in t:
            conn.execute(text("""CREATE TABLE user_trophy_unlocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id VARCHAR(100) NOT NULL, trophy_id VARCHAR(100) NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, trophy_id))"""))
            applied.append("user_trophy_unlocks")
        t = inspector.get_table_names()
        for idx_name, tbl, col in [("idx_trophy_def_category", "trophy_definitions", "category"),
                                    ("idx_user_trophy_user", "user_trophy_unlocks", "user_id")]:
            if tbl not in t:
                continue
            existing = [i['name'] for i in inspector.get_indexes(tbl)]
            if idx_name not in existing:
                try:
                    conn.execute(text("CREATE INDEX %s ON %s(%s)" % (idx_name, tbl, col)))
                    applied.append(idx_name)
                except Exception:
                    pass
        if 'trophy_definitions' in t:
            r = conn.execute(text("SELECT COUNT(*) FROM trophy_definitions")).scalar()
            if r == 0:
                for tid, name, desc, cat in [('first_win', 'First Victory', 'Win your first battle', 'battle'),
                                             ('ten_wins', 'Ten Wins', 'Win 10 battles', 'battle'),
                                             ('shopper', 'Shopper', 'First shop purchase', 'shop')]:
                    try:
                        conn.execute(text("INSERT INTO trophy_definitions (id,name,description,category) VALUES (:a,:b,:c,:d)"),
                                    {'a': tid, 'b': name, 'c': desc, 'd': cat})
                        applied.append("seed")
                    except Exception:
                        pass
    print("Trophies migration done.", applied)
    return applied

if __name__ == '__main__':
    run_migration()
