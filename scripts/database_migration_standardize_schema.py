#!/usr/bin/env python3
"""
Database Migration: Standardize Schema
Creates standardized database schema for all tables
"""
import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class DatabaseMigration:
    """Standardize database schema"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.migrations_applied = []
    
    def run_migration(self):
        """Run all migrations"""
        print("=" * 80)
        print("DATABASE SCHEMA STANDARDIZATION MIGRATION")
        print("=" * 80)
        print()
        
        # 1. Standardize player_levels
        print("1. Standardizing player_levels table...")
        self.migrate_player_levels()
        print()
        
        # 2. Ensure system_point_snapshots exists
        print("2. Ensuring system_point_snapshots table...")
        self.migrate_system_point_snapshots()
        print()
        
        # 3. Ensure user_profiles exists
        print("3. Ensuring user_profiles table...")
        self.migrate_user_profiles()
        print()
        
        # 4. Ensure xp_history exists
        print("4. Ensuring xp_history table...")
        self.migrate_xp_history()
        print()
        
        # 5. Ensure daily_activities exists
        print("5. Ensuring daily_activities table...")
        self.migrate_daily_activities()
        print()
        
        # 6. Create indexes
        print("6. Creating indexes...")
        self.create_indexes()
        print()
        
        # Summary
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Applied {len(self.migrations_applied)} migrations:")
        for migration in self.migrations_applied:
            print(f"   [OK] {migration}")
        print()
        print("Migration complete!")
        print()
    
    def migrate_player_levels(self):
        """Standardize player_levels table"""
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'player_levels' not in tables:
                print("   Creating player_levels table...")
                db.session.execute(text("""
                    CREATE TABLE player_levels (
                        user_id VARCHAR(100) PRIMARY KEY,
                        level INTEGER DEFAULT 1,
                        total_xp INTEGER DEFAULT 0,
                        current_level_xp INTEGER DEFAULT 0,
                        xp_to_next_level INTEGER DEFAULT 1000,
                        level_progress DECIMAL(5,2) DEFAULT 0.0,
                        title VARCHAR(50) DEFAULT 'Novice Hunter',
                        prestige_level INTEGER DEFAULT 0,
                        stat_creativity INTEGER DEFAULT 0,
                        stat_efficiency INTEGER DEFAULT 0,
                        stat_quality INTEGER DEFAULT 0,
                        stat_social INTEGER DEFAULT 0,
                        stat_knowledge INTEGER DEFAULT 0,
                        available_stat_points INTEGER DEFAULT 0,
                        unlocked_themes TEXT,
                        unlocked_templates TEXT,
                        xp_bonus_percent INTEGER DEFAULT 0,
                        xp_bonus_remaining INTEGER DEFAULT 0,
                        prestige_xp_bonus INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created player_levels table")
            else:
                # Check and add missing columns
                columns = {col['name'] for col in inspector.get_columns('player_levels')}
                
                # Add missing columns
                column_definitions = {
                    'level': 'INTEGER DEFAULT 1',
                    'total_xp': 'INTEGER DEFAULT 0',
                    'current_level_xp': 'INTEGER DEFAULT 0',
                    'xp_to_next_level': 'INTEGER DEFAULT 1000',
                    'level_progress': 'DECIMAL(5,2) DEFAULT 0.0',
                    'title': "VARCHAR(50) DEFAULT 'Novice Hunter'",
                    'prestige_level': 'INTEGER DEFAULT 0',
                    'stat_creativity': 'INTEGER DEFAULT 0',
                    'stat_efficiency': 'INTEGER DEFAULT 0',
                    'stat_quality': 'INTEGER DEFAULT 0',
                    'stat_social': 'INTEGER DEFAULT 0',
                    'stat_knowledge': 'INTEGER DEFAULT 0',
                    'available_stat_points': 'INTEGER DEFAULT 0',
                    'unlocked_themes': 'TEXT',
                    'unlocked_templates': 'TEXT',
                    'xp_bonus_percent': 'INTEGER DEFAULT 0',
                    'xp_bonus_remaining': 'INTEGER DEFAULT 0',
                    'prestige_xp_bonus': 'INTEGER DEFAULT 0',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }
                
                added_columns = []
                for col_name, col_def in column_definitions.items():
                    if col_name not in columns:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE player_levels 
                                ADD COLUMN {col_name} {col_def}
                            """))
                            added_columns.append(col_name)
                        except Exception as e:
                            print(f"   [WARN] Could not add {col_name}: {str(e)}")
                
                if added_columns:
                    db.session.commit()
                    self.migrations_applied.append(f"Added columns to player_levels: {', '.join(added_columns)}")
                    print(f"   [OK] Added {len(added_columns)} columns")
                else:
                    print("   [OK] player_levels table is up to date")
            
        except Exception as e:
            print(f"   [ERROR] Migration failed: {str(e)}")
            db.session.rollback()
    
    def migrate_system_point_snapshots(self):
        """Ensure system_point_snapshots table exists"""
        try:
            inspector = inspect(db.engine)
            if 'system_point_snapshots' not in inspector.get_table_names():
                print("   Creating system_point_snapshots table...")
                db.session.execute(text("""
                    CREATE TABLE system_point_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        system_name VARCHAR(100) NOT NULL,
                        point_value DECIMAL(15,2) DEFAULT 0,
                        snapshot_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created system_point_snapshots table")
                print("   [OK] Created system_point_snapshots table")
            else:
                print("   [OK] system_point_snapshots table exists")
        except Exception as e:
            print(f"   [ERROR] Migration failed: {str(e)}")
            db.session.rollback()
    
    def migrate_user_profiles(self):
        """Ensure user_profiles table exists"""
        try:
            inspector = inspect(db.engine)
            if 'user_profiles' not in inspector.get_table_names():
                print("   Creating user_profiles table...")
                db.session.execute(text("""
                    CREATE TABLE user_profiles (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(100) UNIQUE NOT NULL,
                        username VARCHAR(100),
                        preferences TEXT,
                        agent_skillset_id VARCHAR(100),
                        assigned_agent_ids TEXT,
                        skill_levels TEXT,
                        scraped_info TEXT,
                        onboarding_complete BOOLEAN DEFAULT 0,
                        onboarding_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created user_profiles table")
                print("   [OK] Created user_profiles table")
            else:
                print("   [OK] user_profiles table exists")
        except Exception as e:
            print(f"   [ERROR] Migration failed: {str(e)}")
            db.session.rollback()
    
    def migrate_xp_history(self):
        """Ensure xp_history table exists"""
        try:
            inspector = inspect(db.engine)
            if 'xp_history' not in inspector.get_table_names():
                print("   Creating xp_history table...")
                db.session.execute(text("""
                    CREATE TABLE xp_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        xp_amount INTEGER NOT NULL,
                        source VARCHAR(50) NOT NULL,
                        action_type VARCHAR(50),
                        metadata TEXT,
                        level_before INTEGER,
                        level_after INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created xp_history table")
                print("   [OK] Created xp_history table")
            else:
                print("   [OK] xp_history table exists")
        except Exception as e:
            print(f"   [ERROR] Migration failed: {str(e)}")
            db.session.rollback()
    
    def migrate_daily_activities(self):
        """Ensure daily_activities table exists"""
        try:
            inspector = inspect(db.engine)
            if 'daily_activities' not in inspector.get_table_names():
                print("   Creating daily_activities table...")
                db.session.execute(text("""
                    CREATE TABLE daily_activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        activity_date DATE NOT NULL,
                        last_login TIMESTAMP,
                        streak INTEGER DEFAULT 0,
                        login_count INTEGER DEFAULT 0,
                        xp_earned_today INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, activity_date)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created daily_activities table")
                print("   [OK] Created daily_activities table")
            else:
                print("   [OK] daily_activities table exists")
        except Exception as e:
            print(f"   [ERROR] Migration failed: {str(e)}")
            db.session.rollback()
    
    def create_indexes(self):
        """Create indexes for better performance"""
        indexes = [
            ("player_levels", "idx_player_levels_level", "level"),
            ("player_levels", "idx_player_levels_total_xp", "total_xp"),
            ("system_point_snapshots", "idx_snapshots_user_id", "user_id"),
            ("system_point_snapshots", "idx_snapshots_system_name", "system_name"),
            ("system_point_snapshots", "idx_snapshots_created_at", "created_at"),
            ("xp_history", "idx_xp_history_user_id", "user_id"),
            ("xp_history", "idx_xp_history_created_at", "created_at"),
            ("daily_activities", "idx_daily_activities_user_date", "user_id, activity_date"),
        ]
        
        created = 0
        for table, index_name, columns in indexes:
            try:
                # Check if index exists (SQLite doesn't have a direct way, so we'll try to create)
                db.session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})
                """))
                created += 1
            except Exception as e:
                # Index might already exist or table might not exist
                pass
        
        if created > 0:
            db.session.commit()
            self.migrations_applied.append(f"Created {created} indexes")
            print(f"   [OK] Created {created} indexes")
        else:
            print("   [OK] Indexes are up to date")


def main():
    """Main entry point"""
    migration = DatabaseMigration()
    migration.run_migration()


if __name__ == '__main__':
    main()
