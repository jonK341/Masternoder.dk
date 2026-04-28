#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update All Point Tables
Ensures all point-related database tables are up to date with latest schema
"""
import os
import sys
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db

def update_all_point_tables():
    """Update all point tables to latest schema"""
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("UPDATING ALL POINT TABLES")
        print("=" * 80)
        print()
        
        inspector = inspect(db.engine)
        tables_updated = []
        tables_verified = []
        
        # List of all point tables
        point_tables = [
            'player_levels',
            'system_point_snapshots',
            'xp_history',
            'daily_activities',
            'point_transactions',
            'point_history',
            'point_aggregates',
            'point_analytics',
            'system_usage_stats'
        ]
        
        print("Checking point tables...")
        print()
        
        for table_name in point_tables:
            try:
                if table_name in inspector.get_table_names():
                    # Get current columns
                    columns = {col['name'] for col in inspector.get_columns(table_name)}
                    
                    # Define required columns for each table
                    required_columns = get_required_columns(table_name)
                    
                    # Check and add missing columns
                    added = []
                    for col_name, col_def in required_columns.items():
                        if col_name not in columns:
                            try:
                                db.session.execute(text(f"""
                                    ALTER TABLE {table_name} 
                                    ADD COLUMN {col_name} {col_def}
                                """))
                                added.append(col_name)
                            except Exception as e:
                                print(f"   [WARN] Could not add {col_name} to {table_name}: {e}")
                    
                    if added:
                        db.session.commit()
                        tables_updated.append(f"{table_name} - Added: {', '.join(added)}")
                        print(f"   [OK] {table_name} - Updated with {len(added)} new columns")
                    else:
                        tables_verified.append(table_name)
                        print(f"   [OK] {table_name} - Up to date")
                else:
                    print(f"   [INFO] {table_name} - Table does not exist (will be created by migration)")
            except Exception as e:
                print(f"   [ERROR] {table_name}: {e}")
        
        print()
        print("=" * 80)
        print("UPDATE SUMMARY")
        print("=" * 80)
        print()
        
        if tables_updated:
            print(f"Tables Updated: {len(tables_updated)}")
            for update in tables_updated:
                print(f"   - {update}")
            print()
        
        if tables_verified:
            print(f"Tables Verified (up to date): {len(tables_verified)}")
            for table in tables_verified:
                print(f"   - {table}")
            print()
        
        print("All point tables checked and updated!")
        print()

def get_required_columns(table_name):
    """Get required columns for each table"""
    columns = {
        'player_levels': {
            'level': 'INTEGER DEFAULT 1',
            'total_xp': 'INTEGER DEFAULT 0',
            'current_level_xp': 'INTEGER DEFAULT 0',
            'xp_to_next_level': 'INTEGER DEFAULT 1000',
            'level_progress': 'DECIMAL(5,2) DEFAULT 0.0',
            'title': 'VARCHAR(50) DEFAULT \'Novice Hunter\'',
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
        },
        'system_point_snapshots': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'system_name': 'VARCHAR(100) NOT NULL',
            'point_value': 'DECIMAL(15,2) DEFAULT 0',
            'previous_value': 'DECIMAL(15,2) DEFAULT 0',
            'delta': 'DECIMAL(15,2) DEFAULT 0',
            'snapshot_data': 'TEXT',
            'source': 'VARCHAR(100)',
            'metadata': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'xp_history': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'xp_amount': 'INTEGER NOT NULL',
            'source': 'VARCHAR(50) NOT NULL',
            'action_type': 'VARCHAR(50)',
            'metadata': 'TEXT',
            'level_before': 'INTEGER',
            'level_after': 'INTEGER',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'daily_activities': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'activity_date': 'DATE NOT NULL',
            'last_login': 'TIMESTAMP',
            'streak': 'INTEGER DEFAULT 0',
            'login_count': 'INTEGER DEFAULT 0',
            'xp_earned_today': 'INTEGER DEFAULT 0',
            'points_earned_today': 'INTEGER DEFAULT 0',
            'systems_active_today': 'INTEGER DEFAULT 0',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'point_transactions': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'system_name': 'VARCHAR(100) NOT NULL',
            'transaction_type': 'VARCHAR(50) NOT NULL',
            'amount': 'DECIMAL(15,2) NOT NULL',
            'balance_before': 'DECIMAL(15,2) DEFAULT 0',
            'balance_after': 'DECIMAL(15,2) DEFAULT 0',
            'source': 'VARCHAR(100)',
            'reference_id': 'VARCHAR(100)',
            'metadata': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'point_history': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'system_name': 'VARCHAR(100) NOT NULL',
            'point_value': 'DECIMAL(15,2) NOT NULL',
            'change_amount': 'DECIMAL(15,2) DEFAULT 0',
            'change_percentage': 'DECIMAL(5,2) DEFAULT 0',
            'recorded_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'snapshot_date': 'DATE NOT NULL'
        },
        'point_aggregates': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'aggregate_type': 'VARCHAR(50) NOT NULL',
            'period_start': 'DATE NOT NULL',
            'period_end': 'DATE NOT NULL',
            'total_points': 'DECIMAL(15,2) DEFAULT 0',
            'systems_count': 'INTEGER DEFAULT 0',
            'active_systems': 'TEXT',
            'growth_rate': 'DECIMAL(5,2) DEFAULT 0',
            'aggregate_data': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'point_analytics': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'analysis_date': 'DATE NOT NULL',
            'total_points': 'DECIMAL(15,2) DEFAULT 0',
            'systems_active': 'INTEGER DEFAULT 0',
            'top_systems': 'TEXT',
            'growth_trend': 'VARCHAR(50)',
            'growth_rate': 'DECIMAL(5,2) DEFAULT 0',
            'insights': 'TEXT',
            'recommendations': 'TEXT',
            'analytics_data': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        },
        'system_usage_stats': {
            'user_id': 'VARCHAR(100) NOT NULL',
            'system_name': 'VARCHAR(100) NOT NULL',
            'usage_count': 'INTEGER DEFAULT 0',
            'total_points_earned': 'DECIMAL(15,2) DEFAULT 0',
            'last_used_at': 'TIMESTAMP',
            'first_used_at': 'TIMESTAMP',
            'average_points_per_use': 'DECIMAL(10,2) DEFAULT 0',
            'stats_data': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
    }
    
    return columns.get(table_name, {})

if __name__ == '__main__':
    try:
        update_all_point_tables()
        print("Point tables update complete!")
    except Exception as e:
        print(f"Error updating point tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
