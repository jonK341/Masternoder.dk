"""
Unified Point System - RECONSTRUCTED
Clean, logical, single source of truth for all points
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)


class UnifiedPointSystem:
    """
    RECONSTRUCTED Unified Point System
    Single source of truth - makes one sense, not a hallucination
    """
    
    # Point Categories - Clear and Logical
    CATEGORIES = {
        'CORE': {
            'name': 'Core Points',
            'description': 'Fundamental progression points',
            'points': ['xp', 'level', 'prestige']
        },
        'ECONOMY': {
            'name': 'Economy',
            'description': 'Currency and economic resources',
            'points': ['coins', 'credits', 'tokens']
        },
        'STATS': {
            'name': 'Character Stats',
            'description': 'Character attribute points',
            'points': ['creativity', 'efficiency', 'quality', 'knowledge', 'social']
        },
        'ACHIEVEMENTS': {
            'name': 'Achievements',
            'description': 'Achievement and milestone points',
            'points': ['achievements', 'trophies', 'milestones']
        },
        'ACTIVITY': {
            'name': 'Activity',
            'description': 'Activity-based points',
            'points': ['videos', 'generations', 'time_played', 'login_streak']
        },
        'BATTLE': {
            'name': 'Battle',
            'description': 'Battle and combat points',
            'points': ['battle_wins', 'battle_points', 'battle_streak']
        },
        'SOCIAL': {
            'name': 'Social',
            'description': 'Social interaction points',
            'points': ['friends', 'followers', 'chat', 'social_interactions']
        },
        'METAL': {
            'name': 'Metal Systems',
            'description': 'Metal system points',
            'points': ['territory', 'sex_metal', 'porno_rights', 'mtg', 'trophy_hunt']
        },
        'RESOURCES': {
            'name': 'Resources',
            'description': 'Resource generation points',
            'points': ['energy', 'materials', 'knowledge', 'technology']
        }
    }
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialize the unified point system
        
        Args:
            data_dir: Directory to store point data
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Single source of truth - one JSON file per user
        self.points_file = os.path.join(data_dir, 'unified_points.json')
        
        # In-memory cache
        self.cache = {}  # {user_id: {data: {...}, timestamp: ...}}
        self.cache_ttl = 60  # 60 seconds cache
        
        # Initialize default structure
        self._initialize_structure()
    
    def _initialize_structure(self):
        """Initialize the default point structure"""
        self.default_points = {
            # CORE
            'xp': 0,
            'level': 1,
            'level_progress': 0.0,
            'prestige': 0,
            
            # ECONOMY
            'coins': 0,
            'credits': 0,
            'tokens': 0,
            'total_earned': 0,
            'total_spent': 0,
            
            # STATS
            'stats_total': 0,
            'stats_available': 0,
            'stats_used': 0,
            'creativity': 0,
            'efficiency': 0,
            'quality': 0,
            'knowledge': 0,
            'social': 0,
            
            # ACHIEVEMENTS
            'achievements': 0,
            'achievement_points': 0,
            'trophies': 0,
            'trophy_points': 0,
            'milestones': 0,
            'milestone_points': 0,
            
            # ACTIVITY
            'videos_created': 0,
            'videos_watched': 0,
            'videos_shared': 0,
            'generations': 0,
            'time_played': 0,
            'login_streak': 0,
            'daily_logins': 0,
            
            # BATTLE
            'battle_wins': 0,
            'battle_losses': 0,
            'battle_draws': 0,
            'battle_points': 0,
            'battle_streak': 0,
            
            # SOCIAL
            'friends': 0,
            'followers': 0,
            'following': 0,
            'chat_points': 0,
            'chat_messages': 0,
            'social_interactions': 0,
            
            # METAL
            'territory_points': 0,
            'territory_level': 1,
            'sex_metal_points': 0,
            'sex_metal_level': 1,
            'porno_rights_points': 0,
            'porno_rights_level': 1,
            'mtg_points': 0,
            'mtg_level': 1,
            'trophy_hunt_points': 0,
            'trophy_hunt_level': 1,
            
            # RESOURCES
            'resource_energy': 0.0,
            'resource_materials': 0.0,
            'resource_knowledge': 0.0,
            'resource_technology': 0.0,
            
            # METADATA
            'last_updated': datetime.utcnow().isoformat(),
            'version': '2.0_reconstructed'
        }
    
    def get_user_points(self, user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get all points for a user - SINGLE SOURCE OF TRUTH
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from file
            
        Returns:
            Complete points dictionary
        """
        # Check cache
        if not force_refresh and user_id in self.cache:
            cached = self.cache[user_id]
            age = (datetime.utcnow() - datetime.fromisoformat(cached['timestamp'])).total_seconds()
            if age < self.cache_ttl:
                return cached['data'].copy()
        
        # Load from file
        points = self._load_from_file(user_id)
        
        # Merge with defaults to ensure all keys exist
        result = self.default_points.copy()
        result.update(points)
        
        # Validate
        result = self._validate_points(result)
        
        # Cache
        self.cache[user_id] = {
            'data': result.copy(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return result
    
    def add_points(self, user_id: str, category: str, point_type: str, 
                   amount: float, source: str = 'unknown') -> Dict[str, Any]:
        """
        Add points to a user - CLEAR AND LOGICAL
        
        Args:
            user_id: User identifier
            category: Point category (CORE, ECONOMY, STATS, etc.)
            point_type: Specific point type (xp, coins, creativity, etc.)
            amount: Amount to add
            source: Source of the points
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Validate category
            if category not in self.CATEGORIES:
                return {'success': False, 'error': f'Invalid category: {category}'}
            
            # Validate point type
            valid_types = self.CATEGORIES[category]['points']
            if point_type not in valid_types:
                return {'success': False, 'error': f'Invalid point type: {point_type} for category: {category}'}
            
            # Get current points
            points = self.get_user_points(user_id, force_refresh=True)
            
            # Map point type to actual key
            point_key = self._map_point_type(point_type, category)
            
            # Add points
            current_value = points.get(point_key, 0)
            new_value = current_value + amount
            
            # Ensure non-negative
            if new_value < 0:
                new_value = 0
            
            points[point_key] = new_value
            
            # Update totals if applicable
            self._update_totals(points, category, point_type, amount)
            
            # Update metadata
            points['last_updated'] = datetime.utcnow().isoformat()
            
            # Save to file
            self._save_to_file(user_id, points)
            
            # Clear cache
            if user_id in self.cache:
                del self.cache[user_id]
            
            return {
                'success': True,
                'user_id': user_id,
                'category': category,
                'point_type': point_type,
                'point_key': point_key,
                'amount_added': amount,
                'previous_value': current_value,
                'new_value': new_value,
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Error adding points: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def set_points(self, user_id: str, category: str, point_type: str, 
                   value: float) -> Dict[str, Any]:
        """
        Set points to a specific value
        
        Args:
            user_id: User identifier
            category: Point category
            point_type: Point type
            value: Value to set
            
        Returns:
            Result dictionary
        """
        try:
            # Get current points
            points = self.get_user_points(user_id, force_refresh=True)
            
            # Map point type
            point_key = self._map_point_type(point_type, category)
            old_value = points.get(point_key, 0)
            
            # Set value
            points[point_key] = max(0, value)  # Ensure non-negative
            points['last_updated'] = datetime.utcnow().isoformat()
            
            # Save
            self._save_to_file(user_id, points)
            
            # Clear cache
            if user_id in self.cache:
                del self.cache[user_id]
            
            return {
                'success': True,
                'point_key': point_key,
                'old_value': old_value,
                'new_value': points[point_key]
            }
            
        except Exception as e:
            logger.error(f"Error setting points: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_category_points(self, user_id: str, category: str) -> Dict[str, Any]:
        """
        Get all points for a specific category
        
        Args:
            user_id: User identifier
            category: Category name
            
        Returns:
            Category points dictionary
        """
        if category not in self.CATEGORIES:
            return {'success': False, 'error': f'Invalid category: {category}'}
        
        all_points = self.get_user_points(user_id)
        category_info = self.CATEGORIES[category]
        
        result = {
            'category': category,
            'name': category_info['name'],
            'description': category_info['description'],
            'points': {}
        }
        
        for point_type in category_info['points']:
            point_key = self._map_point_type(point_type, category)
            result['points'][point_type] = {
                'key': point_key,
                'value': all_points.get(point_key, 0)
            }
        
        return result
    
    def get_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of all points organized by category
        
        Args:
            user_id: User identifier
            
        Returns:
            Summary dictionary
        """
        all_points = self.get_user_points(user_id)
        
        summary = {
            'user_id': user_id,
            'categories': {},
            'totals': {},
            'last_updated': all_points.get('last_updated'),
            'version': all_points.get('version', '2.0_reconstructed')
        }
        
        # Get points by category
        for category, info in self.CATEGORIES.items():
            category_points = {}
            category_total = 0
            
            for point_type in info['points']:
                point_key = self._map_point_type(point_type, category)
                value = all_points.get(point_key, 0)
                category_points[point_type] = value
                
                # Add to total if it's a point value (not a count)
                if 'points' in point_key.lower() or point_key in ['xp', 'coins', 'credits', 'tokens']:
                    category_total += value
            
            summary['categories'][category] = {
                'name': info['name'],
                'points': category_points,
                'total': category_total
            }
        
        # Calculate grand totals
        summary['totals'] = {
            'total_xp': all_points.get('xp', 0),
            'total_economy': (
                all_points.get('coins', 0) +
                all_points.get('credits', 0) +
                all_points.get('tokens', 0)
            ),
            'total_stats': all_points.get('stats_total', 0),
            'total_achievements': (
                all_points.get('achievement_points', 0) +
                all_points.get('trophy_points', 0) +
                all_points.get('milestone_points', 0)
            ),
            'total_battle': all_points.get('battle_points', 0),
            'total_metal': (
                all_points.get('territory_points', 0) +
                all_points.get('sex_metal_points', 0) +
                all_points.get('porno_rights_points', 0) +
                all_points.get('mtg_points', 0) +
                all_points.get('trophy_hunt_points', 0)
            )
        }
        
        return summary
    
    def _map_point_type(self, point_type: str, category: str) -> str:
        """
        Map point type to actual key in points dictionary
        
        Args:
            point_type: Point type name
            category: Category name
            
        Returns:
            Actual key name
        """
        mapping = {
            'CORE': {
                'xp': 'xp',
                'level': 'level',
                'prestige': 'prestige'
            },
            'ECONOMY': {
                'coins': 'coins',
                'credits': 'credits',
                'tokens': 'tokens'
            },
            'STATS': {
                'creativity': 'creativity',
                'efficiency': 'efficiency',
                'quality': 'quality',
                'knowledge': 'knowledge',
                'social': 'social'
            },
            'ACHIEVEMENTS': {
                'achievements': 'achievements',
                'trophies': 'trophies',
                'milestones': 'milestones'
            },
            'ACTIVITY': {
                'videos': 'videos_created',
                'generations': 'generations',
                'time_played': 'time_played',
                'login_streak': 'login_streak'
            },
            'BATTLE': {
                'battle_wins': 'battle_wins',
                'battle_points': 'battle_points',
                'battle_streak': 'battle_streak'
            },
            'SOCIAL': {
                'friends': 'friends',
                'followers': 'followers',
                'chat': 'chat_points',
                'social_interactions': 'social_interactions'
            },
            'METAL': {
                'territory': 'territory_points',
                'sex_metal': 'sex_metal_points',
                'porno_rights': 'porno_rights_points',
                'mtg': 'mtg_points',
                'trophy_hunt': 'trophy_hunt_points'
            },
            'RESOURCES': {
                'energy': 'resource_energy',
                'materials': 'resource_materials',
                'knowledge': 'resource_knowledge',
                'technology': 'resource_technology'
            }
        }
        
        return mapping.get(category, {}).get(point_type, point_type)
    
    def _update_totals(self, points: Dict[str, Any], category: str, 
                      point_type: str, amount: float):
        """Update total values when points are added"""
        if category == 'STATS':
            # Update stats totals
            stats_used = (
                points.get('creativity', 0) +
                points.get('efficiency', 0) +
                points.get('quality', 0) +
                points.get('knowledge', 0) +
                points.get('social', 0)
            )
            points['stats_used'] = stats_used
            
        elif category == 'ECONOMY':
            # Update economy totals
            if amount > 0:
                points['total_earned'] = points.get('total_earned', 0) + amount
            else:
                points['total_spent'] = points.get('total_spent', 0) + abs(amount)
    
    def _validate_points(self, points: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all points - ensure consistency
        
        Args:
            points: Points dictionary
            
        Returns:
            Validated points dictionary
        """
        # Ensure all required keys exist
        for key, default_value in self.default_points.items():
            if key not in points:
                points[key] = default_value
        
        # Ensure non-negative for point values
        point_keys = [k for k in points.keys() if 'point' in k.lower() or 
                     k in ['xp', 'coins', 'credits', 'tokens', 'level', 'prestige']]
        for key in point_keys:
            if isinstance(points[key], (int, float)) and points[key] < 0:
                points[key] = 0
        
        # Validate stats consistency
        stats_used = (
            points.get('creativity', 0) +
            points.get('efficiency', 0) +
            points.get('quality', 0) +
            points.get('knowledge', 0) +
            points.get('social', 0)
        )
        points['stats_used'] = stats_used
        
        return points
    
    def _load_from_file(self, user_id: str) -> Dict[str, Any]:
        """Load points from file"""
        try:
            user_file = os.path.join(self.data_dir, f'unified_points_{user_id}.json')
            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading points from file: {e}")
        
        return {}
    
    def _save_to_file(self, user_id: str, points: Dict[str, Any]) -> bool:
        """
        Save points to file - ONE JSON FILE PER USER
        
        Args:
            user_id: User identifier
            points: Points dictionary
            
        Returns:
            True if successful
        """
        try:
            # ONE JSON FILE - Rule #1 compliance
            user_file = os.path.join(self.data_dir, f'unified_points_{user_id}.json')
            
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(points, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error saving points to file: {e}")
            return False


# Global instance
unified_point_system = UnifiedPointSystem()

