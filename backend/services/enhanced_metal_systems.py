"""
Enhanced Metal Systems - Integrated with refresh.hash, International GPS, and Jons VoldsRøvID Division
Connects Territory Metal, Sex Metal, Porno Rights Metal, MTG Metal, Trophy Hunt Metal
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import hashlib
import json
import random

# Import existing systems
try:
    from backend.services.hash_system import hash_system
except ImportError:
    hash_system = None

try:
    from backend.services.hardcore_ai_metal_magi import hardcore_ai_metal_magi
except ImportError:
    hardcore_ai_metal_magi = None

try:
    from backend.services.trophy_system import TrophySystem
    trophy_system = TrophySystem()
except ImportError:
    trophy_system = None


class EnhancedMetalSystems:
    """Enhanced Metal Systems with refresh.hash, GPS, and VoldsRøvID integration"""
    
    def __init__(self):
        # Core metal systems
        self.territory_metal = defaultdict(dict)  # {user_id: territory_data}
        self.sex_metal = defaultdict(dict)  # {user_id: sex_metal_data}
        self.porno_rights_metal = defaultdict(dict)  # {user_id: porno_rights_data}
        self.mtg_metal = defaultdict(dict)  # {user_id: mtg_metal_data}
        self.trophy_hunt_metal = defaultdict(dict)  # {user_id: trophy_hunt_data}
        
        # GPS tracking
        self.gps_locations = defaultdict(dict)  # {user_id: {lat, lng, timestamp}}
        self.international_gps = defaultdict(list)  # {user_id: [gps_history]}
        
        # VoldsRøvID Division
        self.voldsrov_division = defaultdict(dict)  # {user_id: voldsrov_data}
        
        # Refresh hash system
        self.refresh_hashes = defaultdict(dict)  # {user_id: {system: hash}}
        
        # Street Minds connection
        self.street_minds = defaultdict(dict)  # {user_id: street_mind_data}
        
        # Metal system connections
        self.metal_connections = defaultdict(dict)  # {user_id: {connections}}
        
        # Zero Points Stats - All initialized at 0
        self.zero_points_stats = defaultdict(dict)  # {user_id: zero_stats}
    
    def initialize_user(self, user_id: str) -> Dict[str, Any]:
        """Initialize user with all metal systems"""
        # Initialize Territory Metal
        if user_id not in self.territory_metal:
            self.territory_metal[user_id] = {
                'territory_level': 1,
                'territory_points': 0,
                'controlled_territories': [],
                'territory_hash': None,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize Sex Metal
        if user_id not in self.sex_metal:
            self.sex_metal[user_id] = {
                'sex_metal_level': 1,
                'sex_metal_points': 0,
                'sex_metal_hash': None,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize Porno Rights Metal
        if user_id not in self.porno_rights_metal:
            self.porno_rights_metal[user_id] = {
                'rights_level': 1,
                'rights_points': 0,
                'rights_hash': None,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize MTG Metal
        if user_id not in self.mtg_metal:
            self.mtg_metal[user_id] = {
                'mtg_level': 1,
                'mana_power': 100,
                'mtg_points': 0,
                'mtg_hash': None,
                'spells_unlocked': [],
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize Trophy Hunt Metal
        if user_id not in self.trophy_hunt_metal:
            self.trophy_hunt_metal[user_id] = {
                'hunt_level': 1,
                'trophies_collected': 0,
                'hunt_points': 0,
                'hunt_hash': None,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize VoldsRøvID Division
        if user_id not in self.voldsrov_division:
            self.voldsrov_division[user_id] = {
                'voldsrov_id': 'Jons_VoldsRøvID_Ny_§',
                'division_level': 1,
                'division_points': 0,
                'division_hash': None,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize Street Minds
        if user_id not in self.street_minds:
            self.street_minds[user_id] = {
                'mind_level': 1,
                'mind_connections': [],
                'territory_connection': False,
                'sex_connection': False,
                'porno_rights_connection': False,
                'mtg_connection': False,
                'trophy_hunt_connection': False,
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Initialize Zero Points Stats
        if user_id not in self.zero_points_stats:
            self.zero_points_stats[user_id] = {
                # Battle Stats
                'battle_wins': 0,
                'battle_losses': 0,
                'battle_draws': 0,
                'battle_streak': 0,
                'total_battles': 0,
                'battle_points': 0,
                
                # Social Stats
                'friends_count': 0,
                'followers_count': 0,
                'following_count': 0,
                'social_points': 0,
                'social_interactions': 0,
                'messages_sent': 0,
                'messages_received': 0,
                
                # Economic Stats
                'coins': 0,
                'credits': 0,
                'tokens': 0,
                'total_earned': 0,
                'total_spent': 0,
                'economic_value': 0,
                
                # Activity Stats
                'daily_logins': 0,
                'login_streak': 0,
                'longest_streak': 0,
                'total_sessions': 0,
                'session_time': 0,
                'actions_today': 0,
                'actions_total': 0,
                
                # Achievement Stats
                'achievements_earned': 0,
                'achievement_points': 0,
                'trophies_collected': 0,
                'badges_earned': 0,
                'medals_earned': 0,
                
                # Video Stats
                'videos_created': 0,
                'videos_watched': 0,
                'videos_shared': 0,
                'videos_liked': 0,
                'videos_commented': 0,
                'total_watch_time': 0,
                
                # Quality Stats
                'perfect_generations': 0,
                'high_quality_generations': 0,
                'average_quality_score': 0,
                'quality_points': 0,
                
                # XP Stats
                'total_xp': 0,
                'xp_today': 0,
                'xp_this_week': 0,
                'xp_this_month': 0,
                'xp_from_videos': 0,
                'xp_from_battles': 0,
                'xp_from_achievements': 0,
                
                # Stats Points
                'stats_points_total': 0,
                'stats_points_available': 0,
                'stats_points_used': 0,
                'creativity_points': 0,
                'efficiency_points': 0,
                'quality_points': 0,
                'social_points': 0,
                'knowledge_points': 0,
                
                # Metal System Stats
                'metal_points_total': 0,
                'metal_levels_total': 0,
                'metal_connections_total': 0,
                
                # Time Stats
                'time_played': 0,
                'time_in_battles': 0,
                'time_in_generator': 0,
                'time_in_gallery': 0,
                'time_in_social': 0,
                
                # Performance Stats
                'fastest_generation': 0,
                'average_generation_time': 0,
                'total_generation_time': 0,
                'success_rate': 0,
                'error_count': 0,
                
                # Engagement Stats
                'clicks_total': 0,
                'clicks_today': 0,
                'page_views': 0,
                'unique_pages_visited': 0,
                'return_visits': 0,
                
                # Network Stats
                'guild_memberships': 0,
                'clan_memberships': 0,
                'guild_contributions': 0,
                'clan_contributions': 0,
                'war_participations': 0,
                
                # Special Stats
                'prestige_count': 0,
                'resets_count': 0,
                'special_events': 0,
                'limited_editions': 0,
                'exclusive_items': 0,
                
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat()
            }
        
        # Generate refresh hashes for all systems
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'user_id': user_id,
            'systems_initialized': True
        }
    
    def _refresh_all_hashes(self, user_id: str) -> None:
        """Generate refresh hashes for all metal systems"""
        systems = {
            'territory': self.territory_metal.get(user_id, {}),
            'sex': self.sex_metal.get(user_id, {}),
            'porno_rights': self.porno_rights_metal.get(user_id, {}),
            'mtg': self.mtg_metal.get(user_id, {}),
            'trophy_hunt': self.trophy_hunt_metal.get(user_id, {}),
            'voldsrov': self.voldsrov_division.get(user_id, {}),
            'zero_points_stats': self.zero_points_stats.get(user_id, {})
        }
        
        for system_name, system_data in systems.items():
            if system_data:
                data_str = json.dumps(system_data, sort_keys=True)
                hash_value = hashlib.sha256(f"{user_id}:{system_name}:{data_str}".encode()).hexdigest()
                
                if user_id not in self.refresh_hashes:
                    self.refresh_hashes[user_id] = {}
                
                self.refresh_hashes[user_id][system_name] = {
                    'hash': hash_value,
                    'timestamp': datetime.utcnow().isoformat(),
                    'system': system_name
                }
                
                # Update system hash
                if system_name == 'territory':
                    self.territory_metal[user_id]['territory_hash'] = hash_value
                elif system_name == 'sex':
                    self.sex_metal[user_id]['sex_metal_hash'] = hash_value
                elif system_name == 'porno_rights':
                    self.porno_rights_metal[user_id]['rights_hash'] = hash_value
                elif system_name == 'mtg':
                    self.mtg_metal[user_id]['mtg_hash'] = hash_value
                elif system_name == 'trophy_hunt':
                    self.trophy_hunt_metal[user_id]['hunt_hash'] = hash_value
                elif system_name == 'voldsrov':
                    self.voldsrov_division[user_id]['division_hash'] = hash_value
    
    def update_gps_location(self, user_id: str, lat: float, lng: float, 
                           country: str = None, city: str = None) -> Dict[str, Any]:
        """Update International GPS location"""
        location = {
            'user_id': user_id,
            'lat': lat,
            'lng': lng,
            'country': country,
            'city': city,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.gps_locations[user_id] = location
        
        # Add to international GPS history
        if user_id not in self.international_gps:
            self.international_gps[user_id] = []
        
        self.international_gps[user_id].append(location)
        
        # Keep last 100 locations
        if len(self.international_gps[user_id]) > 100:
            self.international_gps[user_id] = self.international_gps[user_id][-100:]
        
        # Refresh hashes after GPS update
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'location': location
        }
    
    def add_territory_metal_points(self, user_id: str, points: int) -> Dict[str, Any]:
        """Add points to Territory Metal"""
        if user_id not in self.territory_metal:
            self.initialize_user(user_id)
        
        self.territory_metal[user_id]['territory_points'] += points
        
        # Check for level up
        current_level = self.territory_metal[user_id]['territory_level']
        required_points = current_level * 500
        
        if self.territory_metal[user_id]['territory_points'] >= required_points:
            self.territory_metal[user_id]['territory_level'] += 1
        
        # Refresh hash
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'points_added': points,
            'total_points': self.territory_metal[user_id]['territory_points'],
            'level': self.territory_metal[user_id]['territory_level']
        }
    
    def add_sex_metal_points(self, user_id: str, points: int) -> Dict[str, Any]:
        """Add points to Sex Metal"""
        if user_id not in self.sex_metal:
            self.initialize_user(user_id)
        
        self.sex_metal[user_id]['sex_metal_points'] += points
        
        # Check for level up
        current_level = self.sex_metal[user_id]['sex_metal_level']
        required_points = current_level * 300
        
        if self.sex_metal[user_id]['sex_metal_points'] >= required_points:
            self.sex_metal[user_id]['sex_metal_level'] += 1
        
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'points_added': points,
            'total_points': self.sex_metal[user_id]['sex_metal_points'],
            'level': self.sex_metal[user_id]['sex_metal_level']
        }
    
    def add_porno_rights_metal_points(self, user_id: str, points: int) -> Dict[str, Any]:
        """Add points to Porno Rights Metal"""
        if user_id not in self.porno_rights_metal:
            self.initialize_user(user_id)
        
        self.porno_rights_metal[user_id]['rights_points'] += points
        
        current_level = self.porno_rights_metal[user_id]['rights_level']
        required_points = current_level * 400
        
        if self.porno_rights_metal[user_id]['rights_points'] >= required_points:
            self.porno_rights_metal[user_id]['rights_level'] += 1
        
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'points_added': points,
            'total_points': self.porno_rights_metal[user_id]['rights_points'],
            'level': self.porno_rights_metal[user_id]['rights_level']
        }
    
    def add_mtg_metal_points(self, user_id: str, points: int) -> Dict[str, Any]:
        """Add points to MTG Metal"""
        if user_id not in self.mtg_metal:
            self.initialize_user(user_id)
        
        self.mtg_metal[user_id]['mtg_points'] += points
        self.mtg_metal[user_id]['mana_power'] += points // 10
        
        current_level = self.mtg_metal[user_id]['mtg_level']
        required_points = current_level * 600
        
        if self.mtg_metal[user_id]['mtg_points'] >= required_points:
            self.mtg_metal[user_id]['mtg_level'] += 1
            # Unlock new spell
            spell_name = f"Spell_Level_{self.mtg_metal[user_id]['mtg_level']}"
            if spell_name not in self.mtg_metal[user_id]['spells_unlocked']:
                self.mtg_metal[user_id]['spells_unlocked'].append(spell_name)
        
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'points_added': points,
            'total_points': self.mtg_metal[user_id]['mtg_points'],
            'mana_power': self.mtg_metal[user_id]['mana_power'],
            'level': self.mtg_metal[user_id]['mtg_level']
        }
    
    def add_trophy_hunt_metal_points(self, user_id: str, points: int) -> Dict[str, Any]:
        """Add points to Trophy Hunt Metal"""
        if user_id not in self.trophy_hunt_metal:
            self.initialize_user(user_id)
        
        self.trophy_hunt_metal[user_id]['hunt_points'] += points
        
        current_level = self.trophy_hunt_metal[user_id]['hunt_level']
        required_points = current_level * 500
        
        if self.trophy_hunt_metal[user_id]['hunt_points'] >= required_points:
            self.trophy_hunt_metal[user_id]['hunt_level'] += 1
            self.trophy_hunt_metal[user_id]['trophies_collected'] += 1
        
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'points_added': points,
            'total_points': self.trophy_hunt_metal[user_id]['hunt_points'],
            'trophies_collected': self.trophy_hunt_metal[user_id]['trophies_collected'],
            'level': self.trophy_hunt_metal[user_id]['hunt_level']
        }
    
    def connect_street_minds(self, user_id: str, metal_type: str) -> Dict[str, Any]:
        """Connect Street Minds with metal systems"""
        if user_id not in self.street_minds:
            self.initialize_user(user_id)
        
        connections = {
            'territory': 'territory_connection',
            'sex': 'sex_connection',
            'porno_rights': 'porno_rights_connection',
            'mtg': 'mtg_connection',
            'trophy_hunt': 'trophy_hunt_connection'
        }
        
        if metal_type in connections:
            connection_key = connections[metal_type]
            if not self.street_minds[user_id][connection_key]:
                self.street_minds[user_id][connection_key] = True
                self.street_minds[user_id]['mind_connections'].append(metal_type)
                self.street_minds[user_id]['mind_level'] += 1
        
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'connections': self.street_minds[user_id]['mind_connections'],
            'mind_level': self.street_minds[user_id]['mind_level']
        }
    
    def get_user_systems(self, user_id: str) -> Dict[str, Any]:
        """
        Get all metal system data for a user
        Returns data in format expected by unified_point_counter
        """
        if user_id not in self.territory_metal:
            self.initialize_user(user_id)
        
        territory = self.territory_metal.get(user_id, {})
        sex = self.sex_metal.get(user_id, {})
        rights = self.porno_rights_metal.get(user_id, {})
        mtg = self.mtg_metal.get(user_id, {})
        hunt = self.trophy_hunt_metal.get(user_id, {})
        
        return {
            'territory': {
                'territory_points': territory.get('territory_points', 0),
                'territory_level': territory.get('territory_level', 1)
            },
            'sex': {
                'sex_metal_points': sex.get('sex_metal_points', 0),
                'sex_metal_level': sex.get('sex_metal_level', 1)
            },
            'porno_rights': {
                'rights_points': rights.get('rights_points', 0),
                'rights_level': rights.get('rights_level', 1)
            },
            'mtg': {
                'mtg_points': mtg.get('mtg_points', 0),
                'mtg_level': mtg.get('mtg_level', 1)
            },
            'trophy_hunt': {
                'hunt_points': hunt.get('hunt_points', 0),
                'hunt_level': hunt.get('hunt_level', 1)
            }
        }
    
    def get_all_metal_stats(self, user_id: str) -> Dict[str, Any]:
        """Get all metal system stats"""
        if user_id not in self.territory_metal:
            self.initialize_user(user_id)
        
        return {
            'success': True,
            'user_id': user_id,
            'territory_metal': self.territory_metal[user_id],
            'sex_metal': self.sex_metal[user_id],
            'porno_rights_metal': self.porno_rights_metal[user_id],
            'mtg_metal': self.mtg_metal[user_id],
            'trophy_hunt_metal': self.trophy_hunt_metal[user_id],
            'voldsrov_division': self.voldsrov_division[user_id],
            'street_minds': self.street_minds[user_id],
            'zero_points_stats': self.zero_points_stats.get(user_id, {}),
            'gps_location': self.gps_locations.get(user_id, {}),
            'refresh_hashes': self.refresh_hashes.get(user_id, {}),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def update_zero_points_stat(self, user_id: str, stat_name: str, value: int = None, increment: int = None) -> Dict[str, Any]:
        """Update a zero points stat"""
        if user_id not in self.zero_points_stats:
            self.initialize_user(user_id)
        
        if stat_name not in self.zero_points_stats[user_id]:
            return {'success': False, 'error': f'Stat {stat_name} not found'}
        
        if value is not None:
            self.zero_points_stats[user_id][stat_name] = value
        elif increment is not None:
            self.zero_points_stats[user_id][stat_name] = self.zero_points_stats[user_id].get(stat_name, 0) + increment
        else:
            return {'success': False, 'error': 'Either value or increment must be provided'}
        
        self.zero_points_stats[user_id]['last_updated'] = datetime.utcnow().isoformat()
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'stat_name': stat_name,
            'new_value': self.zero_points_stats[user_id][stat_name]
        }
    
    def get_zero_points_stats(self, user_id: str) -> Dict[str, Any]:
        """Get all zero points stats"""
        if user_id not in self.zero_points_stats:
            self.initialize_user(user_id)
        
        return {
            'success': True,
            'user_id': user_id,
            'zero_points_stats': self.zero_points_stats[user_id],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def increment_multiple_stats(self, user_id: str, stats_updates: Dict[str, int]) -> Dict[str, Any]:
        """Increment multiple zero points stats at once"""
        if user_id not in self.zero_points_stats:
            self.initialize_user(user_id)
        
        updated_stats = {}
        for stat_name, increment in stats_updates.items():
            if stat_name in self.zero_points_stats[user_id]:
                self.zero_points_stats[user_id][stat_name] = self.zero_points_stats[user_id].get(stat_name, 0) + increment
                updated_stats[stat_name] = self.zero_points_stats[user_id][stat_name]
        
        self.zero_points_stats[user_id]['last_updated'] = datetime.utcnow().isoformat()
        self._refresh_all_hashes(user_id)
        
        return {
            'success': True,
            'updated_stats': updated_stats,
            'total_updated': len(updated_stats)
        }
    
    def get_refresh_hash(self, user_id: str, system: str = None) -> Dict[str, Any]:
        """Get refresh hash for system(s)"""
        if user_id not in self.refresh_hashes:
            self.initialize_user(user_id)
        
        if system:
            return {
                'success': True,
                'system': system,
                'hash': self.refresh_hashes[user_id].get(system, {})
            }
        else:
            return {
                'success': True,
                'all_hashes': self.refresh_hashes.get(user_id, {})
            }


# Global instance
enhanced_metal_systems = EnhancedMetalSystems()

