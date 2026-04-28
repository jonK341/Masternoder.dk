#!/usr/bin/env python3
"""Points analytics migration. Creates point_aggregates_daily for analytics. Use --standalone for direct DB."""
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
        url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///documentary_generator.db'
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
        if 'point_aggregates_daily' not in t:
            conn.execute(text("""CREATE TABLE point_aggregates_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) NOT NULL,
                aggregate_date DATE NOT NULL,
                system_name VARCHAR(100) NOT NULL,
                total_credits DECIMAL(15,2) DEFAULT 0,
                total_debits DECIMAL(15,2) DEFAULT 0,
                net_change DECIMAL(15,2) DEFAULT 0,
                transaction_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, aggregate_date, system_name)
            )"""))
            applied.append("point_aggregates_daily")
        t = inspector.get_table_names()
        for idx_name, tbl, col in [
            ("idx_point_agg_daily_user", "point_aggregates_daily", "user_id"),
            ("idx_point_agg_daily_date", "point_aggregates_daily", "aggregate_date"),
            ("idx_point_agg_daily_system", "point_aggregates_daily", "system_name"),
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
    print("Points migration done.", applied)
    return applied


if __name__ == '__main__':
    run_migration()
