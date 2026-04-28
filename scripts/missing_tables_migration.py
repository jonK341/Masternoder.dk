#!/usr/bin/env python3
"""
Missing Tables Database Migration
Creates all missing tables identified by the requirements analysis
"""
import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class MissingTablesMigration:
    """Create all missing database tables"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.migrations_applied = []
    
    def run_migration(self):
        """Run all migrations for missing tables"""
        print("=" * 80)
        print("MISSING TABLES DATABASE MIGRATION")
        print("=" * 80)
        print()
        
        # HIGH PRIORITY
        print("HIGH PRIORITY TABLES:")
        print("1. Creating agent_missions table...")
        self.create_agent_missions()
        print()
        
        print("2. Creating agent_quests table...")
        self.create_agent_quests()
        print()
        
        print("3. Creating agent_personality table...")
        self.create_agent_personality()
        print()
        
        # MEDIUM PRIORITY
        print("MEDIUM PRIORITY TABLES:")
        print("4. Creating agent_skill_history table...")
        self.create_agent_skill_history()
        print()
        
        print("5. Creating agent_ai_intelligence table...")
        self.create_agent_ai_intelligence()
        print()
        
        print("6. Creating agent_errors table...")
        self.create_agent_errors()
        print()
        
        print("7. Creating agent_use_cases table...")
        self.create_agent_use_cases()
        print()
        
        print("8. Creating video_generation_jobs table...")
        self.create_video_generation_jobs()
        print()
        
        # LOW PRIORITY
        print("LOW PRIORITY TABLES:")
        print("9. Creating dna_manipulation table...")
        self.create_dna_manipulation()
        print()
        
        # Create indexes
        print("10. Creating indexes...")
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
    
    def create_agent_missions(self):
        """Create agent_missions table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_missions' not in inspector.get_table_names():
                print("   Creating agent_missions table...")
                db.session.execute(text("""
                    CREATE TABLE agent_missions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mission_id VARCHAR(100) UNIQUE NOT NULL,
                        user_id VARCHAR(100),
                        mission_name VARCHAR(200) NOT NULL,
                        description TEXT,
                        tasks TEXT,
                        progress INTEGER DEFAULT 0,
                        total_tasks INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'pending',
                        rewards TEXT,
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        xp_earned INTEGER DEFAULT 0,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_missions table")
                print("   [OK] Created agent_missions table")
            else:
                print("   [OK] agent_missions table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_quests(self):
        """Create agent_quests table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_quests' not in inspector.get_table_names():
                print("   Creating agent_quests table...")
                db.session.execute(text("""
                    CREATE TABLE agent_quests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        quest_id VARCHAR(100) UNIQUE NOT NULL,
                        user_id VARCHAR(100),
                        quest_name VARCHAR(200) NOT NULL,
                        description TEXT,
                        objectives TEXT,
                        progress INTEGER DEFAULT 0,
                        total_objectives INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'available',
                        rewards TEXT,
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        xp_earned INTEGER DEFAULT 0,
                        achievements_unlocked TEXT,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_quests table")
                print("   [OK] Created agent_quests table")
            else:
                print("   [OK] agent_quests table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_personality(self):
        """Create agent_personality table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_personality' not in inspector.get_table_names():
                print("   Creating agent_personality table...")
                db.session.execute(text("""
                    CREATE TABLE agent_personality (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) UNIQUE NOT NULL,
                        agent_name VARCHAR(200) DEFAULT 'Master Fix Agent',
                        personality_type VARCHAR(50) DEFAULT 'analytical',
                        traits TEXT,
                        behavior_patterns TEXT,
                        preferences TEXT,
                        experience_level INTEGER DEFAULT 0,
                        experience_points INTEGER DEFAULT 0,
                        skills_unlocked TEXT,
                        achievements TEXT,
                        personality_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_personality table")
                print("   [OK] Created agent_personality table")
            else:
                print("   [OK] agent_personality table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_skill_history(self):
        """Create agent_skill_history table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_skill_history' not in inspector.get_table_names():
                print("   Creating agent_skill_history table...")
                db.session.execute(text("""
                    CREATE TABLE agent_skill_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100),
                        skill_name VARCHAR(100) NOT NULL,
                        action VARCHAR(100),
                        result VARCHAR(50),
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        xp_earned INTEGER DEFAULT 0,
                        execution_time DECIMAL(10,2) DEFAULT 0,
                        skill_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_skill_history table")
                print("   [OK] Created agent_skill_history table")
            else:
                print("   [OK] agent_skill_history table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_ai_intelligence(self):
        """Create agent_ai_intelligence table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_ai_intelligence' not in inspector.get_table_names():
                print("   Creating agent_ai_intelligence table...")
                db.session.execute(text("""
                    CREATE TABLE agent_ai_intelligence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100),
                        intelligence_type VARCHAR(50),
                        knowledge_data TEXT,
                        patterns TEXT,
                        predictions TEXT,
                        decisions TEXT,
                        learning_history TEXT,
                        strategies TEXT,
                        risk_assessments TEXT,
                        optimizations TEXT,
                        context_understanding TEXT,
                        intelligence_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_ai_intelligence table")
                print("   [OK] Created agent_ai_intelligence table")
            else:
                print("   [OK] agent_ai_intelligence table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_errors(self):
        """Create agent_errors table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_errors' not in inspector.get_table_names():
                print("   Creating agent_errors table...")
                db.session.execute(text("""
                    CREATE TABLE agent_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type VARCHAR(100),
                        error_message TEXT,
                        error_pattern VARCHAR(200),
                        category VARCHAR(50),
                        frequency INTEGER DEFAULT 1,
                        first_occurred TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_occurred TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        error_data TEXT,
                        stack_trace TEXT,
                        context_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_errors table")
                print("   [OK] Created agent_errors table")
            else:
                print("   [OK] agent_errors table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_agent_use_cases(self):
        """Create agent_use_cases table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_use_cases' not in inspector.get_table_names():
                print("   Creating agent_use_cases table...")
                db.session.execute(text("""
                    CREATE TABLE agent_use_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        use_case_id VARCHAR(100) UNIQUE NOT NULL,
                        error_id INTEGER,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        steps TEXT,
                        expected_result TEXT,
                        status VARCHAR(50) DEFAULT 'draft',
                        priority VARCHAR(20) DEFAULT 'medium',
                        tags TEXT,
                        use_case_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_use_cases table")
                print("   [OK] Created agent_use_cases table")
            else:
                print("   [OK] agent_use_cases table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_video_generation_jobs(self):
        """Create video_generation_jobs table"""
        try:
            inspector = inspect(db.engine)
            if 'video_generation_jobs' not in inspector.get_table_names():
                print("   Creating video_generation_jobs table...")
                db.session.execute(text("""
                    CREATE TABLE video_generation_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id VARCHAR(100) UNIQUE NOT NULL,
                        user_id VARCHAR(100),
                        job_type VARCHAR(50) DEFAULT 'documentary',
                        status VARCHAR(50) DEFAULT 'pending',
                        progress INTEGER DEFAULT 0,
                        theme VARCHAR(100),
                        config TEXT,
                        clips TEXT,
                        video_url VARCHAR(500),
                        error_message TEXT,
                        estimated_time INTEGER DEFAULT 0,
                        actual_time INTEGER DEFAULT 0,
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created video_generation_jobs table")
                print("   [OK] Created video_generation_jobs table")
            else:
                print("   [OK] video_generation_jobs table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_dna_manipulation(self):
        """Create dna_manipulation table"""
        try:
            inspector = inspect(db.engine)
            if 'dna_manipulation' not in inspector.get_table_names():
                print("   Creating dna_manipulation table...")
                db.session.execute(text("""
                    CREATE TABLE dna_manipulation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        manipulation_type VARCHAR(50) NOT NULL,
                        dna_data TEXT,
                        cloning_data TEXT,
                        manipulation_result TEXT,
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        dna_points DECIMAL(15,2) DEFAULT 0,
                        cloning_points DECIMAL(15,2) DEFAULT 0,
                        manipulation_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created dna_manipulation table")
                print("   [OK] Created dna_manipulation table")
            else:
                print("   [OK] dna_manipulation table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_indexes(self):
        """Create indexes for all new tables"""
        indexes = [
            # agent_missions indexes
            ("agent_missions", "idx_missions_user_id", "user_id"),
            ("agent_missions", "idx_missions_status", "status"),
            ("agent_missions", "idx_missions_mission_id", "mission_id"),
            
            # agent_quests indexes
            ("agent_quests", "idx_quests_user_id", "user_id"),
            ("agent_quests", "idx_quests_status", "status"),
            ("agent_quests", "idx_quests_quest_id", "quest_id"),
            
            # agent_personality indexes
            ("agent_personality", "idx_personality_user_id", "user_id"),
            ("agent_personality", "idx_personality_type", "personality_type"),
            
            # agent_skill_history indexes
            ("agent_skill_history", "idx_skill_history_user_id", "user_id"),
            ("agent_skill_history", "idx_skill_history_skill", "skill_name"),
            ("agent_skill_history", "idx_skill_history_created", "created_at"),
            
            # agent_ai_intelligence indexes
            ("agent_ai_intelligence", "idx_intelligence_user_id", "user_id"),
            ("agent_ai_intelligence", "idx_intelligence_type", "intelligence_type"),
            
            # agent_errors indexes
            ("agent_errors", "idx_errors_type", "error_type"),
            ("agent_errors", "idx_errors_category", "category"),
            ("agent_errors", "idx_errors_last_occurred", "last_occurred"),
            
            # agent_use_cases indexes
            ("agent_use_cases", "idx_use_cases_error_id", "error_id"),
            ("agent_use_cases", "idx_use_cases_status", "status"),
            ("agent_use_cases", "idx_use_cases_use_case_id", "use_case_id"),
            
            # video_generation_jobs indexes
            ("video_generation_jobs", "idx_video_jobs_user_id", "user_id"),
            ("video_generation_jobs", "idx_video_jobs_status", "status"),
            ("video_generation_jobs", "idx_video_jobs_job_id", "job_id"),
            ("video_generation_jobs", "idx_video_jobs_created", "created_at"),
            
            # dna_manipulation indexes
            ("dna_manipulation", "idx_dna_user_id", "user_id"),
            ("dna_manipulation", "idx_dna_type", "manipulation_type"),
        ]
        
        created = 0
        for table, index_name, columns in indexes:
            try:
                db.session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})
                """))
                created += 1
            except Exception:
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
    migration = MissingTablesMigration()
    migration.run_migration()


if __name__ == '__main__':
    main()
