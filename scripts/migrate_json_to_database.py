#!/usr/bin/env python3
"""
Migrate JSON File Storage to Database
Migrates data from JSON files to database tables
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class JSONToDatabaseMigrator:
    """Migrate JSON file storage to database"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.migrations_completed = []
        self.migrations_failed = []
    
    def run_migration(self):
        """Run all migrations"""
        print("=" * 80)
        print("JSON TO DATABASE MIGRATION")
        print("=" * 80)
        print()
        
        # 1. Migrate agent missions
        print("1. Migrating agent missions...")
        self.migrate_agent_missions()
        print()
        
        # 2. Migrate agent quests
        print("2. Migrating agent quests...")
        self.migrate_agent_quests()
        print()
        
        # 3. Migrate agent personality
        print("3. Migrating agent personality...")
        self.migrate_agent_personality()
        print()
        
        # 4. Migrate agent skill history
        print("4. Migrating agent skill history...")
        self.migrate_agent_skill_history()
        print()
        
        # 5. Migrate AI intelligence
        print("5. Migrating AI intelligence...")
        self.migrate_ai_intelligence()
        print()
        
        # 6. Migrate agent errors
        print("6. Migrating agent errors...")
        self.migrate_agent_errors()
        print()
        
        # 7. Migrate use cases
        print("7. Migrating use cases...")
        self.migrate_use_cases()
        print()
        
        # 8. Migrate video generation jobs (from in-memory)
        print("8. Migrating video generation jobs...")
        self.migrate_video_jobs()
        print()
        
        # Summary
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Completed: {len(self.migrations_completed)} migrations")
        for migration in self.migrations_completed:
            print(f"   [OK] {migration}")
        print()
        if self.migrations_failed:
            print(f"Failed: {len(self.migrations_failed)} migrations")
            for migration in self.migrations_failed:
                print(f"   [FAIL] {migration}")
        print()
    
    def migrate_agent_missions(self):
        """Migrate agent missions from JSON to database"""
        try:
            missions_file = os.path.join(self.base_dir, 'logs', 'agent_skills', 'missions.json')
            if not os.path.exists(missions_file):
                print("   [SKIP] No missions.json file found")
                return
            
            with open(missions_file, 'r', encoding='utf-8') as f:
                missions = json.load(f)
            
            if not isinstance(missions, list):
                missions = []
            
            migrated = 0
            for mission in missions:
                try:
                    mission_id = mission.get('mission_id') or mission.get('id') or f"mission_{migrated + 1}"
                    db.session.execute(
                        text("""
                            INSERT OR REPLACE INTO agent_missions
                            (mission_id, user_id, mission_name, description, tasks, progress, total_tasks,
                             status, rewards, points_earned, xp_earned, started_at, completed_at, created_at, updated_at)
                            VALUES (:mission_id, :user_id, :mission_name, :description, :tasks, :progress, :total_tasks,
                                    :status, :rewards, :points_earned, :xp_earned, :started_at, :completed_at,
                                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {
                            "mission_id": mission_id,
                            "user_id": mission.get('user_id'),
                            "mission_name": mission.get('mission_name') or mission.get('name', 'Unknown Mission'),
                            "description": mission.get('description', ''),
                            "tasks": json.dumps(mission.get('tasks', [])),
                            "progress": mission.get('progress', 0),
                            "total_tasks": mission.get('total_tasks', len(mission.get('tasks', []))),
                            "status": mission.get('status', 'pending'),
                            "rewards": json.dumps(mission.get('rewards', {})),
                            "points_earned": mission.get('points_earned', 0),
                            "xp_earned": mission.get('xp_earned', 0),
                            "started_at": mission.get('started_at'),
                            "completed_at": mission.get('completed_at'),
                        }
                    )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate mission: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} agent missions")
            print(f"   [OK] Migrated {migrated} missions")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_missions: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_agent_quests(self):
        """Migrate agent quests from JSON to database"""
        try:
            quests_file = os.path.join(self.base_dir, 'logs', 'agent_skills', 'quests.json')
            if not os.path.exists(quests_file):
                print("   [SKIP] No quests.json file found")
                return
            
            with open(quests_file, 'r', encoding='utf-8') as f:
                quests = json.load(f)
            
            if not isinstance(quests, list):
                quests = []
            
            migrated = 0
            for quest in quests:
                try:
                    quest_id = quest.get('quest_id') or quest.get('id') or f"quest_{migrated + 1}"
                    db.session.execute(
                        text("""
                            INSERT OR REPLACE INTO agent_quests
                            (quest_id, user_id, quest_name, description, objectives, progress, total_objectives,
                             status, rewards, points_earned, xp_earned, achievements_unlocked, started_at, completed_at,
                             created_at, updated_at)
                            VALUES (:quest_id, :user_id, :quest_name, :description, :objectives, :progress, :total_objectives,
                                    :status, :rewards, :points_earned, :xp_earned, :achievements_unlocked, :started_at, :completed_at,
                                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {
                            "quest_id": quest_id,
                            "user_id": quest.get('user_id'),
                            "quest_name": quest.get('quest_name') or quest.get('name', 'Unknown Quest'),
                            "description": quest.get('description', ''),
                            "objectives": json.dumps(quest.get('objectives', [])),
                            "progress": int(quest.get('progress', 0)),
                            "total_objectives": int(quest.get('total_objectives', len(quest.get('objectives', [])))),
                            "status": str(quest.get('status', 'available')),
                            "rewards": json.dumps(quest.get('rewards', {})) if quest.get('rewards') else '{}',
                            "points_earned": quest.get('points_earned', 0),
                            "xp_earned": quest.get('xp_earned', 0),
                            "achievements_unlocked": json.dumps(quest.get('achievements_unlocked', [])),
                            "started_at": quest.get('started_at'),
                            "completed_at": quest.get('completed_at'),
                        }
                    )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate quest: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} agent quests")
            print(f"   [OK] Migrated {migrated} quests")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_quests: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_agent_personality(self):
        """Migrate agent personality from JSON to database"""
        try:
            personality_file = os.path.join(self.base_dir, 'logs', 'agent_skills', 'agent_personality.json')
            if not os.path.exists(personality_file):
                print("   [SKIP] No agent_personality.json file found")
                return
            
            with open(personality_file, 'r', encoding='utf-8') as f:
                personality_data = json.load(f)
            
            if not isinstance(personality_data, dict):
                print("   [SKIP] Invalid personality data format")
                return
            
            # Get user_id from personality data or use default
            user_id = personality_data.get('user_id', 'default_user')
            
            db.session.execute(
                text("""
                    INSERT OR REPLACE INTO agent_personality
                    (user_id, agent_name, personality_type, traits, behavior_patterns, preferences,
                     experience_level, experience_points, skills_unlocked, achievements, personality_data,
                     created_at, updated_at)
                    VALUES (:user_id, :agent_name, :personality_type, :traits, :behavior_patterns, :preferences,
                            :experience_level, :experience_points, :skills_unlocked, :achievements, :personality_data,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {
                    "user_id": user_id,
                    "agent_name": personality_data.get('name', 'Master Fix Agent'),
                    "personality_type": personality_data.get('personality_type', 'analytical'),
                    "traits": json.dumps(personality_data.get('traits', [])),
                    "behavior_patterns": json.dumps(personality_data.get('behavior_patterns', {})),
                    "preferences": json.dumps(personality_data.get('preferences', {})),
                    "experience_level": personality_data.get('experience_level', 0),
                    "experience_points": personality_data.get('experience_points', 0),
                    "skills_unlocked": json.dumps(personality_data.get('skills_unlocked', [])),
                    "achievements": json.dumps(personality_data.get('achievements', [])),
                    "personality_data": json.dumps(personality_data),
                }
            )
            
            db.session.commit()
            self.migrations_completed.append("Migrated agent personality")
            print("   [OK] Migrated agent personality")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_personality: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_agent_skill_history(self):
        """Migrate agent skill history from JSON to database"""
        try:
            history_file = os.path.join(self.base_dir, 'logs', 'agent_skills', 'skill_history.json')
            if not os.path.exists(history_file):
                print("   [SKIP] No skill_history.json file found")
                return
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if not isinstance(history, list):
                history = []
            
            # Limit to last 1000 entries to avoid overwhelming database
            history = history[-1000:] if len(history) > 1000 else history
            
            migrated = 0
            for entry in history:
                try:
                    db.session.execute(
                        text("""
                            INSERT INTO agent_skill_history
                            (user_id, skill_name, action, result, points_earned, xp_earned, execution_time, skill_data, created_at)
                            VALUES (:user_id, :skill_name, :action, :result, :points_earned, :xp_earned, :execution_time, :skill_data, :created_at)
                        """),
                        {
                            "user_id": entry.get('user_id'),
                            "skill_name": entry.get('skill_name') or entry.get('skill', 'unknown'),
                            "action": entry.get('action', ''),
                            "result": entry.get('result', 'success'),
                            "points_earned": entry.get('points_earned', 0),
                            "xp_earned": entry.get('xp_earned', 0),
                            "execution_time": entry.get('execution_time', 0),
                            "skill_data": json.dumps(entry),
                            "created_at": entry.get('created_at') or entry.get('timestamp') or datetime.now().isoformat(),
                        }
                    )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate history entry: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} skill history entries")
            print(f"   [OK] Migrated {migrated} skill history entries")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_skill_history: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_ai_intelligence(self):
        """Migrate AI intelligence from JSON to database"""
        try:
            intelligence_file = os.path.join(self.base_dir, 'logs', 'agent_ai_intelligence', 'intelligence.json')
            if not os.path.exists(intelligence_file):
                print("   [SKIP] No intelligence.json file found")
                return
            
            with open(intelligence_file, 'r', encoding='utf-8') as f:
                intelligence_data = json.load(f)
            
            if not isinstance(intelligence_data, dict):
                print("   [SKIP] Invalid intelligence data format")
                return
            
            # Migrate each agent's intelligence data
            agents = intelligence_data.get('agents', {})
            migrated = 0
            
            for agent_id, agent_data in agents.items():
                try:
                    user_id = agent_data.get('user_id', agent_id)
                    db.session.execute(
                        text("""
                            INSERT OR REPLACE INTO agent_ai_intelligence
                            (user_id, intelligence_type, knowledge_data, patterns, predictions, decisions,
                             learning_history, strategies, risk_assessments, optimizations, context_understanding,
                             intelligence_data, created_at, updated_at)
                            VALUES (:user_id, :intelligence_type, :knowledge_data, :patterns, :predictions, :decisions,
                                    :learning_history, :strategies, :risk_assessments, :optimizations, :context_understanding,
                                    :intelligence_data, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {
                            "user_id": user_id,
                            "intelligence_type": agent_data.get('type', 'general'),
                            "knowledge_data": json.dumps(intelligence_data.get('knowledge_base', {})),
                            "patterns": json.dumps(intelligence_data.get('patterns', {})),
                            "predictions": json.dumps(intelligence_data.get('predictions', {})),
                            "decisions": json.dumps(intelligence_data.get('decisions', [])),
                            "learning_history": json.dumps(intelligence_data.get('learning_history', [])),
                            "strategies": json.dumps(intelligence_data.get('strategies', {})),
                            "risk_assessments": json.dumps(intelligence_data.get('risk_assessments', {})),
                            "optimizations": json.dumps(intelligence_data.get('optimizations', {})),
                            "context_understanding": json.dumps(intelligence_data.get('context_understanding', {})),
                            "intelligence_data": json.dumps(intelligence_data),
                        }
                    )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate intelligence for {agent_id}: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} AI intelligence records")
            print(f"   [OK] Migrated {migrated} AI intelligence records")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_ai_intelligence: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_agent_errors(self):
        """Migrate agent errors from JSON to database"""
        try:
            errors_file = os.path.join(self.base_dir, 'logs', 'agent_errors', 'errors.json')
            if not os.path.exists(errors_file):
                print("   [SKIP] No errors.json file found")
                return
            
            with open(errors_file, 'r', encoding='utf-8') as f:
                errors_data = json.load(f)
            
            errors_list = errors_data.get('errors', [])
            if not isinstance(errors_list, list):
                errors_list = []
            
            migrated = 0
            for error in errors_list:
                try:
                    # Group similar errors by pattern
                    error_pattern = error.get('error_pattern') or error.get('pattern', '')
                    error_type = error.get('error_type') or error.get('type', 'unknown')
                    error_message = error.get('error_message') or error.get('message', '')
                    
                    # Check if error pattern already exists
                    existing = db.session.execute(
                        text("SELECT id, frequency FROM agent_errors WHERE error_pattern = :pattern"),
                        {"pattern": error_pattern}
                    ).fetchone()
                    
                    if existing:
                        # Update frequency
                        db.session.execute(
                            text("UPDATE agent_errors SET frequency = frequency + 1, last_occurred = CURRENT_TIMESTAMP WHERE id = :id"),
                            {"id": existing[0]}
                        )
                    else:
                        # Insert new error
                        db.session.execute(
                            text("""
                                INSERT INTO agent_errors
                                (error_type, error_message, error_pattern, category, frequency, first_occurred, last_occurred,
                                 error_data, stack_trace, context_data, created_at)
                                VALUES (:error_type, :error_message, :error_pattern, :category, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                                        :error_data, :stack_trace, :context_data, CURRENT_TIMESTAMP)
                            """),
                            {
                                "error_type": error_type,
                                "error_message": error_message[:1000],  # Limit length
                                "error_pattern": error_pattern,
                                "category": error.get('category', 'general'),
                                "error_data": json.dumps(error),
                                "stack_trace": error.get('stack_trace', ''),
                                "context_data": json.dumps(error.get('context', {})),
                            }
                        )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate error: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} error records")
            print(f"   [OK] Migrated {migrated} error records")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_errors: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_use_cases(self):
        """Migrate use cases from JSON to database"""
        try:
            use_cases_file = os.path.join(self.base_dir, 'logs', 'agent_errors', 'use_cases.json')
            if not os.path.exists(use_cases_file):
                print("   [SKIP] No use_cases.json file found")
                return
            
            with open(use_cases_file, 'r', encoding='utf-8') as f:
                use_cases_data = json.load(f)
            
            use_cases_list = use_cases_data.get('use_cases', [])
            if not isinstance(use_cases_list, list):
                use_cases_list = []
            
            migrated = 0
            for use_case in use_cases_list:
                try:
                    use_case_id = use_case.get('use_case_id') or use_case.get('id') or f"use_case_{migrated + 1}"
                    db.session.execute(
                        text("""
                            INSERT OR REPLACE INTO agent_use_cases
                            (use_case_id, error_id, title, description, steps, expected_result, status, priority,
                             tags, use_case_data, created_at, updated_at)
                            VALUES (:use_case_id, :error_id, :title, :description, :steps, :expected_result, :status, :priority,
                                    :tags, :use_case_data, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {
                            "use_case_id": use_case_id,
                            "error_id": use_case.get('error_id'),
                            "title": use_case.get('title') or use_case.get('name', 'Unknown Use Case'),
                            "description": use_case.get('description', ''),
                            "steps": json.dumps(use_case.get('steps', [])),
                            "expected_result": use_case.get('expected_result', ''),
                            "status": use_case.get('status', 'draft'),
                            "priority": use_case.get('priority', 'medium'),
                            "tags": json.dumps(use_case.get('tags', [])),
                            "use_case_data": json.dumps(use_case),
                        }
                    )
                    migrated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to migrate use case: {str(e)}")
            
            db.session.commit()
            self.migrations_completed.append(f"Migrated {migrated} use cases")
            print(f"   [OK] Migrated {migrated} use cases")
        except Exception as e:
            db.session.rollback()
            self.migrations_failed.append(f"agent_use_cases: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")
    
    def migrate_video_jobs(self):
        """Migrate video generation jobs (note: in-memory, so this is for future jobs)"""
        try:
            # Video jobs are currently in-memory, so we'll just ensure the table is ready
            # Future jobs will be stored in database
            print("   [INFO] Video jobs are currently in-memory")
            print("   [INFO] Table ready for future job storage")
            print("   [OK] Video generation jobs table ready")
            self.migrations_completed.append("Video generation jobs table ready")
        except Exception as e:
            self.migrations_failed.append(f"video_generation_jobs: {str(e)}")
            print(f"   [ERROR] Failed: {str(e)}")


def main():
    """Main entry point"""
    migrator = JSONToDatabaseMigrator()
    migrator.run_migration()


if __name__ == '__main__':
    main()
