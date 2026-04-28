"""
Database Helper Functions
Utility functions for common database operations
"""
import json
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
            {
                "mission_id": mission_data.get('mission_id') or mission_data.get('id'),
                "user_id": mission_data.get('user_id'),
                "mission_name": mission_data.get('mission_name') or mission_data.get('name', 'Unknown Mission'),
                "description": mission_data.get('description', ''),
                "tasks": json.dumps(mission_data.get('tasks', [])),
                "progress": int(mission_data.get('progress', 0)),
                "total_tasks": int(mission_data.get('total_tasks', len(mission_data.get('tasks', [])))),
                "status": str(mission_data.get('status', 'pending')),
                "rewards": json.dumps(mission_data.get('rewards', {})),
                "points_earned": float(mission_data.get('points_earned', 0)),
                "xp_earned": int(mission_data.get('xp_earned', 0)),
                "started_at": mission_data.get('started_at'),
                "completed_at": mission_data.get('completed_at'),
            }
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_agent_mission(mission_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Get agent mission from database"""
    try:
        query = "SELECT * FROM agent_missions WHERE mission_id = :mission_id"
        params = {"mission_id": mission_id}
        
        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        
        result = db.session.execute(text(query), params).fetchone()
        
        if result:
            return {
                "mission_id": result[0],
                "user_id": result[1],
                "mission_name": result[2],
                "description": result[3],
                "tasks": json.loads(result[4]) if result[4] else [],
                "progress": result[5],
                "total_tasks": result[6],
                "status": result[7],
                "rewards": json.loads(result[8]) if result[8] else {},
                "points_earned": float(result[9] or 0),
                "xp_earned": result[10],
                "started_at": result[11].isoformat() if result[11] else None,
                "completed_at": result[12].isoformat() if result[12] else None,
            }
        return None
    except Exception:
        return None


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
            {
                "quest_id": quest_data.get('quest_id') or quest_data.get('id'),
                "user_id": quest_data.get('user_id'),
                "quest_name": quest_data.get('quest_name') or quest_data.get('name', 'Unknown Quest'),
                "description": quest_data.get('description', ''),
                "objectives": json.dumps(quest_data.get('objectives', [])),
                "progress": int(quest_data.get('progress', 0)),
                "total_objectives": int(quest_data.get('total_objectives', len(quest_data.get('objectives', [])))),
                "status": str(quest_data.get('status', 'available')),
                "rewards": json.dumps(quest_data.get('rewards', {})),
                "points_earned": float(quest_data.get('points_earned', 0)),
                "xp_earned": int(quest_data.get('xp_earned', 0)),
                "achievements_unlocked": json.dumps(quest_data.get('achievements_unlocked', [])),
                "started_at": quest_data.get('started_at'),
                "completed_at": quest_data.get('completed_at'),
            }
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def save_agent_personality(user_id: str, personality_data: Dict) -> bool:
    """Save agent personality to database"""
    try:
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
                "experience_level": int(personality_data.get('experience_level', 0)),
                "experience_points": int(personality_data.get('experience_points', 0)),
                "skills_unlocked": json.dumps(personality_data.get('skills_unlocked', [])),
                "achievements": json.dumps(personality_data.get('achievements', [])),
                "personality_data": json.dumps(personality_data),
            }
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_agent_personality(user_id: str) -> Optional[Dict]:
    """Get agent personality from database"""
    try:
        result = db.session.execute(
            text("SELECT * FROM agent_personality WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if result:
            return {
                "user_id": result[1],
                "name": result[2],
                "personality_type": result[3],
                "traits": json.loads(result[4]) if result[4] else [],
                "behavior_patterns": json.loads(result[5]) if result[5] else {},
                "preferences": json.loads(result[6]) if result[6] else {},
                "experience_level": result[7],
                "experience_points": result[8],
                "skills_unlocked": json.loads(result[9]) if result[9] else [],
                "achievements": json.loads(result[10]) if result[10] else [],
            }
        return None
    except Exception:
        return None


def save_skill_history(user_id: str, skill_name: str, action: str, result: str, 
                       points_earned: float = 0, xp_earned: int = 0, execution_time: float = 0,
                       skill_data: Optional[Dict] = None) -> bool:
    """Save skill history entry to database"""
    try:
        db.session.execute(
            text("""
                INSERT INTO agent_skill_history
                (user_id, skill_name, action, result, points_earned, xp_earned, execution_time, skill_data, created_at)
                VALUES (:user_id, :skill_name, :action, :result, :points_earned, :xp_earned, :execution_time, :skill_data, CURRENT_TIMESTAMP)
            """),
            {
                "user_id": user_id,
                "skill_name": skill_name,
                "action": action,
                "result": result,
                "points_earned": points_earned,
                "xp_earned": xp_earned,
                "execution_time": execution_time,
                "skill_data": json.dumps(skill_data) if skill_data else None,
            }
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
            {
                "job_id": job_data.get('job_id') or job_data.get('id'),
                "user_id": job_data.get('user_id'),
                "job_type": job_data.get('job_type') or job_data.get('type', 'documentary'),
                "status": job_data.get('status', 'pending'),
                "progress": int(job_data.get('progress', 0)),
                "theme": job_data.get('theme'),
                "config": json.dumps(job_data.get('config', {})),
                "clips": json.dumps(job_data.get('clips', [])),
                "video_url": job_data.get('video_url'),
                "error_message": job_data.get('error_message'),
                "estimated_time": int(job_data.get('estimated_time', 0)),
                "actual_time": int(job_data.get('actual_time', 0)),
                "points_earned": float(job_data.get('points_earned', 0)),
                "completed_at": job_data.get('completed_at'),
            }
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
