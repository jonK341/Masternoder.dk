#!/usr/bin/env python3
"""Gallery DB Migration. Creates gallery_items, user_gallery_state, gallery_downloads. Use --standalone for direct DB."""
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
        if 'gallery_items' not in t:
            conn.execute(text("""CREATE TABLE gallery_items (
                id VARCHAR(200) PRIMARY KEY,
                title VARCHAR(500),
                file_path TEXT,
                status VARCHAR(50) DEFAULT 'completed',
                duration INTEGER DEFAULT 0,
                category_name VARCHAR(100),
                description TEXT,
                prompt TEXT,
                quality_level VARCHAR(50),
                quality_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            applied.append("gallery_items")
        if 'user_gallery_state' not in t:
            conn.execute(text("""CREATE TABLE user_gallery_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) NOT NULL,
                item_id VARCHAR(200) NOT NULL,
                last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_id)
            )"""))
            applied.append("user_gallery_state")
        if 'gallery_downloads' not in t:
            conn.execute(text("""CREATE TABLE gallery_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) NOT NULL,
                item_id VARCHAR(200) NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            applied.append("gallery_downloads")
        t = inspector.get_table_names()
        for idx_name, tbl, col in [
            ("idx_gallery_items_category", "gallery_items", "category_name"),
            ("idx_user_gallery_state_user", "user_gallery_state", "user_id"),
            ("idx_gallery_downloads_user", "gallery_downloads", "user_id"),
            ("idx_gallery_downloads_item", "gallery_downloads", "item_id"),
        ]:
            if tbl not in t:
                continue
            existing = [i['name'] for i in inspector.get_indexes(tbl)]
            if idx_name not in existing:
                try:
                    conn.execute(text("CREATE INDEX %s ON %s(%s)" % (idx_name, tbl, col)))
                    applied.append(idx_name)
                except Exception:
                    pass
    print("Gallery migration done.", applied)
    return applied


if __name__ == '__main__':
    run_migration()
