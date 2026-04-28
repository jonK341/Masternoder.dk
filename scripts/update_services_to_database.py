#!/usr/bin/env python3
"""
Update Services to Use Database
Updates services to use database instead of JSON file storage
"""
import os
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db
from sqlalchemy import text


class ServiceDatabaseUpdater:
    """Update services to use database"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.updates_applied = []
    
    def update_video_generation_service(self):
        """Update video generation to use database instead of in-memory"""
        try:
            routes_file = Path("backend/routes/missing_endpoints_routes.py")
            if not routes_file.exists():
                print("   [SKIP] missing_endpoints_routes.py not found")
                return
            
            content = routes_file.read_text(encoding='utf-8')
            
            # Check if already updated
            if 'video_generation_jobs' in content and 'INSERT INTO video_generation_jobs' in content:
                print("   [OK] Video generation already uses database")
                return
            
            # This would require manual code updates - just document it
            print("   [INFO] Video generation service needs manual update")
            print("   [INFO] Replace _video_jobs dictionary with database calls")
            print("   [INFO] Use video_generation_jobs table for persistence")
            
            self.updates_applied.append("Documented video generation database migration")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
    
    def create_database_helpers(self):
        """Create helper functions for database operations"""
        helpers_file = Path("backend/utils/database_helpers.py")
        
        if helpers_file.exists():
            print("   [OK] database_helpers.py already exists")
            return
        
        helpers_content = '''"""
Database Helper Functions
Utility functions for common database operations
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import text
from src.db.models import db


def save_agent_mission(mission_data: Dict) -> bool:
    """Save agent mission to database"""
    try:
        db.session.execute(
            text("""
                INSERT OR REPLACE INTO agent_missions
                (mission_id, user_id, mission_name, description, tasks, progress, total_tasks,
                 status, rewards, points_earned, xp_earned, started_at, completed_at, created_at, updated_at)
                VALUES (:mission_id, :user_id, :mission_name, :description, :tasks, :progress, :total_tasks,
                        :status, :rewards, :points_earned, :xp_earned, :started_at, :completed_at,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            mission_data
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def save_agent_quest(quest_data: Dict) -> bool:
    """Save agent quest to database"""
    try:
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
            quest_data
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def save_video_job(job_data: Dict) -> bool:
    """Save video generation job to database"""
    try:
        db.session.execute(
            text("""
                INSERT OR REPLACE INTO video_generation_jobs
                (job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                 error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at)
                VALUES (:job_id, :user_id, :job_type, :status, :progress, :theme, :config, :clips, :video_url,
                        :error_message, :estimated_time, :actual_time, :points_earned, CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP, :completed_at)
            """),
            job_data
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_video_job(job_id: str) -> Optional[Dict]:
    """Get video generation job from database"""
    try:
        result = db.session.execute(
            text("""
                SELECT job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                       error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at
                FROM video_generation_jobs
                WHERE job_id = :job_id
            """),
            {"job_id": job_id}
        ).fetchone()
        
        if result:
            return {
                "id": result[0],
                "user_id": result[1],
                "type": result[2],
                "status": result[3],
                "progress": result[4],
                "theme": result[5],
                "config": json.loads(result[6]) if result[6] else {},
                "clips": json.loads(result[7]) if result[7] else [],
                "video_url": result[8],
                "error_message": result[9],
                "estimated_time": result[10],
                "actual_time": result[11],
                "points_earned": float(result[12] or 0),
                "created_at": result[13].isoformat() if result[13] else None,
                "updated_at": result[14].isoformat() if result[14] else None,
                "completed_at": result[15].isoformat() if result[15] else None,
            }
        return None
    except Exception:
        return None
'''
        
        # Create directory if needed
        helpers_file.parent.mkdir(parents=True, exist_ok=True)
        helpers_file.write_text(helpers_content, encoding='utf-8')
        
        self.updates_applied.append("Created database_helpers.py")
        print("   [OK] Created database_helpers.py")


def main():
    """Main entry point"""
    updater = ServiceDatabaseUpdater()
    print("=" * 80)
    print("SERVICE DATABASE UPDATER")
    print("=" * 80)
    print()
    
    print("1. Creating database helpers...")
    updater.create_database_helpers()
    print()
    
    print("2. Checking video generation service...")
    updater.update_video_generation_service()
    print()
    
    print("=" * 80)
    print("UPDATES SUMMARY")
    print("=" * 80)
    print()
    for update in updater.updates_applied:
        print(f"   [OK] {update}")
    print()


if __name__ == '__main__':
    import json
    main()
