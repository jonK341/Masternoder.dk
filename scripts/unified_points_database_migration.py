#!/usr/bin/env python3
"""
Unified Points System Database Migration
Creates all tables needed for the unified points system supporting 178 point systems
"""
import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class UnifiedPointsMigration:
    """Complete database migration for unified points system"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.migrations_applied = []
    
    def run_migration(self):
        """Run all migrations for unified points system"""
        print("=" * 80)
        print("UNIFIED POINTS SYSTEM DATABASE MIGRATION")
        print("=" * 80)
        print()
        
        # 1. Core tables
        print("1. Creating core tables...")
        self.create_player_levels()
        self.create_system_point_snapshots()
        self.create_xp_history()
        self.create_daily_activities()
        print()
        
        # 2. Point tracking tables
        print("2. Creating point tracking tables...")
        self.create_point_transactions()
        self.create_point_history()
        self.create_point_aggregates()
        print()
        
        # 3. Analytics tables
        print("3. Creating analytics tables...")
        self.create_point_analytics()
        self.create_system_usage_stats()
        print()
        
        # 4. Indexes
        print("4. Creating indexes...")
        self.create_indexes()
        print()
        
        # 5. Summary
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
    
    def create_player_levels(self):
        """Create/update player_levels table"""
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
                # Ensure all columns exist
                columns = {col['name'] for col in inspector.get_columns('player_levels')}
                required_columns = {
                    'level': 'INTEGER DEFAULT 1',
                    'total_xp': 'INTEGER DEFAULT 0',
                    'current_level_xp': 'INTEGER DEFAULT 0',
                    'xp_to_next_level': 'INTEGER DEFAULT 1000'
                }
                
                added = []
                for col_name, col_def in required_columns.items():
                    if col_name not in columns:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE player_levels 
                                ADD COLUMN {col_name} {col_def}
                            """))
                            added.append(col_name)
                        except Exception:
                            pass
                
                if added:
                    db.session.commit()
                    self.migrations_applied.append(f"Added columns to player_levels: {', '.join(added)}")
                print("   [OK] player_levels table ready")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_system_point_snapshots(self):
        """Create system_point_snapshots table for all 178 point systems"""
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
                        previous_value DECIMAL(15,2) DEFAULT 0,
                        delta DECIMAL(15,2) DEFAULT 0,
                        snapshot_data TEXT,
                        source VARCHAR(100),
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created system_point_snapshots table")
                print("   [OK] Created system_point_snapshots table")
            else:
                # Add new columns if missing
                columns = {col['name'] for col in inspector.get_columns('system_point_snapshots')}
                new_columns = {
                    'previous_value': 'DECIMAL(15,2) DEFAULT 0',
                    'delta': 'DECIMAL(15,2) DEFAULT 0',
                    'source': 'VARCHAR(100)',
                    'metadata': 'TEXT',
                    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }
                
                added = []
                for col_name, col_def in new_columns.items():
                    if col_name not in columns:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE system_point_snapshots 
                                ADD COLUMN {col_name} {col_def}
                            """))
                            added.append(col_name)
                        except Exception:
                            pass
                
                if added:
                    db.session.commit()
                    self.migrations_applied.append(f"Added columns to system_point_snapshots: {', '.join(added)}")
                print("   [OK] system_point_snapshots table ready")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_xp_history(self):
        """Create xp_history table"""
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
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_daily_activities(self):
        """Create daily_activities table"""
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
                        points_earned_today INTEGER DEFAULT 0,
                        systems_active_today INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, activity_date)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created daily_activities table")
                print("   [OK] Created daily_activities table")
            else:
                # Add new columns if missing
                columns = {col['name'] for col in inspector.get_columns('daily_activities')}
                new_columns = {
                    'points_earned_today': 'INTEGER DEFAULT 0',
                    'systems_active_today': 'INTEGER DEFAULT 0'
                }
                
                added = []
                for col_name, col_def in new_columns.items():
                    if col_name not in columns:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE daily_activities 
                                ADD COLUMN {col_name} {col_def}
                            """))
                            added.append(col_name)
                        except Exception:
                            pass
                
                if added:
                    db.session.commit()
                    self.migrations_applied.append(f"Added columns to daily_activities: {', '.join(added)}")
                print("   [OK] daily_activities table ready")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_point_transactions(self):
        """Create point_transactions table for tracking all point changes"""
        try:
            inspector = inspect(db.engine)
            if 'point_transactions' not in inspector.get_table_names():
                print("   Creating point_transactions table...")
                db.session.execute(text("""
                    CREATE TABLE point_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        system_name VARCHAR(100) NOT NULL,
                        transaction_type VARCHAR(50) NOT NULL,
                        amount DECIMAL(15,2) NOT NULL,
                        balance_before DECIMAL(15,2) DEFAULT 0,
                        balance_after DECIMAL(15,2) DEFAULT 0,
                        source VARCHAR(100),
                        reference_id VARCHAR(100),
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created point_transactions table")
                print("   [OK] Created point_transactions table")
            else:
                print("   [OK] point_transactions table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_point_history(self):
        """Create point_history table for historical point tracking"""
        try:
            inspector = inspect(db.engine)
            if 'point_history' not in inspector.get_table_names():
                print("   Creating point_history table...")
                db.session.execute(text("""
                    CREATE TABLE point_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        system_name VARCHAR(100) NOT NULL,
                        point_value DECIMAL(15,2) NOT NULL,
                        change_amount DECIMAL(15,2) DEFAULT 0,
                        change_percentage DECIMAL(5,2) DEFAULT 0,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        snapshot_date DATE NOT NULL
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created point_history table")
                print("   [OK] Created point_history table")
            else:
                print("   [OK] point_history table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_point_aggregates(self):
        """Create point_aggregates table for aggregated point data"""
        try:
            inspector = inspect(db.engine)
            if 'point_aggregates' not in inspector.get_table_names():
                print("   Creating point_aggregates table...")
                db.session.execute(text("""
                    CREATE TABLE point_aggregates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        aggregate_type VARCHAR(50) NOT NULL,
                        period_start DATE NOT NULL,
                        period_end DATE NOT NULL,
                        total_points DECIMAL(15,2) DEFAULT 0,
                        systems_count INTEGER DEFAULT 0,
                        active_systems TEXT,
                        growth_rate DECIMAL(5,2) DEFAULT 0,
                        aggregate_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, aggregate_type, period_start)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created point_aggregates table")
                print("   [OK] Created point_aggregates table")
            else:
                print("   [OK] point_aggregates table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_point_analytics(self):
        """Create point_analytics table for analytics data"""
        try:
            inspector = inspect(db.engine)
            if 'point_analytics' not in inspector.get_table_names():
                print("   Creating point_analytics table...")
                db.session.execute(text("""
                    CREATE TABLE point_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        analysis_date DATE NOT NULL,
                        total_points DECIMAL(15,2) DEFAULT 0,
                        systems_active INTEGER DEFAULT 0,
                        top_systems TEXT,
                        growth_trend VARCHAR(50),
                        growth_rate DECIMAL(5,2) DEFAULT 0,
                        insights TEXT,
                        recommendations TEXT,
                        analytics_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, analysis_date)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created point_analytics table")
                print("   [OK] Created point_analytics table")
            else:
                print("   [OK] point_analytics table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_system_usage_stats(self):
        """Create system_usage_stats table for tracking system usage"""
        try:
            inspector = inspect(db.engine)
            if 'system_usage_stats' not in inspector.get_table_names():
                print("   Creating system_usage_stats table...")
                db.session.execute(text("""
                    CREATE TABLE system_usage_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        system_name VARCHAR(100) NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        total_points_earned DECIMAL(15,2) DEFAULT 0,
                        last_used_at TIMESTAMP,
                        first_used_at TIMESTAMP,
                        average_points_per_use DECIMAL(10,2) DEFAULT 0,
                        stats_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, system_name)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created system_usage_stats table")
                print("   [OK] Created system_usage_stats table")
            else:
                print("   [OK] system_usage_stats table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_indexes(self):
        """Create indexes for performance"""
        indexes = [
            # player_levels indexes
            ("player_levels", "idx_player_levels_level", "level"),
            ("player_levels", "idx_player_levels_total_xp", "total_xp"),
            ("player_levels", "idx_player_levels_user_id", "user_id"),
            
            # system_point_snapshots indexes
            ("system_point_snapshots", "idx_snapshots_user_id", "user_id"),
            ("system_point_snapshots", "idx_snapshots_system_name", "system_name"),
            ("system_point_snapshots", "idx_snapshots_user_system", "user_id, system_name"),
            ("system_point_snapshots", "idx_snapshots_created_at", "created_at"),
            
            # xp_history indexes
            ("xp_history", "idx_xp_history_user_id", "user_id"),
            ("xp_history", "idx_xp_history_created_at", "created_at"),
            ("xp_history", "idx_xp_history_source", "source"),
            
            # daily_activities indexes
            ("daily_activities", "idx_daily_activities_user_date", "user_id, activity_date"),
            ("daily_activities", "idx_daily_activities_date", "activity_date"),
            
            # point_transactions indexes
            ("point_transactions", "idx_transactions_user_id", "user_id"),
            ("point_transactions", "idx_transactions_system", "system_name"),
            ("point_transactions", "idx_transactions_user_system", "user_id, system_name"),
            ("point_transactions", "idx_transactions_created_at", "created_at"),
            
            # point_history indexes
            ("point_history", "idx_history_user_id", "user_id"),
            ("point_history", "idx_history_system", "system_name"),
            ("point_history", "idx_history_user_system", "user_id, system_name"),
            ("point_history", "idx_history_snapshot_date", "snapshot_date"),
            
            # point_aggregates indexes
            ("point_aggregates", "idx_aggregates_user_id", "user_id"),
            ("point_aggregates", "idx_aggregates_type", "aggregate_type"),
            ("point_aggregates", "idx_aggregates_user_type", "user_id, aggregate_type"),
            
            # point_analytics indexes
            ("point_analytics", "idx_analytics_user_id", "user_id"),
            ("point_analytics", "idx_analytics_analysis_date", "analysis_date"),
            ("point_analytics", "idx_analytics_user_date", "user_id, analysis_date"),
            
            # system_usage_stats indexes
            ("system_usage_stats", "idx_usage_user_id", "user_id"),
            ("system_usage_stats", "idx_usage_system", "system_name"),
            ("system_usage_stats", "idx_usage_user_system", "user_id, system_name"),
        ]
        
        created = 0
        for table, index_name, columns in indexes:
            try:
                db.session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})
                """))
                created += 1
            except Exception as e:
                # Table might not exist or index already exists
                pass
        
        if created > 0:
            db.session.commit()
            self.migrations_applied.append(f"Created {created} indexes")
            print(f"   [OK] Created {created} indexes")
        else:
            print("   [OK] Indexes are up to date")


def main():
    """Main entry point"""
    migration = UnifiedPointsMigration()
    migration.run_migration()


if __name__ == '__main__':
    main()
