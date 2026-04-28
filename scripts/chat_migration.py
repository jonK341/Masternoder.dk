#!/usr/bin/env python3
"""Chat DB Migration. Creates chat_sessions and chat_messages. Use --standalone for direct DB."""
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
        if 'chat_sessions' not in t:
            conn.execute(text("""CREATE TABLE chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            applied.append("chat_sessions")
        if 'chat_messages' not in t:
            conn.execute(text("""CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                username VARCHAR(200),
                message TEXT NOT NULL,
                is_ai BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )"""))
            applied.append("chat_messages")
        t = inspector.get_table_names()
        for idx_name, tbl, col in [
            ("idx_chat_sessions_user_id", "chat_sessions", "user_id"),
            ("idx_chat_messages_session_id", "chat_messages", "session_id"),
            ("idx_chat_messages_created_at", "chat_messages", "created_at"),
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
    print("Chat migration done.", applied)
    return applied


if __name__ == '__main__':
    run_migration()
