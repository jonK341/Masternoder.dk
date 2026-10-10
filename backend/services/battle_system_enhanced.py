"""
Enhanced Battle System - Timepockets, Timelocks, Match Tracking, PVP Trophies
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random
import uuid

class EnhancedBattleSystem:
    """Enhanced battle system with timepockets, timelocks, match tracking, and PVP trophies"""
    
    def __init__(self):
        self.battles = {}  # battle_id -> battle_data
        self.clans = {}  # clan_id -> clan_data
        self.battle_history = []  # List of completed battles
        self.match_tracking = defaultdict(dict)  # {battle_id: match_data}
        self.user_win_streaks = defaultdict(int)  # {user_id: streak_count}
        self.user_mission_streaks = defaultdict(int)  # {user_id: mission_streak}
        self.user_operation_streaks = defaultdict(int)  # {user_id: operation_streak}
        self.pvp_trophies = defaultdict(list)  # {user_id: [trophy_data]}
        self.id_system = {}  # ID system for NisseID, KusseMors ID, Giga Jons ID
        self.time_frames = defaultdict(list)  # {battle_id: [time_frame_data]}
        self.active_time_frames = {}  # {time_frame_id: time_frame_data}
        self.battle_activity_history = defaultdict(list)  # {user_id: [activity_data]}
        self.time_disorder_devices = {}  # {device_id: device_data} - Linked devices
        self.active_shields = {}  # {shield_id: shield_data} - Active shields in battles
        self.advanced_tech_active = {}  # {tech_id: tech_data} - Active advanced tech
        self._initialize_id_system()
    
    def _initialize_id_system(self):
        """Initialize ID system"""
        self.id_system = {
            'nisse_id': {
                'id': 'nisse_id',
                'name': 'NisseID',
                'description': 'Nisse identification system',
                'info': 'Nisse system information and tracking',
                'death_brings': True
            },
            'kusse_mors_id': {
                'id': 'kusse_mors_id',
                'name': 'KusseMors ID',
                'description': 'KusseMors identification system',
                'info': 'KusseMors system information and tracking',
                'death_brings': True
            },
            'giga_jons_id': {
                'id': 'giga_jons_id',
                'name': 'Giga Jons ID',
                'description': 'Giga Jons identification system',
                'info': 'Giga Jons system information and tracking',
                'death_brings': True
            }
        }
    
    def create_battle_with_timepocket(
        self,
        clan1_id: str,
        clan2_id: str,
        battle_type: str = 'standard',
        enable_timepocket: bool = False,
        timelock_minutes: Optional[int] = None,
        total_matches: int = 3
    ) -> Dict[str, Any]:
        """Create battle with timepocket and timelock support - auto-creates clans if needed"""
        # Auto-create clans if they don't exist
        if clan1_id not in self.clans:
            self.create_clan(clan1_id, f"Clan {clan1_id}", f"leader_{clan1_id}", f"Auto-created clan {clan1_id}")
        if clan2_id not in self.clans:
            self.create_clan(clan2_id, f"Clan {clan2_id}", f"leader_{clan2_id}", f"Auto-created clan {clan2_id}")
        
        battle_id = f"battle_{datetime.utcnow().timestamp()}"
        
        # Create timepocket if enabled
        timepocket_data = None
        if enable_timepocket:
            pocket_id = f"pocket_{battle_id}"
            timepocket_data = {
                'pocket_id': pocket_id,
                'enabled': True,
                'sync_active': False,
                'time_period': 'present',
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Create timelock if specified
        timelock_data = None
        if timelock_minutes and timelock_minutes > 0:
            timelock_data = {
                'locked': True,
                'lock_until': (datetime.utcnow() + timedelta(minutes=timelock_minutes)).isoformat(),
                'time_remaining_minutes': timelock_minutes
            }
        
        # Initialize match tracking with levels
        match_tracking = {
            'total_matches': total_matches,
            'completed_matches': 0,
            'matches': [],
            'all_matches_complete': False,
            'level': 1,
            'level_progress': 0.0,
            'max_level': 100,
            'level_rewards': []
        }
        
        battle = {
            'id': battle_id,
            'clan1_id': clan1_id,
            'clan2_id': clan2_id,
            'clan1_name': self.clans[clan1_id]['name'],
            'clan2_name': self.clans[clan2_id]['name'],
            'battle_type': battle_type,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'clan1_score': 0,
            'clan2_score': 0,
            'clan1_power': self.calculate_clan_power(clan1_id),
            'clan2_power': self.calculate_clan_power(clan2_id),
            'winner': None,
            'rewards': {},
            'timepocket': timepocket_data,
            'timepocket_enabled': enable_timepocket,
            'timelock_status': timelock_data,
            'match_tracking': match_tracking
        }
        
        self.battles[battle_id] = battle
        self.match_tracking[battle_id] = match_tracking
        
        return {'success': True, 'battle': battle}
    
    def submit_match_result(
        self,
        battle_id: str,
        match_number: int,
        clan1_score: int,
        clan2_score: int,
        winner_clan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a match result and track completion"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.battles[battle_id]
        match_tracking = self.match_tracking[battle_id]
        
        # Create match entry
        match_data = {
            'match_number': match_number,
            'clan1_score': clan1_score,
            'clan2_score': clan2_score,
            'winner_clan_id': winner_clan_id,
            'completed_at': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Add to matches list
        match_tracking['matches'].append(match_data)
        match_tracking['completed_matches'] = len(match_tracking['matches'])
        
        # Check if all matches complete
        if match_tracking['completed_matches'] >= match_tracking['total_matches']:
            match_tracking['all_matches_complete'] = True
            
            # Level up system
            level_progress = (match_tracking['completed_matches'] / match_tracking['total_matches']) * 100
            match_tracking['level_progress'] = level_progress
            
            # Check for level up
            if match_tracking['level'] < match_tracking['max_level']:
                level_increase = int(level_progress / 10)  # Level up every 10% progress
                if level_increase > 0:
                    old_level = match_tracking['level']
                    match_tracking['level'] = min(match_tracking['level'] + level_increase, match_tracking['max_level'])
                    
                    if match_tracking['level'] > old_level:
                        # Award level rewards
                        reward = {
                            'level': match_tracking['level'],
                            'reward_type': 'level_up',
                            'points': match_tracking['level'] * 100,
                            'trophies': match_tracking['level'] // 10,
                            'awarded_at': datetime.utcnow().isoformat()
                        }
                        match_tracking['level_rewards'].append(reward)
            
            # Determine overall battle winner
            clan1_wins = sum(1 for m in match_tracking['matches'] if m.get('winner_clan_id') == battle['clan1_id'])
            clan2_wins = sum(1 for m in match_tracking['matches'] if m.get('winner_clan_id') == battle['clan2_id'])
            
            if clan1_wins > clan2_wins:
                battle['winner'] = battle['clan1_id']
            elif clan2_wins > clan1_wins:
                battle['winner'] = battle['clan2_id']
            else:
                battle['winner'] = None  # Draw
        
        # Update battle scores
        battle['clan1_score'] = sum(m['clan1_score'] for m in match_tracking['matches'])
        battle['clan2_score'] = sum(m['clan2_score'] for m in match_tracking['matches'])
        
        return {
            'success': True,
            'match': match_data,
            'match_tracking': match_tracking,
            'all_matches_complete': match_tracking['all_matches_complete']
        }
    
    def check_all_matches_complete(self, battle_id: str) -> Dict[str, Any]:
        """Check if all matches in a battle are complete with levels"""
        if battle_id not in self.match_tracking:
            return {'success': False, 'error': 'Battle not found'}
        
        match_tracking = self.match_tracking[battle_id]
        
        return {
            'success': True,
            'all_matches_complete': match_tracking['all_matches_complete'],
            'total_matches': match_tracking['total_matches'],
            'completed_matches': match_tracking['completed_matches'],
            'matches': match_tracking['matches'],
            'level': match_tracking.get('level', 1),
            'level_progress': match_tracking.get('level_progress', 0.0),
            'max_level': match_tracking.get('max_level', 100),
            'level_rewards': match_tracking.get('level_rewards', [])
        }
    
    def update_win_streak(self, user_id: str, won: bool, battle_type: str = 'pvp') -> Dict[str, Any]:
        """Update win streak for PVP trophy tracking"""
        if won:
            self.user_win_streaks[user_id] += 1
            
            # Check for mission/operation streaks
            if battle_type == 'mission':
                self.user_mission_streaks[user_id] += 1
            elif battle_type == 'operation':
                self.user_operation_streaks[user_id] += 1
            
            # Award PVP trophies based on streaks
            trophies_awarded = []
            streak = self.user_win_streaks[user_id]
            
            if streak >= 5 and not any(t.get('id') == 'pvp_streak_5' for t in self.pvp_trophies.get(user_id, [])):
                trophies_awarded.append(self._award_pvp_trophy(user_id, 'pvp_streak_5', streak))
            
            if streak >= 10 and not any(t.get('id') == 'pvp_streak_10' for t in self.pvp_trophies.get(user_id, [])):
                trophies_awarded.append(self._award_pvp_trophy(user_id, 'pvp_streak_10', streak))
            
            if streak >= 25 and not any(t.get('id') == 'pvp_streak_25' for t in self.pvp_trophies.get(user_id, [])):
                trophies_awarded.append(self._award_pvp_trophy(user_id, 'pvp_streak_25', streak))
            
            if streak >= 50 and not any(t.get('id') == 'pvp_streak_50' for t in self.pvp_trophies.get(user_id, [])):
                trophies_awarded.append(self._award_pvp_trophy(user_id, 'pvp_streak_50', streak))
            
            # Mission/Operation specific trophies
            if battle_type == 'mission':
                mission_streak = self.user_mission_streaks[user_id]
                if mission_streak >= 10 and not any(t.get('id') == 'mission_streak_10' for t in self.pvp_trophies.get(user_id, [])):
                    trophies_awarded.append(self._award_pvp_trophy(user_id, 'mission_streak_10', mission_streak, 'mission'))
            
            if battle_type == 'operation':
                operation_streak = self.user_operation_streaks[user_id]
                if operation_streak >= 10 and not any(t.get('id') == 'operation_streak_10' for t in self.pvp_trophies.get(user_id, [])):
                    trophies_awarded.append(self._award_pvp_trophy(user_id, 'operation_streak_10', operation_streak, 'operation'))
            
            return {
                'success': True,
                'win_streak': streak,
                'mission_streak': self.user_mission_streaks[user_id],
                'operation_streak': self.user_operation_streaks[user_id],
                'trophies_awarded': trophies_awarded
            }
        else:
            # Reset streaks on loss
            self.user_win_streaks[user_id] = 0
            if battle_type == 'mission':
                self.user_mission_streaks[user_id] = 0
            elif battle_type == 'operation':
                self.user_operation_streaks[user_id] = 0
            
            return {
                'success': True,
                'win_streak': 0,
                'mission_streak': self.user_mission_streaks[user_id],
                'operation_streak': self.user_operation_streaks[user_id],
                'streak_reset': True
            }
    
    def _award_pvp_trophy(self, user_id: str, trophy_id: str, streak: int, battle_type: str = 'pvp') -> Dict[str, Any]:
        """Award a PVP trophy"""
        trophy_definitions = {
            'pvp_streak_5': {
                'id': 'pvp_streak_5',
                'name': 'PVP Win Streak 5',
                'description': f'Achieved {streak} consecutive PVP wins',
                'icon': '🏆',
                'points': 100,
                'category': 'pvp',
                'streak': streak
            },
            'pvp_streak_10': {
                'id': 'pvp_streak_10',
                'name': 'PVP Win Streak 10',
                'description': f'Achieved {streak} consecutive PVP wins',
                'icon': '🥇',
                'points': 250,
                'category': 'pvp',
                'streak': streak
            },
            'pvp_streak_25': {
                'id': 'pvp_streak_25',
                'name': 'PVP Win Streak 25',
                'description': f'Achieved {streak} consecutive PVP wins',
                'icon': '👑',
                'points': 500,
                'category': 'pvp',
                'streak': streak
            },
            'pvp_streak_50': {
                'id': 'pvp_streak_50',
                'name': 'PVP Win Streak 50',
                'description': f'Achieved {streak} consecutive PVP wins',
                'icon': '💎',
                'points': 1000,
                'category': 'pvp',
                'streak': streak
            },
            'mission_streak_10': {
                'id': 'mission_streak_10',
                'name': 'Mission Win Streak 10',
                'description': f'Achieved {streak} consecutive mission wins',
                'icon': '🎯',
                'points': 300,
                'category': 'mission',
                'streak': streak
            },
            'operation_streak_10': {
                'id': 'operation_streak_10',
                'name': 'Operation Win Streak 10',
                'description': f'Achieved {streak} consecutive operation wins',
                'icon': '⚔️',
                'points': 300,
                'category': 'operation',
                'streak': streak
            }
        }
        
        trophy_data = trophy_definitions.get(trophy_id, {})
        if not trophy_data:
            return {}
        
        trophy = {
            **trophy_data,
            'earned_at': datetime.utcnow().isoformat(),
            'battle_type': battle_type
        }
        
        if user_id not in self.pvp_trophies:
            self.pvp_trophies[user_id] = []
        
        self.pvp_trophies[user_id].append(trophy)
        
        return trophy
    
    def get_pvp_trophies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all PVP trophies for a user"""
        return self.pvp_trophies.get(user_id, [])
    
    def get_win_streaks(self, user_id: str) -> Dict[str, Any]:
        """Get win streak information for a user"""
        return {
            'pvp_streak': self.user_win_streaks.get(user_id, 0),
            'mission_streak': self.user_mission_streaks.get(user_id, 0),
            'operation_streak': self.user_operation_streaks.get(user_id, 0)
        }
    
    def handle_death(self, user_id: str, death_type: str = 'battle') -> Dict[str, Any]:
        """Handle death and bring ID information"""
        # Get IDs that death brings
        death_ids = []
        
        if death_type == 'battle' or death_type == 'all':
            # Death brings all IDs
            for id_key, id_data in self.id_system.items():
                if id_data.get('death_brings', False):
                    death_ids.append({
                        'id': id_data['id'],
                        'name': id_data['name'],
                        'description': id_data['description'],
                        'info': id_data['info'],
                        'brought_by': 'death',
                        'timestamp': datetime.utcnow().isoformat()
                    })
        
        return {
            'success': True,
            'death_type': death_type,
            'ids_brought': death_ids,
            'message': f'Death brings {len(death_ids)} ID(s)'
        }
    
    def get_id_info(self, id_key: str) -> Optional[Dict[str, Any]]:
        """Get ID system information"""
        return self.id_system.get(id_key)
    
    def get_all_ids(self) -> Dict[str, Dict[str, Any]]:
        """Get all ID system information"""
        return self.id_system
    
    def check_timelock(self, battle_id: str) -> Dict[str, Any]:
        """Check timelock status for a battle"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.battles[battle_id]
        timelock = battle.get('timelock_status')
        
        if not timelock:
            return {
                'success': True,
                'locked': False,
                'message': 'No timelock on this battle'
            }
        
        # Check if timelock has expired
        lock_until = datetime.fromisoformat(timelock['lock_until'].replace('Z', '+00:00'))
        if datetime.utcnow() >= lock_until:
            timelock['locked'] = False
            timelock['time_remaining_minutes'] = 0
        
        if timelock['locked']:
            remaining = (lock_until - datetime.utcnow()).total_seconds() / 60
            timelock['time_remaining_minutes'] = int(remaining)
        
        return {
            'success': True,
            'locked': timelock['locked'],
            'time_remaining_minutes': timelock.get('time_remaining_minutes', 0),
            'lock_until': timelock.get('lock_until')
        }
    
    def create_clan(self, clan_id: str, name: str, leader_id: str, description: str = "") -> Dict[str, Any]:
        """Create a new clan"""
        clan = {
            'id': clan_id,
            'name': name,
            'leader_id': leader_id,
            'description': description,
            'members': [leader_id],
            'created_at': datetime.utcnow().isoformat(),
            'total_wins': 0,
            'total_losses': 0,
            'total_draws': 0,
            'trophies': 0,
            'power': 0
        }
        self.clans[clan_id] = clan
        return clan
    
    def calculate_clan_power(self, clan_id: str) -> int:
        """Calculate total power of a clan"""
        if clan_id not in self.clans:
            return 0
        member_count = len(self.clans[clan_id]['members'])
        return member_count * 100 + self.clans[clan_id]['trophies'] * 10
    
    def get_battle(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """Get battle with enhanced data"""
        if battle_id not in self.battles:
            return None
        
        battle = self.battles[battle_id].copy()
        
        # Add match tracking
        if battle_id in self.match_tracking:
            battle['match_tracking'] = self.match_tracking[battle_id]
        
        # Add timelock status
        timelock_status = self.check_timelock(battle_id)
        battle['timelock_status'] = timelock_status
        
        # Add time frames
        if battle_id in self.time_frames:
            battle['time_frames'] = self.time_frames[battle_id]
        
        return battle
    
    def create_time_frame(self, battle_id: str, frame_name: str, duration_minutes: int, loop: bool = True) -> Dict[str, Any]:
        """Create a time frame for battle looping"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        frame_id = f"frame_{datetime.utcnow().timestamp()}"
        time_frame = {
            'frame_id': frame_id,
            'battle_id': battle_id,
            'frame_name': frame_name,
            'duration_minutes': duration_minutes,
            'loop': loop,
            'created_at': datetime.utcnow().isoformat(),
            'start_time': datetime.utcnow().isoformat(),
            'end_time': (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat(),
            'active': True,
            'loop_count': 0
        }
        
        self.time_frames[battle_id].append(time_frame)
        self.active_time_frames[frame_id] = time_frame
        
        return {'success': True, 'time_frame': time_frame}
    
    def get_active_time_frames(self, battle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active time frames, optionally filtered by battle_id"""
        if battle_id:
            return [tf for tf in self.time_frames.get(battle_id, []) if tf.get('active', False)]
        else:
            return [tf for tf in self.active_time_frames.values() if tf.get('active', False)]
    
    def update_time_frame_loop(self, frame_id: str) -> Dict[str, Any]:
        """Update time frame loop - called when frame completes"""
        if frame_id not in self.active_time_frames:
            return {'success': False, 'error': 'Time frame not found'}
        
        time_frame = self.active_time_frames[frame_id]
        
        if not time_frame.get('loop', False):
            time_frame['active'] = False
            return {'success': True, 'looped': False, 'active': False}
        
        # Loop the time frame
        time_frame['loop_count'] = time_frame.get('loop_count', 0) + 1
        time_frame['start_time'] = datetime.utcnow().isoformat()
        time_frame['end_time'] = (datetime.utcnow() + timedelta(minutes=time_frame['duration_minutes'])).isoformat()
        
        return {
            'success': True,
            'looped': True,
            'loop_count': time_frame['loop_count'],
            'time_frame': time_frame
        }
    
    def record_battle_activity(self, user_id: str, activity_type: str, battle_id: str, difficulty: Optional[str] = None, result: Optional[str] = None) -> None:
        """Record battle activity for charts"""
        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,  # 'battle_start', 'battle_end', 'battle_win', 'battle_loss'
            'battle_id': battle_id,
            'difficulty': difficulty,
            'result': result
        }
        self.battle_activity_history[user_id].append(activity)
        
        # Keep only last 100 activities
        if len(self.battle_activity_history[user_id]) > 100:
            self.battle_activity_history[user_id] = self.battle_activity_history[user_id][-100:]
    
    def get_battle_activity_stats(self, user_id: str) -> Dict[str, Any]:
        """Get battle activity statistics for charts"""
        activities = self.battle_activity_history.get(user_id, [])
        
        # Calculate stats
        total_battles = len([a for a in activities if a['activity_type'] == 'battle_end'])
        wins = len([a for a in activities if a.get('result') == 'win'])
        losses = len([a for a in activities if a.get('result') == 'loss'])
        win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
        
        # Difficulty distribution
        difficulty_dist = {}
        for activity in activities:
            if activity.get('difficulty'):
                difficulty_dist[activity['difficulty']] = difficulty_dist.get(activity['difficulty'], 0) + 1
        
        # Time-based activity (last 7 days)
        now = datetime.utcnow()
        last_7_days = []
        for i in range(7):
            day_start = now - timedelta(days=i+1)
            day_end = now - timedelta(days=i)
            day_activities = [
                a for a in activities
                if day_start <= datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) <= day_end
            ]
            last_7_days.append({
                'date': day_end.strftime('%Y-%m-%d'),
                'count': len(day_activities)
            })
        last_7_days.reverse()
        
        return {
            'total_battles': total_battles,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'difficulty_distribution': difficulty_dist,
            'activity_timeline': last_7_days,
            'activities': activities[-20:]  # Last 20 activities
        }
    
    def add_time_disorder_to_battle(
        self,
        battle_id: str,
        device_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Add Time Disorder Device to battle"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        # Import time disorder device
        try:
            from backend.services.time_disorder_device import time_disorder_device
            device_result = time_disorder_device.get_shield_status(device_id) if hasattr(time_disorder_device, 'get_shield_status') else None
            
            battle = self.battles[battle_id]
            if 'time_disorder_devices' not in battle:
                battle['time_disorder_devices'] = []
            
            battle['time_disorder_devices'].append({
                'device_id': device_id,
                'user_id': user_id,
                'added_at': datetime.utcnow().isoformat()
            })
            
            self.time_disorder_devices[device_id] = {
                'battle_id': battle_id,
                'user_id': user_id,
                'device_id': device_id
            }
            
            return {
                'success': True,
                'battle': battle,
                'message': 'Time Disorder Device added to battle'
            }
        except ImportError:
            return {'success': False, 'error': 'Time Disorder Device system not available'}
    
    def activate_shield_in_battle(
        self,
        battle_id: str,
        shield_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Activate Time-Death Shield in battle"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        try:
            from backend.services.time_disorder_device import time_disorder_device
            shield_result = time_disorder_device.get_shield_status(shield_id)
            
            if not shield_result.get('success'):
                return shield_result
            
            shield = shield_result['shield']
            battle = self.battles[battle_id]
            
            if 'active_shields' not in battle:
                battle['active_shields'] = []
            
            battle['active_shields'].append({
                'shield_id': shield_id,
                'user_id': user_id,
                'shield_power': shield['shield_power'],
                'durability': shield.get('current_durability', shield['durability']),
                'activated_at': datetime.utcnow().isoformat()
            })
            
            self.active_shields[shield_id] = {
                'battle_id': battle_id,
                'user_id': user_id,
                'shield': shield
            }
            
            # Apply shield protection to battle
            if 'protection' not in battle:
                battle['protection'] = {}
            
            battle['protection']['shield_active'] = True
            battle['protection']['shield_power'] = shield['shield_power']
            
            return {
                'success': True,
                'battle': battle,
                'shield': shield,
                'message': f'Time-Death Shield activated! Power: {shield["shield_power"]}'
            }
        except ImportError:
            return {'success': False, 'error': 'Time Disorder Device system not available'}
    
    def add_advanced_tech_to_battle(
        self,
        battle_id: str,
        tech_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Add advanced technology to battle"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        try:
            from backend.services.advanced_battle_tech import advanced_battle_tech
            
            # Find tech in active tech
            tech = None
            for tid, tech_data in advanced_battle_tech.active_tech.items():
                if tid == tech_id:
                    tech = tech_data
                    break
            
            if not tech:
                return {'success': False, 'error': 'Advanced tech not found or not active'}
            
            battle = self.battles[battle_id]
            if 'advanced_tech' not in battle:
                battle['advanced_tech'] = []
            
            battle['advanced_tech'].append({
                'tech_id': tech_id,
                'tech_name': tech['tech_data']['name'],
                'user_id': user_id,
                'power_boost': tech['tech_data'].get('power_boost', 0),
                'force_boost': tech['tech_data'].get('force_boost', 0),
                'impressiveness': tech['tech_data'].get('impressiveness', 0),
                'added_at': datetime.utcnow().isoformat()
            })
            
            self.advanced_tech_active[tech_id] = {
                'battle_id': battle_id,
                'user_id': user_id,
                'tech': tech
            }
            
            # Apply tech boosts to battle
            if 'tech_boosts' not in battle:
                battle['tech_boosts'] = {
                    'total_power_boost': 0,
                    'total_force_boost': 0,
                    'total_impressiveness': 0
                }
            
            battle['tech_boosts']['total_power_boost'] += tech['tech_data'].get('power_boost', 0)
            battle['tech_boosts']['total_force_boost'] += tech['tech_data'].get('force_boost', 0)
            battle['tech_boosts']['total_impressiveness'] += tech['tech_data'].get('impressiveness', 0)
            
            return {
                'success': True,
                'battle': battle,
                'tech': tech,
                'message': f'Advanced tech {tech["tech_data"]["name"]} added! Impressiveness: {tech["tech_data"].get("impressiveness", 0)}'
            }
        except ImportError:
            return {'success': False, 'error': 'Advanced Battle Tech system not available'}
    
    def get_battle_tech_status(self, battle_id: str) -> Dict[str, Any]:
        """Get all tech status for a battle"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.battles[battle_id]
        
        return {
            'success': True,
            'battle_id': battle_id,
            'time_disorder_devices': battle.get('time_disorder_devices', []),
            'active_shields': battle.get('active_shields', []),
            'advanced_tech': battle.get('advanced_tech', []),
            'protection': battle.get('protection', {}),
            'tech_boosts': battle.get('tech_boosts', {}),
            'message': 'Battle tech status retrieved'
        }


# Global instance
enhanced_battle_system = EnhancedBattleSystem()

