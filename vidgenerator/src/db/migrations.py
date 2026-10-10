"""
Database migration system
Tracks and applies database schema changes
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import inspect, text, Table, Column, MetaData
from sqlalchemy.exc import OperationalError

logger = logging.getLogger('vidgenerator.db.migrations')

# Migration registry - all migrations should be registered here
MIGRATIONS = []


class Migration:
    """Represents a database migration"""
    
    def __init__(self, version: str, name: str, up_func, down_func=None):
        """
        Initialize migration
        
        Args:
            version: Migration version (e.g., '001', '002')
            name: Human-readable migration name
            up_func: Function to apply migration
            down_func: Optional function to rollback migration
        """
        self.version = version
        self.name = name
        self.up_func = up_func
        self.down_func = down_func
    
    def apply(self, db, app) -> bool:
        """Apply this migration"""
        try:
            logger.info(f"Applying migration {self.version}: {self.name}")
            with app.app_context():
                result = self.up_func(db, app)
                if result:
                    self._record_migration(db, applied=True)
                return result
        except Exception as e:
            logger.error(f"Error applying migration {self.version}: {e}", exc_info=True)
            return False
    
    def rollback(self, db, app) -> bool:
        """Rollback this migration"""
        if not self.down_func:
            logger.warning(f"Migration {self.version} has no rollback function")
            return False
        
        try:
            logger.info(f"Rolling back migration {self.version}: {self.name}")
            with app.app_context():
                result = self.down_func(db, app)
                if result:
                    self._record_migration(db, applied=False)
                return result
        except Exception as e:
            logger.error(f"Error rolling back migration {self.version}: {e}", exc_info=True)
            return False
    
    def _record_migration(self, db, applied: bool):
        """Record migration in migrations table"""
        try:
            # Create migrations table if it doesn't exist
            inspector = inspect(db.engine)
            if 'migrations' not in inspector.get_table_names():
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE migrations (
                            version VARCHAR(10) PRIMARY KEY,
                            name VARCHAR(200) NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            applied BOOLEAN DEFAULT 1
                        )
                    """))
            
            # Record migration
            if applied:
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        INSERT OR REPLACE INTO migrations (version, name, applied_at, applied)
                        VALUES (:version, :name, CURRENT_TIMESTAMP, 1)
                    """), {"version": self.version, "name": self.name})
            else:
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        DELETE FROM migrations WHERE version = :version
                    """), {"version": self.version})
        except Exception as e:
            logger.warning(f"Could not record migration: {e}")


def get_applied_migrations(db, app) -> List[str]:
    """Get list of applied migration versions"""
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            if 'migrations' not in inspector.get_table_names():
                return []
            
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT version FROM migrations WHERE applied = 1 ORDER BY version
                """))
                return [row[0] for row in result]
    except Exception as e:
        logger.warning(f"Error getting applied migrations: {e}")
        return []


def run_migrations(db, app) -> bool:
    """
    Run all pending migrations
    
    Args:
        db: SQLAlchemy database instance
        app: Flask application instance
    
    Returns:
        True if all migrations succeeded, False otherwise
    """
    applied = set(get_applied_migrations(db, app))
    
    # Sort migrations by version
    sorted_migrations = sorted(MIGRATIONS, key=lambda m: m.version)
    
    success = True
    for migration in sorted_migrations:
        if migration.version not in applied:
            if not migration.apply(db, app):
                logger.error(f"Migration {migration.version} failed, stopping")
                success = False
                break
        else:
            logger.debug(f"Migration {migration.version} already applied, skipping")
    
    return success


# Register migrations
def migration_001_add_categories(db, app):
    """Migration 001: Add content categories support"""
    try:
        from src.db.models_content_categories import ContentCategory, CategoryStats
        
        # Create category tables
        ContentCategory.__table__.create(db.engine, checkfirst=True)
        CategoryStats.__table__.create(db.engine, checkfirst=True)
        
        # Add category columns to documentaries table
        inspector = inspect(db.engine)
        if 'documentaries' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('documentaries')]
            
            if 'category_id' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE documentaries ADD COLUMN category_id VARCHAR(36)"))
            
            if 'category_name' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE documentaries ADD COLUMN category_name VARCHAR(100)"))
            
            # Create indexes
            indexes = [idx['name'] for idx in inspector.get_indexes('documentaries')]
            if 'ix_documentaries_category_name' not in indexes:
                with db.engine.begin() as conn:
                    conn.execute(text("CREATE INDEX ix_documentaries_category_name ON documentaries(category_name)"))
        
        # Initialize default categories
        from src.services.content_categories import content_category_service
        content_category_service.ensure_default_categories()
        
        return True
    except Exception as e:
        logger.error(f"Migration 001 error: {e}", exc_info=True)
        return False

MIGRATIONS.append(Migration('001', 'add_content_categories', migration_001_add_categories))


def migration_002_optimize_indexes(db, app):
    """Migration 002: Add composite indexes for query optimization"""
    try:
        from sqlalchemy import text, inspect
        
        inspector = inspect(db.engine)
        existing_indexes = {}
        
        # Get all existing indexes
        for table_name in inspector.get_table_names():
            indexes = inspector.get_indexes(table_name)
            existing_indexes[table_name] = [idx['name'] for idx in indexes]
        
        with db.engine.begin() as conn:
            # Composite index for status + category_name
            if 'ix_documentaries_status_category' not in existing_indexes.get('documentaries', []):
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_documentaries_status_category 
                    ON documentaries(status, category_name)
                """))
            
            # Composite index for status + created_at
            if 'ix_documentaries_status_created' not in existing_indexes.get('documentaries', []):
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_documentaries_status_created 
                    ON documentaries(status, created_at DESC)
                """))
            
            # Index for quality_score on MovieClip
            if 'movie_clips' in existing_indexes:
                if 'ix_movie_clips_quality_score' not in existing_indexes['movie_clips']:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_movie_clips_quality_score 
                        ON movie_clips(quality_score DESC)
                    """))
                
                # Composite index for documentary_id + quality_score
                if 'ix_movie_clips_doc_id_quality' not in existing_indexes['movie_clips']:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_movie_clips_doc_id_quality 
                        ON movie_clips(documentary_id, quality_score DESC)
                    """))
        
        return True
    except Exception as e:
        logger.error(f"Migration 002 error: {e}", exc_info=True)
        return False

MIGRATIONS.append(Migration('002', 'optimize_indexes', migration_002_optimize_indexes))

