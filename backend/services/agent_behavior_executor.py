"""
Agent Behavior Executor
Executes agent behaviors and saves to database
"""
import os
import sys
from datetime import datetime
from typing import Dict, List
from sqlalchemy import text

class AgentBehaviorExecutor:
    """Executes agent behaviors and persists to database"""
    
    def __init__(self):
        self.behavior_system = None
        try:
            from backend.services.agent_player_behavior import agent_player_behavior
            self.behavior_system = agent_player_behavior
        except Exception as e:
            print(f"Warning: Could not load behavior system: {e}")
    
    def execute_and_save_session(self, agent_id: str, db) -> Dict:
        """Execute a session and save all actions to database"""
        if not self.behavior_system:
            return {'success': False, 'error': 'Behavior system not available'}
        
        try:
            # Generate session plan
            session_plan = self.behavior_system.generate_session_plan(agent_id)
            
            # Execute actions
            results = []
            total_xp = 0
            total_points = 0
            
            for action in session_plan['actions']:
                result = self.behavior_system.execute_action(agent_id, action)
                results.append(result)
                total_xp += result['xp_gained']
                total_points += result['points_gained']
                
                # Save to XP history
                self._save_xp_history(agent_id, result, db)
            
            # Update player level
            self._update_player_level(agent_id, total_xp, db)
            
            # Save daily activity
            self._save_daily_activity(agent_id, len(results), total_xp, db)
            
            return {
                'success': True,
                'agent_id': agent_id,
                'actions_executed': len(results),
                'total_xp': total_xp,
                'total_points': total_points,
                'session_plan': session_plan
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _save_xp_history(self, agent_id: str, action_result: Dict, db):
        """Save XP history entry"""
        try:
            db.session.execute(text("""
                INSERT INTO xp_history
                (user_id, xp_amount, xp_source, source_details, created_at)
                VALUES (:user_id, :xp, :source, :details, :created)
            """), {
                'user_id': agent_id,
                'xp': action_result['xp_gained'],
                'source': action_result['action_type'],
                'details': json.dumps(action_result['details']),
                'created': datetime.now()
            })
            db.session.commit()
        except Exception as e:
            print(f"Error saving XP history: {e}")
            db.session.rollback()
    
    def _update_player_level(self, agent_id: str, xp_gained: int, db):
        """Update player level with XP gained"""
        try:
            # Get current level
            result = db.session.execute(text("""
                SELECT level, total_xp FROM player_levels WHERE user_id = :user_id
            """), {'user_id': agent_id})
            row = result.fetchone()
            
            if row:
                current_level, current_xp = row
                new_xp = current_xp + xp_gained
                new_level = self._calculate_level(new_xp)
                
                # Update level
                db.session.execute(text("""
                    UPDATE player_levels
                    SET total_xp = :xp, level = :level, updated_at = :updated
                    WHERE user_id = :user_id
                """), {
                    'user_id': agent_id,
                    'xp': new_xp,
                    'level': new_level,
                    'updated': datetime.now()
                })
            else:
                # Create new level entry
                new_level = self._calculate_level(xp_gained)
                db.session.execute(text("""
                    INSERT INTO player_levels
                    (user_id, level, total_xp, current_level_xp, xp_to_next_level, created_at, updated_at)
                    VALUES (:user_id, :level, :xp, :current_xp, :next_xp, :created, :updated)
                """), {
                    'user_id': agent_id,
                    'level': new_level,
                    'xp': xp_gained,
                    'current_xp': xp_gained % (new_level * 100),
                    'next_xp': (new_level * 100) - (xp_gained % (new_level * 100)),
                    'created': datetime.now(),
                    'updated': datetime.now()
                })
            
            db.session.commit()
        except Exception as e:
            print(f"Error updating player level: {e}")
            db.session.rollback()
    
    def _save_daily_activity(self, agent_id: str, actions_count: int, xp_gained: int, db):
        """Save daily activity entry"""
        try:
            today = datetime.now().date()
            
            # Check if entry exists
            result = db.session.execute(text("""
                SELECT id, activity_xp, activities_completed FROM daily_activities
                WHERE user_id = :user_id AND activity_date = :date
            """), {'user_id': agent_id, 'date': today})
            row = result.fetchone()
            
            if row:
                # Update existing
                activity_id, current_xp, current_actions = row
                new_xp = current_xp + xp_gained
                new_actions = current_actions + actions_count
                
                db.session.execute(text("""
                    UPDATE daily_activities
                    SET activity_xp = :xp, activities_completed = :actions, total_xp = :total
                    WHERE id = :id
                """), {
                    'id': activity_id,
                    'xp': new_xp,
                    'actions': new_actions,
                    'total': new_xp
                })
            else:
                # Create new
                db.session.execute(text("""
                    INSERT INTO daily_activities
                    (user_id, activity_date, login_xp, activity_xp, total_xp, activities_completed, created_at)
                    VALUES (:user_id, :date, :login_xp, :activity_xp, :total, :actions, :created)
                """), {
                    'user_id': agent_id,
                    'date': today,
                    'login_xp': 0,
                    'activity_xp': xp_gained,
                    'total': xp_gained,
                    'actions': actions_count,
                    'created': datetime.now()
                })
            
            db.session.commit()
        except Exception as e:
            print(f"Error saving daily activity: {e}")
            db.session.rollback()
    
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP"""
        # Simple formula: level = sqrt(xp / 100)
        import math
        return max(1, int(math.sqrt(total_xp / 100)) + 1)

import json

# Global instance
agent_behavior_executor = AgentBehaviorExecutor()
