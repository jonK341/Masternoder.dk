"""
Player Profiler - Tracks player behavior and triggers
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

class PlayerProfiler:
    """Profiles player behavior and triggers game events"""
    
    def __init__(self):
        self.profiles = {}  # user_id -> profile_data
        self.triggers = {}  # trigger_id -> trigger_config
        self.trigger_history = []  # List of triggered events
        self._initialize_triggers()
    
    def _initialize_triggers(self):
        """Initialize trigger configurations"""
        self.triggers = {
            'first_video': {
                'id': 'first_video',
                'name': 'First Video Created',
                'condition': {'videos_created': 1},
                'action': {'type': 'award_xp', 'amount': 100},
                'one_time': True
            },
            'quality_master': {
                'id': 'quality_master',
                'name': 'Quality Master',
                'condition': {'avg_quality': 0.9, 'videos_created': 10},
                'action': {'type': 'award_item', 'item_id': 'rare_quality_boost'},
                'one_time': True
            },
            'speed_demon': {
                'id': 'speed_demon',
                'name': 'Speed Demon',
                'condition': {'fastest_generation': 30},  # seconds
                'action': {'type': 'award_xp', 'amount': 200},
                'one_time': False
            },
            'social_butterfly': {
                'id': 'social_butterfly',
                'name': 'Social Butterfly',
                'condition': {'friends_count': 10, 'posts_created': 5},
                'action': {'type': 'award_artifact', 'artifact_id': 'crystal_of_innovation'},
                'one_time': True
            },
            'battle_warrior': {
                'id': 'battle_warrior',
                'name': 'Battle Warrior',
                'condition': {'battles_won': 5},
                'action': {'type': 'award_item', 'item_id': 'epic_xp_multiplier'},
                'one_time': True
            },
            'milestone_chaser': {
                'id': 'milestone_chaser',
                'name': 'Milestone Chaser',
                'condition': {'milestones_reached': 20},
                'action': {'type': 'award_artifact', 'artifact_id': 'trophy_of_legends'},
                'one_time': True
            },
            'daily_player': {
                'id': 'daily_player',
                'name': 'Daily Player',
                'condition': {'days_active': 7},
                'action': {'type': 'award_xp', 'amount': 150},
                'one_time': False  # Can trigger weekly
            },
            'engagement_king': {
                'id': 'engagement_king',
                'name': 'Engagement King',
                'condition': {'online_time_hours': 50, 'actions_count': 1000},
                'action': {'type': 'award_artifact', 'artifact_id': 'essence_of_creativity'},
                'one_time': True
            }
        }
    
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get or create player profile"""
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'last_active': datetime.utcnow().isoformat(),
                'stats': {},
                'triggers_activated': [],
                'total_actions': 0,
                'online_time_seconds': 0,
                'avatar_url': '',
                'picture_gallery': [],
            }
        profile = self.profiles[user_id]
        profile.setdefault('avatar_url', '')
        profile.setdefault('picture_gallery', [])
        return profile

    def _normalize_picture_url(self, url: str) -> str:
        token = str(url or '').strip()
        if not token:
            return ''
        if token.startswith(('http://', 'https://', '/')):
            return token
        return '/' + token.lstrip('/')

    def set_avatar_url(self, user_id: str, url: str) -> Dict[str, Any]:
        profile = self.get_profile(user_id)
        clean = self._normalize_picture_url(url)
        profile['avatar_url'] = clean
        profile['last_active'] = datetime.utcnow().isoformat()
        if clean:
            self.add_picture(user_id, clean, source='avatar')
        return {'success': True, 'avatar_url': clean}

    def add_picture(self, user_id: str, url: str, source: str = 'manual') -> Dict[str, Any]:
        profile = self.get_profile(user_id)
        clean = self._normalize_picture_url(url)
        if not clean:
            return {'success': False, 'error': 'url_required'}
        gallery = profile.get('picture_gallery') or []
        if not isinstance(gallery, list):
            gallery = []
        entry = {
            'url': clean,
            'source': str(source or 'manual'),
            'added_at': datetime.utcnow().isoformat(),
        }
        if not any(row.get('url') == clean for row in gallery if isinstance(row, dict)):
            gallery.insert(0, entry)
        profile['picture_gallery'] = gallery[:48]
        profile['last_active'] = datetime.utcnow().isoformat()
        return {'success': True, 'picture': entry, 'count': len(profile['picture_gallery'])}

    def camgirl_picture_board(self, user_id: str) -> List[Dict[str, Any]]:
        """Portrait stills from unlocked / favorited camgirl performers."""
        board: List[Dict[str, Any]] = []
        try:
            from backend.services.camgirls_service import list_performers_catalog

            catalog = list_performers_catalog(user_id=user_id, lite=False)
            for row in catalog.get('performers') or []:
                if not isinstance(row, dict):
                    continue
                if not row.get('unlocked') and not row.get('fan_club'):
                    continue
                media = row.get('media') if isinstance(row.get('media'), dict) else {}
                url = str(
                    row.get('picture_url')
                    or (media or {}).get('picture_url')
                    or row.get('avatar_url')
                    or ''
                ).strip()
                if not url:
                    continue
                board.append(
                    {
                        'url': url,
                        'performer_id': row.get('id'),
                        'display_name': row.get('display_name'),
                        'studio_upgrades': row.get('studio_upgrades') or [],
                        'source': 'camgirls_studio',
                    }
                )
        except Exception:
            return board
        return board[:24]

    def get_picture_features(self, user_id: str) -> Dict[str, Any]:
        profile = self.get_profile(user_id)
        gallery = profile.get('picture_gallery') or []
        camgirl_board = self.camgirl_picture_board(user_id)
        return {
            'avatar_url': profile.get('avatar_url') or '',
            'picture_gallery': gallery if isinstance(gallery, list) else [],
            'camgirl_pictures': camgirl_board,
            'total_saved': len(gallery) if isinstance(gallery, list) else 0,
            'total_studio': len(camgirl_board),
        }
    
    def update_profile(self, user_id: str, stats: Dict[str, Any], action_type: str = 'general') -> Dict[str, Any]:
        """Update player profile with new stats"""
        profile = self.get_profile(user_id)
        
        # Update stats
        profile['stats'].update(stats)
        profile['last_active'] = datetime.utcnow().isoformat()
        profile['total_actions'] += 1
        
        # Check triggers
        triggered = self._check_triggers(user_id, profile)
        
        return {
            'profile': profile,
            'triggers_activated': triggered
        }
    
    def _check_triggers(self, user_id: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any triggers should fire"""
        triggered = []
        stats = profile['stats']
        activated = set(profile.get('triggers_activated', []))
        
        for trigger_id, trigger_config in self.triggers.items():
            # Skip if one-time and already activated
            if trigger_config.get('one_time', False) and trigger_id in activated:
                continue
            
            # Check conditions
            conditions = trigger_config.get('condition', {})
            should_trigger = True
            
            for condition_key, condition_value in conditions.items():
                stat_value = stats.get(condition_key, 0)
                
                # Handle different comparison types
                if isinstance(condition_value, (int, float)):
                    if stat_value < condition_value:
                        should_trigger = False
                        break
                elif isinstance(condition_value, dict):
                    # Complex condition
                    if 'min' in condition_value and stat_value < condition_value['min']:
                        should_trigger = False
                        break
                    if 'max' in condition_value and stat_value > condition_value['max']:
                        should_trigger = False
                        break
            
            if should_trigger:
                # Execute action
                action = trigger_config.get('action', {})
                action_result = self._execute_action(user_id, action)
                
                triggered.append({
                    'trigger_id': trigger_id,
                    'trigger_name': trigger_config.get('name', ''),
                    'action': action_result
                })
                
                # Mark as activated
                if trigger_config.get('one_time', False):
                    profile['triggers_activated'].append(trigger_id)
                
                # Record in history
                self.trigger_history.append({
                    'user_id': user_id,
                    'trigger_id': trigger_id,
                    'triggered_at': datetime.utcnow().isoformat(),
                    'action': action_result
                })
        
        return triggered
    
    def _execute_action(self, user_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trigger action"""
        action_type = action.get('type')
        
        try:
            if action_type == 'award_xp':
                from backend.services.hunters_leveling_system import hunters_leveling_system
                if hunters_leveling_system:
                    amount = action.get('amount', 0)
                    hunters_leveling_system.award_xp(user_id, amount, 'trigger_reward', {'trigger': action})
                    return {'type': 'xp', 'amount': amount, 'success': True}
            
            elif action_type == 'award_item':
                from backend.services.items_system import items_system
                if items_system:
                    item_id = action.get('item_id')
                    result = items_system.add_item(user_id, item_id, 1)
                    return {'type': 'item', 'item_id': item_id, 'success': result.get('success', False)}
            
            elif action_type == 'award_artifact':
                from backend.services.artifacts_system import artifacts_system
                if artifacts_system:
                    artifact_id = action.get('artifact_id')
                    result = artifacts_system.discover_artifact(user_id, artifact_id)
                    return {'type': 'artifact', 'artifact_id': artifact_id, 'success': result.get('success', False)}
            
            return {'type': 'unknown', 'success': False}
        except Exception as e:
            return {'type': action_type, 'success': False, 'error': str(e)}
    
    def track_action(self, user_id: str, action_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Track a player action"""
        profile = self.get_profile(user_id)
        
        # Update action count
        profile['total_actions'] += 1
        
        # Update specific action stats
        if 'actions' not in profile['stats']:
            profile['stats']['actions'] = {}
        
        if action_type not in profile['stats']['actions']:
            profile['stats']['actions'][action_type] = 0
        
        profile['stats']['actions'][action_type] += 1
        
        # Update metadata stats
        if metadata:
            for key, value in metadata.items():
                if key not in profile['stats']:
                    profile['stats'][key] = value
                elif isinstance(value, (int, float)):
                    profile['stats'][key] = profile['stats'].get(key, 0) + value
                elif isinstance(value, dict):
                    # Merge dictionaries
                    if key not in profile['stats']:
                        profile['stats'][key] = {}
                    profile['stats'][key].update(value)
        
        # Check triggers
        triggered = self._check_triggers(user_id, profile)
        
        return {
            'success': True,
            'triggers_activated': triggered
        }
    
    def get_trigger_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trigger history for user"""
        user_history = [h for h in self.trigger_history if h['user_id'] == user_id]
        user_history.sort(key=lambda x: x['triggered_at'], reverse=True)
        return user_history[:limit]


# Global instance
player_profiler = PlayerProfiler()

