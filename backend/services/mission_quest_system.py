"""
Mission & Quest System - Daily Quests and Timeline Missions
Includes MTG.ID integration
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random

class MissionQuestSystem:
    """Mission and quest system with daily quests and timeline missions"""
    
    def __init__(self):
        self.daily_quests = {}  # {quest_id: quest_data}
        self.timeline_missions = {}  # {mission_id: mission_data}
        self.user_quest_progress = defaultdict(dict)  # {user_id: {quest_id: progress}}
        self.user_mission_progress = defaultdict(dict)  # {user_id: {mission_id: progress}}
        self.quest_completions = defaultdict(list)  # {user_id: [completion_data]}
        self.mtg_ids = {}  # MTG.ID system integration
        self.local_gps_missions = {}  # {mission_id: mission_data}
        self.user_gps_missions = defaultdict(list)  # {user_id: [mission_ids]}
        self.quest_mission_operators = defaultdict(list)  # {user_id: [operator_data]}
        self._initialize_daily_quests()
        self._initialize_timeline_missions()
        self._initialize_mtg_ids()
    
    def _initialize_daily_quests(self):
        """Initialize daily quest pool"""
        self.daily_quest_pool = [
            {
                'id': 'daily_battle_win',
                'name': 'Win a Battle',
                'description': 'Win 1 battle today',
                'type': 'battle',
                'target': 1,
                'reward_points': 50,
                'reward_trophies': 1,
                'icon': '⚔️'
            },
            {
                'id': 'daily_battle_3',
                'name': 'Battle Warrior',
                'description': 'Complete 3 battles today',
                'type': 'battle',
                'target': 3,
                'reward_points': 100,
                'reward_trophies': 2,
                'icon': '🗡️'
            },
            {
                'id': 'daily_trophy_collect',
                'name': 'Trophy Hunter',
                'description': 'Collect 5 trophies today',
                'type': 'trophy',
                'target': 5,
                'reward_points': 75,
                'reward_trophies': 1,
                'icon': '🏆'
            },
            {
                'id': 'daily_card_create',
                'name': 'Card Collector',
                'description': 'Create 1 collectible card today',
                'type': 'collectible',
                'target': 1,
                'reward_points': 60,
                'reward_trophies': 1,
                'icon': '🃏'
            },
            {
                'id': 'daily_trade_complete',
                'name': 'Trader',
                'description': 'Complete 1 trade today',
                'type': 'trade',
                'target': 1,
                'reward_points': 80,
                'reward_trophies': 2,
                'icon': '💎'
            }
        ]
    
    def _initialize_timeline_missions(self):
        """Initialize timeline missions"""
        self.timeline_missions = {
            'mission_001': {
                'id': 'mission_001',
                'name': 'First Steps',
                'description': 'Complete your first battle',
                'timeline_position': 1,
                'type': 'battle',
                'target': 1,
                'reward_points': 100,
                'reward_trophies': 3,
                'icon': '🎯',
                'unlocks': ['mission_002']
            },
            'mission_002': {
                'id': 'mission_002',
                'name': 'Rising Warrior',
                'description': 'Win 5 battles',
                'timeline_position': 2,
                'type': 'battle',
                'target': 5,
                'reward_points': 200,
                'reward_trophies': 5,
                'icon': '⚔️',
                'unlocks': ['mission_003']
            },
            'mission_003': {
                'id': 'mission_003',
                'name': 'Trophy Master',
                'description': 'Collect 10 trophies',
                'timeline_position': 3,
                'type': 'trophy',
                'target': 10,
                'reward_points': 300,
                'reward_trophies': 7,
                'icon': '🏆',
                'unlocks': ['mission_004']
            },
            'mission_004': {
                'id': 'mission_004',
                'name': 'Collector',
                'description': 'Create 3 collectible cards',
                'timeline_position': 4,
                'type': 'collectible',
                'target': 3,
                'reward_points': 400,
                'reward_trophies': 10,
                'icon': '🃏',
                'unlocks': ['mission_005']
            },
            'mission_005': {
                'id': 'mission_005',
                'name': 'Master Trader',
                'description': 'Complete 5 trades',
                'timeline_position': 5,
                'type': 'trade',
                'target': 5,
                'reward_points': 500,
                'reward_trophies': 15,
                'icon': '💎',
                'unlocks': []
            }
        }
    
    def _initialize_mtg_ids(self):
        """Initialize MTG.ID system"""
        self.mtg_ids = {
            'mtg_start': {
                'id': 'mtg_start',
                'name': 'MTG.ID.Start',
                'description': 'Magic: The Gathering ID System Start',
                'unlocked': True,
                'mission_related': True
            }
        }
    
    def generate_daily_quests(self, user_id: str) -> Dict[str, Any]:
        """Generate 4-5 daily quests for a user"""
        today = datetime.utcnow().date().isoformat()
        
        # Check if already generated today
        if user_id in self.user_quest_progress:
            existing_quests = [
                q for q in self.daily_quests.values()
                if q.get('user_id') == user_id and q.get('date') == today
            ]
            if existing_quests:
                return {
                    'success': True,
                    'quests': existing_quests,
                    'regenerated': False
                }
        
        # Select 4-5 random quests from pool
        selected_quests = random.sample(self.daily_quest_pool, min(5, len(self.daily_quest_pool)))
        
        generated_quests = []
        for quest_template in selected_quests:
            quest_id = f"{quest_template['id']}_{user_id}_{today}"
            quest = {
                'quest_id': quest_id,
                'user_id': user_id,
                'name': quest_template['name'],
                'description': quest_template['description'],
                'type': quest_template['type'],
                'target': quest_template['target'],
                'current_progress': 0,
                'reward_points': quest_template['reward_points'],
                'reward_trophies': quest_template['reward_trophies'],
                'icon': quest_template['icon'],
                'date': today,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(days=1)).isoformat()
            }
            
            self.daily_quests[quest_id] = quest
            self.user_quest_progress[user_id][quest_id] = {
                'current_progress': 0,
                'target': quest_template['target']
            }
            generated_quests.append(quest)
        
        return {
            'success': True,
            'quests': generated_quests,
            'regenerated': True
        }
    
    def update_quest_progress(self, user_id: str, quest_type: str, amount: int = 1) -> Dict[str, Any]:
        """Update progress for quests of a specific type"""
        today = datetime.utcnow().date().isoformat()
        updated_quests = []
        completed_quests = []
        
        # Find active daily quests for user
        user_quests = [
            q for q in self.daily_quests.values()
            if q.get('user_id') == user_id and q.get('type') == quest_type and q.get('status') == 'active'
        ]
        
        for quest in user_quests:
            quest_id = quest['quest_id']
            if quest_id in self.user_quest_progress[user_id]:
                progress = self.user_quest_progress[user_id][quest_id]
                progress['current_progress'] = min(
                    progress['current_progress'] + amount,
                    progress['target']
                )
                
                quest['current_progress'] = progress['current_progress']
                
                if progress['current_progress'] >= progress['target']:
                    # Quest completed
                    quest['status'] = 'completed'
                    quest['completed_at'] = datetime.utcnow().isoformat()
                    completed_quests.append(quest)
                    
                    # Record completion
                    self.quest_completions[user_id].append({
                        'quest_id': quest_id,
                        'completed_at': datetime.utcnow().isoformat(),
                        'rewards': {
                            'points': quest['reward_points'],
                            'trophies': quest['reward_trophies']
                        }
                    })
                else:
                    updated_quests.append(quest)
        
        return {
            'success': True,
            'updated_quests': updated_quests,
            'completed_quests': completed_quests
        }
    
    def get_user_daily_quests(self, user_id: str) -> Dict[str, Any]:
        """Get user's daily quests"""
        today = datetime.utcnow().date().isoformat()
        
        # Generate if not exists
        user_quests = [
            q for q in self.daily_quests.values()
            if q.get('user_id') == user_id and q.get('date') == today
        ]
        
        if not user_quests:
            result = self.generate_daily_quests(user_id)
            user_quests = result.get('quests', [])
        
        return {
            'success': True,
            'quests': user_quests,
            'date': today
        }
    
    def get_timeline_missions(self, user_id: str) -> Dict[str, Any]:
        """Get timeline missions for user"""
        missions = []
        
        for mission_id, mission in self.timeline_missions.items():
            progress = self.user_mission_progress[user_id].get(mission_id, {
                'current_progress': 0,
                'target': mission['target'],
                'status': 'locked'
            })
            
            # Check if unlocked
            is_unlocked = True
            if mission.get('unlocks'):
                # Check if previous missions completed
                for unlock_id in mission.get('unlocks', []):
                    prev_progress = self.user_mission_progress[user_id].get(unlock_id, {})
                    if prev_progress.get('status') != 'completed':
                        is_unlocked = False
                        break
            
            mission_data = {
                **mission,
                'current_progress': progress.get('current_progress', 0),
                'status': 'completed' if progress.get('status') == 'completed' else ('active' if is_unlocked else 'locked')
            }
            
            missions.append(mission_data)
        
        # Sort by timeline position
        missions.sort(key=lambda x: x['timeline_position'])
        
        return {
            'success': True,
            'missions': missions
        }
    
    def update_mission_progress(self, user_id: str, mission_type: str, amount: int = 1) -> Dict[str, Any]:
        """Update progress for timeline missions"""
        updated_missions = []
        completed_missions = []
        
        # Find active missions of this type
        for mission_id, mission in self.timeline_missions.items():
            if mission['type'] != mission_type:
                continue
            
            progress = self.user_mission_progress[user_id].get(mission_id, {
                'current_progress': 0,
                'target': mission['target'],
                'status': 'active'
            })
            
            if progress.get('status') == 'completed':
                continue
            
            # Check if unlocked
            is_unlocked = True
            if mission.get('unlocks'):
                for unlock_id in mission.get('unlocks', []):
                    prev_progress = self.user_mission_progress[user_id].get(unlock_id, {})
                    if prev_progress.get('status') != 'completed':
                        is_unlocked = False
                        break
            
            if not is_unlocked:
                continue
            
            progress['current_progress'] = min(
                progress['current_progress'] + amount,
                progress['target']
            )
            
            if progress['current_progress'] >= progress['target']:
                progress['status'] = 'completed'
                progress['completed_at'] = datetime.utcnow().isoformat()
                completed_missions.append({
                    **mission,
                    'current_progress': progress['current_progress'],
                    'status': 'completed'
                })
            else:
                updated_missions.append({
                    **mission,
                    'current_progress': progress['current_progress'],
                    'status': 'active'
                })
            
            self.user_mission_progress[user_id][mission_id] = progress
        
        return {
            'success': True,
            'updated_missions': updated_missions,
            'completed_missions': completed_missions
        }
    
    def get_mtg_id_info(self, mtg_id: str) -> Optional[Dict[str, Any]]:
        """Get MTG.ID information"""
        return self.mtg_ids.get(mtg_id)
    
    def create_local_gps_mission(self, user_id: str, lat: float, lng: float, mission_name: str = "Local GPS Mission") -> Dict[str, Any]:
        """Create first local GPS mission for user - real-time gameplay"""
        mission_id = f"local_gps_{user_id}_{datetime.utcnow().timestamp()}"
        
        mission = {
            'mission_id': mission_id,
            'user_id': user_id,
            'name': mission_name,
            'description': f'Complete mission at your current location ({lat:.4f}, {lng:.4f})',
            'type': 'gps_location',
            'gps_point': {'lat': lat, 'lng': lng},
            'radius_km': 1.0,
            'target': 1,
            'current_progress': 0,
            'reward_points': 100,
            'reward_trophies': 2,
            'icon': '📍',
            'real_time': True,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.local_gps_missions[mission_id] = mission
        self.user_gps_missions[user_id].append(mission_id)
        
        return {
            'success': True,
            'mission': mission
        }
    
    def check_gps_mission_progress(self, user_id: str, lat: float, lng: float) -> Dict[str, Any]:
        """Check if user is at GPS mission location - real-time"""
        completed_missions = []
        
        for mission_id in self.user_gps_missions.get(user_id, []):
            if mission_id not in self.local_gps_missions:
                continue
            
            mission = self.local_gps_missions[mission_id]
            if mission['status'] != 'active':
                continue
            
            # Calculate distance
            distance = self._calculate_distance(
                lat, lng,
                mission['gps_point']['lat'],
                mission['gps_point']['lng']
            )
            
            if distance <= mission['radius_km']:
                # Mission completed
                mission['status'] = 'completed'
                mission['completed_at'] = datetime.utcnow().isoformat()
                mission['current_progress'] = mission['target']
                completed_missions.append(mission)
        
        return {
            'success': True,
            'completed_missions': completed_missions
        }
    
    def get_user_gps_missions(self, user_id: str) -> Dict[str, Any]:
        """Get user's GPS missions"""
        mission_ids = self.user_gps_missions.get(user_id, [])
        missions = [self.local_gps_missions[mid] for mid in mission_ids if mid in self.local_gps_missions]
        
        return {
            'success': True,
            'missions': missions
        }
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two GPS points in km (Haversine formula)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0  # Earth radius in km
        
        lat1_rad = radians(lat1)
        lng1_rad = radians(lng1)
        lat2_rad = radians(lat2)
        lng2_rad = radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c


# Global instance
mission_quest_system = MissionQuestSystem()

