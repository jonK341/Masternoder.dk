"""
Agent Achievements Service
Manages achievements for agent tasks and activities
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AgentAchievements:
    """Agent achievements system"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.achievements_file = os.path.join(self.base_dir, 'logs', 'agent_achievements', 'achievements.json')
        self.load_achievements()
    
    def load_achievements(self):
        """Load achievements data"""
        os.makedirs(os.path.dirname(self.achievements_file), exist_ok=True)
        if os.path.exists(self.achievements_file):
            try:
                with open(self.achievements_file, 'r') as f:
                    self.achievements = json.load(f)
            except:
                self.achievements = self._default_achievements()
        else:
            self.achievements = self._default_achievements()
        self.save_achievements()
    
    def _default_achievements(self) -> Dict:
        """Default achievements configuration"""
        return {
            'achievements': [
                {
                    'id': 'first_task_completed',
                    'name': 'First Task Completed',
                    'description': 'Complete your first agent task',
                    'icon': '🎯',
                    'rarity': 'common',
                    'points_reward': {'xp': 50, 'activity_points': 25},
                    'condition': {'type': 'task_completed', 'count': 1}
                },
                {
                    'id': 'task_master_10',
                    'name': 'Task Master',
                    'description': 'Complete 10 tasks',
                    'icon': '⭐',
                    'rarity': 'uncommon',
                    'points_reward': {'xp': 200, 'activity_points': 100},
                    'condition': {'type': 'task_completed', 'count': 10}
                },
                {
                    'id': 'task_master_50',
                    'name': 'Task Expert',
                    'description': 'Complete 50 tasks',
                    'icon': '🌟',
                    'rarity': 'rare',
                    'points_reward': {'xp': 500, 'activity_points': 250},
                    'condition': {'type': 'task_completed', 'count': 50}
                },
                {
                    'id': 'task_master_100',
                    'name': 'Task Legend',
                    'description': 'Complete 100 tasks',
                    'icon': '💫',
                    'rarity': 'epic',
                    'points_reward': {'xp': 1000, 'activity_points': 500},
                    'condition': {'type': 'task_completed', 'count': 100}
                },
                {
                    'id': 'debugger_master',
                    'name': 'Debugger Master',
                    'description': 'Complete all debugger tab tasks',
                    'icon': '🔧',
                    'rarity': 'rare',
                    'points_reward': {'xp': 300, 'activity_points': 150},
                    'condition': {'type': 'tab_tasks_completed', 'tab': 'all'}
                },
                {
                    'id': 'error_migration_expert',
                    'name': 'Error Migration Expert',
                    'description': 'Migrate 100 error handlers',
                    'icon': '🔄',
                    'rarity': 'epic',
                    'points_reward': {'xp': 750, 'activity_points': 375},
                    'condition': {'type': 'handlers_migrated', 'count': 100}
                },
                {
                    'id': 'perfect_week',
                    'name': 'Perfect Week',
                    'description': 'Complete tasks every day for a week',
                    'icon': '📅',
                    'rarity': 'rare',
                    'points_reward': {'xp': 400, 'activity_points': 200},
                    'condition': {'type': 'daily_tasks', 'days': 7}
                },
                {
                    'id': 'speed_demon',
                    'name': 'Speed Demon',
                    'description': 'Complete 5 tasks in one day',
                    'icon': '⚡',
                    'rarity': 'uncommon',
                    'points_reward': {'xp': 150, 'activity_points': 75},
                    'condition': {'type': 'tasks_in_day', 'count': 5}
                },
                {
                    'id': 'all_tabs_explorer',
                    'name': 'All Tabs Explorer',
                    'description': 'Complete tasks in all debugger tabs',
                    'icon': '🗺️',
                    'rarity': 'rare',
                    'points_reward': {'xp': 350, 'activity_points': 175},
                    'condition': {'type': 'tabs_completed', 'count': 7}
                },
                {
                    'id': 'points_collector',
                    'name': 'Points Collector',
                    'description': 'Earn 5000 XP from tasks',
                    'icon': '💰',
                    'rarity': 'epic',
                    'points_reward': {'xp': 1000, 'activity_points': 500},
                    'condition': {'type': 'total_xp', 'amount': 5000}
                }
            ],
            'unlocked': {},
            'progress': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def save_achievements(self):
        """Save achievements data"""
        try:
            self.achievements['last_updated'] = datetime.now().isoformat()
            with open(self.achievements_file, 'w') as f:
                json.dump(self.achievements, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving achievements: {e}")
    
    def check_achievements(self, agent_id: str, action: str, data: Dict = None) -> List[Dict]:
        """Check and unlock achievements based on action"""
        unlocked = []
        data = data or {}
        
        # Get agent's unlocked achievements
        agent_unlocked = self.achievements['unlocked'].get(agent_id, {})
        agent_progress = self.achievements['progress'].get(agent_id, {})
        
        # Update progress based on action
        if action == 'task_completed':
            agent_progress['tasks_completed'] = agent_progress.get('tasks_completed', 0) + 1
            agent_progress['total_xp'] = agent_progress.get('total_xp', 0) + data.get('xp', 0)
            agent_progress['total_activity'] = agent_progress.get('total_activity', 0) + data.get('activity_points', 0)
            
            # Check task count achievements
            task_count = agent_progress['tasks_completed']
            for achievement in self.achievements['achievements']:
                if achievement['id'] not in agent_unlocked:
                    condition = achievement.get('condition', {})
                    if condition.get('type') == 'task_completed':
                        if task_count >= condition.get('count', 0):
                            unlocked.append(self._unlock_achievement(agent_id, achievement))
        
        elif action == 'handlers_migrated':
            agent_progress['handlers_migrated'] = agent_progress.get('handlers_migrated', 0) + data.get('count', 0)
            
            handlers_count = agent_progress['handlers_migrated']
            for achievement in self.achievements['achievements']:
                if achievement['id'] not in agent_unlocked:
                    condition = achievement.get('condition', {})
                    if condition.get('type') == 'handlers_migrated':
                        if handlers_count >= condition.get('count', 0):
                            unlocked.append(self._unlock_achievement(agent_id, achievement))
        
        elif action == 'tab_task_completed':
            tab = data.get('tab', '')
            if 'tabs_completed' not in agent_progress:
                agent_progress['tabs_completed'] = set()
            agent_progress['tabs_completed'].add(tab)
            
            tabs_count = len(agent_progress.get('tabs_completed', set()))
            for achievement in self.achievements['achievements']:
                if achievement['id'] not in agent_unlocked:
                    condition = achievement.get('condition', {})
                    if condition.get('type') == 'tabs_completed':
                        if tabs_count >= condition.get('count', 0):
                            unlocked.append(self._unlock_achievement(agent_id, achievement))
        
        # Check total XP achievement
        total_xp = agent_progress.get('total_xp', 0)
        for achievement in self.achievements['achievements']:
            if achievement['id'] not in agent_unlocked:
                condition = achievement.get('condition', {})
                if condition.get('type') == 'total_xp':
                    if total_xp >= condition.get('amount', 0):
                        unlocked.append(self._unlock_achievement(agent_id, achievement))
        
        # Save progress
        self.achievements['progress'][agent_id] = agent_progress
        self.save_achievements()
        
        return unlocked
    
    def _unlock_achievement(self, agent_id: str, achievement: Dict) -> Dict:
        """Unlock an achievement for an agent"""
        if agent_id not in self.achievements['unlocked']:
            self.achievements['unlocked'][agent_id] = {}
        
        unlock_data = {
            'achievement_id': achievement['id'],
            'achievement': achievement,
            'unlocked_at': datetime.now().isoformat(),
            'points_reward': achievement.get('points_reward', {})
        }
        
        self.achievements['unlocked'][agent_id][achievement['id']] = unlock_data
        self.save_achievements()
        
        return unlock_data
    
    def get_agent_achievements(self, agent_id: str) -> Dict:
        """Get all achievements for an agent"""
        unlocked = self.achievements['unlocked'].get(agent_id, {})
        progress = self.achievements['progress'].get(agent_id, {})
        
        return {
            'unlocked': list(unlocked.values()),
            'progress': progress,
            'total_unlocked': len(unlocked),
            'total_available': len(self.achievements['achievements'])
        }
    
    def get_all_achievements(self) -> List[Dict]:
        """Get all available achievements"""
        return self.achievements['achievements']


# Global instance
agent_achievements = AgentAchievements()
