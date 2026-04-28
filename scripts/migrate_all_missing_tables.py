#!/usr/bin/env python3
"""
Migrate All Missing Tables
Creates all missing database tables for user profiles, onboarding, calculations, and game systems
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_user_profile_tables(db):
    """Create user profile related tables"""
    print("Creating user profile tables...")
    
    # User Profiles
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            preferences TEXT,
            scraped_info TEXT,
            agent_skillset_id TEXT,
            assigned_agent_ids TEXT,
            skill_levels TEXT,
            onboarding_complete BOOLEAN DEFAULT 0,
            onboarding_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User Scraped Info
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS user_scraped_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            info_type TEXT NOT NULL,
            info_data TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
    """)
    
    # User Agent Skills
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS user_agent_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            skill_level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
    """)
    
    # Onboarding Progress
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            onboarding_started TIMESTAMP,
            onboarding_completed TIMESTAMP,
            current_step TEXT,
            completed_steps TEXT,
            skipped_steps TEXT,
            progress_percentage INTEGER DEFAULT 0,
            skill_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
    """)
    
    print("  ✓ User profile tables created")
    db.session.commit()

def create_calculator_tables(db):
    """Create advanced calculator tables"""
    print("Creating calculator tables...")
    
    # Calculation History
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS calculation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            calculation_type TEXT NOT NULL,
            final_total REAL,
            confidence_score REAL,
            points_restored REAL DEFAULT 0,
            calculation_data TEXT,
            system_breakdown TEXT,
            multipliers_applied TEXT,
            insights TEXT,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Point Loss Detection
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS point_loss_detection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            points_lost REAL,
            systems_affected INTEGER,
            detection_confidence REAL,
            detection_method TEXT,
            affected_systems TEXT,
            loss_breakdown TEXT,
            resolved BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Repair Log
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS repair_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            calculation_id INTEGER,
            loss_detection_id INTEGER,
            points_restored REAL,
            repair_method TEXT,
            success BOOLEAN DEFAULT 0,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (calculation_id) REFERENCES calculation_history(id),
            FOREIGN KEY (loss_detection_id) REFERENCES point_loss_detection(id)
        )
    """)
    
    # Predictions
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            prediction_type TEXT NOT NULL,
            predicted_value REAL,
            confidence_interval_lower REAL,
            confidence_interval_upper REAL,
            prediction_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Pattern Analysis
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS pattern_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_data TEXT,
            insights TEXT,
            recommendations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Anomaly Detection
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_detection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            anomaly_type TEXT NOT NULL,
            severity TEXT,
            anomaly_data TEXT,
            auto_fixed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # System Point Snapshots
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS system_point_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            system_name TEXT NOT NULL,
            point_value REAL,
            snapshot_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("  ✓ Calculator tables created")
    db.session.commit()

def create_game_tables(db):
    """Create game system tables"""
    print("Creating game tables...")
    
    # Player Levels
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS player_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            level INTEGER DEFAULT 1,
            total_xp INTEGER DEFAULT 0,
            current_level_xp INTEGER DEFAULT 0,
            xp_to_next_level INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # XP History
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS xp_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            xp_amount INTEGER NOT NULL,
            xp_source TEXT,
            source_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES player_levels(user_id)
        )
    """)
    
    # Daily Activities
    db.session.execute("""
        CREATE TABLE IF NOT EXISTS daily_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            activity_date DATE NOT NULL,
            login_xp INTEGER DEFAULT 0,
            activity_xp INTEGER DEFAULT 0,
            total_xp INTEGER DEFAULT 0,
            activities_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, activity_date)
        )
    """)
    
    print("  ✓ Game tables created")
    db.session.commit()

def create_indexes(db):
    """Create indexes for better performance"""
    print("Creating indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_scraped_info_user_id ON user_scraped_info(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_agent_skills_user_id ON user_agent_skills(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_onboarding_user_id ON onboarding_progress(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_calc_history_user_id ON calculation_history(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_loss_detection_user_id ON point_loss_detection(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_xp_history_user_id ON xp_history(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_daily_activities_user_id ON daily_activities(user_id)",
    ]
    
    for index_sql in indexes:
        try:
            db.session.execute(index_sql)
        except Exception as e:
            print(f"  ⚠ Warning creating index: {e}")
    
    db.session.commit()
    print("  ✓ Indexes created")

def main():
    """Main migration function"""
    print("=" * 70)
    print("MIGRATE ALL MISSING TABLES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        
        app = create_app()
        with app.app_context():
            print("Creating all missing tables...")
            print()
            
            # Create user profile tables
            create_user_profile_tables(db)
            
            # Create calculator tables
            create_calculator_tables(db)
            
            # Create game tables
            create_game_tables(db)
            
            # Create indexes
            create_indexes(db)
            
            print()
            print("=" * 70)
            print("MIGRATION COMPLETE")
            print("=" * 70)
            print()
            print("✓ All tables created successfully!")
            print()
            print("Created tables:")
            print("  - User Profiles: user_profiles, user_scraped_info, user_agent_skills, onboarding_progress")
            print("  - Calculator: calculation_history, point_loss_detection, repair_log, predictions, pattern_analysis, anomaly_detection, system_point_snapshots")
            print("  - Game: player_levels, xp_history, daily_activities")
            print()
            
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
