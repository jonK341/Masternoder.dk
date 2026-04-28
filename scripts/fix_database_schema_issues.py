#!/usr/bin/env python3
"""
Fix Database Schema Issues
Fixes missing columns and schema inconsistencies
"""
import os
import sys
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class DatabaseSchemaFixer:
    """Fix database schema issues"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.fixes_applied = []
    
    def fix_all_issues(self):
        """Fix all schema issues"""
        print("=" * 80)
        print("DATABASE SCHEMA FIXER")
        print("=" * 80)
        print()
        
        # 1. Fix system_point_snapshots
        print("1. Fixing system_point_snapshots table...")
        self.fix_system_point_snapshots()
        print()
        
        # 2. Verify all tables
        print("2. Verifying all tables...")
        self.verify_tables()
        print()
        
        # Summary
        print("=" * 80)
        print("FIX SUMMARY")
        print("=" * 80)
        print()
        if self.fixes_applied:
            for fix in self.fixes_applied:
                print(f"   [OK] {fix}")
        else:
            print("   [OK] No fixes needed - all schemas are correct")
        print()
    
    def fix_system_point_snapshots(self):
        """Fix system_point_snapshots table schema"""
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'system_point_snapshots' not in tables:
                print("   [SKIP] Table does not exist - run migration first")
                return
            
            columns = {col['name'] for col in inspector.get_columns('system_point_snapshots')}
            
            # Check for updated_at column
            if 'updated_at' not in columns:
                try:
                    db.session.execute(text("""
                        ALTER TABLE system_point_snapshots 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    db.session.commit()
                    self.fixes_applied.append("Added updated_at column to system_point_snapshots")
                    print("   [OK] Added updated_at column")
                except Exception as e:
                    print(f"   [WARN] Could not add updated_at: {str(e)}")
            else:
                print("   [OK] updated_at column exists")
            
            # Check for other required columns
            required_columns = {
                'previous_value': 'DECIMAL(15,2) DEFAULT 0',
                'delta': 'DECIMAL(15,2) DEFAULT 0',
                'source': 'VARCHAR(100)',
                'metadata': 'TEXT'
            }
            
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    try:
                        db.session.execute(text(f"""
                            ALTER TABLE system_point_snapshots 
                            ADD COLUMN {col_name} {col_def}
                        """))
                        db.session.commit()
                        self.fixes_applied.append(f"Added {col_name} column to system_point_snapshots")
                        print(f"   [OK] Added {col_name} column")
                    except Exception as e:
                        print(f"   [WARN] Could not add {col_name}: {str(e)}")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def verify_tables(self):
        """Verify all required tables exist"""
        required_tables = [
            'player_levels', 'system_point_snapshots', 'xp_history',
            'point_transactions', 'point_history', 'point_aggregates',
            'point_analytics', 'system_usage_stats'
        ]
        
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        
        missing = []
        for table in required_tables:
            if table not in existing_tables:
                missing.append(table)
        
        if missing:
            print(f"   [WARN] Missing tables: {', '.join(missing)}")
            print("   [INFO] Run migration scripts to create missing tables")
        else:
            print(f"   [OK] All {len(required_tables)} required tables exist")


def main():
    """Main entry point"""
    fixer = DatabaseSchemaFixer()
    fixer.fix_all_issues()


if __name__ == '__main__':
    main()
