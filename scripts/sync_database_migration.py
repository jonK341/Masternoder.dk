#!/usr/bin/env python3
"""
Sync Device Database Migration
Creates sync_state and sync_audit tables for database-backed sync (replaces JSON file).
"""
import os
import sys
from sqlalchemy import text, inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


def run_migration():
    """Create sync_state and sync_audit tables."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        # 1. sync_state table
        if 'sync_state' not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE sync_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_sync_at TIMESTAMP,
                    last_sync_source VARCHAR(100),
                    sync_count INTEGER DEFAULT 0,
                    state_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.execute(text("INSERT INTO sync_state (id, sync_count) VALUES (1, 0)"))
            db.session.commit()
            print("   [OK] Created sync_state table")
        else:
            print("   [OK] sync_state table exists")

        # 2. sync_domain_state table (per-domain last_sync_at, count)
        if 'sync_domain_state' not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE sync_domain_state (
                    domain VARCHAR(100) PRIMARY KEY,
                    last_sync_at TIMESTAMP,
                    count INTEGER,
                    extra_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            print("   [OK] Created sync_domain_state table")
        else:
            print("   [OK] sync_domain_state table exists")

        # 3. sync_audit table (append-only audit log)
        if 'sync_audit' not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE sync_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain VARCHAR(100) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    source VARCHAR(100),
                    user_id VARCHAR(100),
                    count INTEGER,
                    extra_json TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.execute(text("CREATE INDEX idx_sync_audit_domain ON sync_audit(domain)"))
            db.session.execute(text("CREATE INDEX idx_sync_audit_created ON sync_audit(created_at)"))
            db.session.commit()
            print("   [OK] Created sync_audit table")
        else:
            print("   [OK] sync_audit table exists")

        # 4. sync_health table (success/failure counts per domain)
        if 'sync_health' not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE sync_health (
                    domain VARCHAR(100) NOT NULL,
                    metric_date DATE NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_success_at TIMESTAMP,
                    last_failure_at TIMESTAMP,
                    last_error_message TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (domain, metric_date)
                )
            """))
            db.session.commit()
            print("   [OK] Created sync_health table")
        else:
            print("   [OK] sync_health table exists")


if __name__ == '__main__':
    print("=" * 60)
    print("SYNC DATABASE MIGRATION")
    print("=" * 60)
    run_migration()
    print("Done.")
