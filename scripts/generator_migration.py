#!/usr/bin/env python3
"""Generator/Jobs DB Migration. Creates video_generation_jobs and job_artifacts. Use --standalone for direct DB."""
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
        if 'video_generation_jobs' not in t:
            conn.execute(text("""CREATE TABLE video_generation_jobs (
                job_id VARCHAR(100) PRIMARY KEY,
                user_id VARCHAR(100),
                job_type VARCHAR(50) DEFAULT 'documentary',
                status VARCHAR(50) DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                theme VARCHAR(200),
                config TEXT,
                clips TEXT,
                video_url VARCHAR(500),
                error_message TEXT,
                estimated_time INTEGER DEFAULT 0,
                actual_time INTEGER DEFAULT 0,
                points_earned REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )"""))
            applied.append("video_generation_jobs")
        if 'job_artifacts' not in t:
            conn.execute(text("""CREATE TABLE job_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(100) NOT NULL,
                artifact_type VARCHAR(50) DEFAULT 'video',
                file_path VARCHAR(500),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""))
            applied.append("job_artifacts")
        t = inspector.get_table_names()
        for idx_name, tbl, col in [
            ("idx_video_jobs_user", "video_generation_jobs", "user_id"),
            ("idx_video_jobs_status", "video_generation_jobs", "status"),
            ("idx_video_jobs_created", "video_generation_jobs", "created_at"),
            ("idx_job_artifacts_job", "job_artifacts", "job_id"),
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
    print("Generator migration done.", applied)
    return applied


if __name__ == '__main__':
    run_migration()
