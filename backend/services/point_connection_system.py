"""
Point Connection System
Systematic solution to connect ALL points from ALL systems
Ensures no points are lost and everything counts
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Import unified systems
try:
    from backend.services.unified_point_counter import UnifiedPointCounter
    from backend.services.unified_points_database import unified_points_db
except ImportError:
    UnifiedPointCounter = None
    unified_points_db = None


class PointConnectionSystem:
    """
    Systematic point connection system
    Connects all point sources and ensures everything counts
    """
    
    def __init__(self):
        self.unified_counter = UnifiedPointCounter() if UnifiedPointCounter else None
        self.connection_map = {
            # Core Systems
            'xp_system': {
                'module': 'backend.services.xp_system',
                'points': ['xp', 'level'],
                'connected': True
            },
            'activity_points': {
                'module': 'backend.services.activity_points_system',
                'points': ['activity_points', 'page_views', 'clicks', 'scrolls'],
                'connected': True
            },
            'theme_points': {
                'module': 'backend.services.theme_points_system',
                'points': ['theme_points'],
                'connected': True
            },
            'chat_points': {
                'module': 'backend.services.chat_points',
                'points': ['chat_points', 'messages'],
                'connected': True
            },
            'trophy_system': {
                'module': 'backend.services.trophy_system',
                'points': ['trophy_points', 'trophy_level'],
                'connected': True
            },
            'battle_intelligence': {
                'module': 'backend.services.battle_intelligence_system',
                'points': ['battle_points', 'battle_wins', 'battle_losses'],
                'connected': True
            },
            'game_achievements': {
                'module': 'backend.services.game_achievements',
                'points': ['achievement_points', 'achievements'],
                'connected': True
            },
            'hunters_leveling': {
                'module': 'backend.services.hunters_leveling_system',
                'points': ['stats_points', 'creativity', 'efficiency', 'quality'],
                'connected': True
            },
            'enhanced_metal': {
                'module': 'backend.services.enhanced_metal_systems',
                'points': ['territory_points', 'sex_metal_points', 'porno_rights_points', 'mtg_points'],
                'connected': True
            },
            'graduation_points': {
                'module': 'backend.services.graduation_points',
                'points': ['graduation_points'],
                'connected': True
            },
            'generation_tracker': {
                'module': 'backend.services.generation_tracker',
                'points': ['generation_points', 'videos_created'],
                'connected': True
            },
            'krimetime_warzone': {
                'module': 'backend.services.krimetime_warzone',
                'points': ['krimetime_points', 'warzone_wins'],
                'connected': True
            },
            'guild_clan': {
                'module': 'backend.services.guild_clan_system',
                'points': ['guild_points', 'clan_points'],
                'connected': True
            },
            'rewards_system': {
                'module': 'backend.services.rewards_system',
                'points': ['reward_points', 'bonus_points'],
                'connected': True
            },
            'quest_system': {
                'module': 'backend.services.quest_system',
                'points': ['quest_points', 'quest_xp'],
                'connected': True
            },
            'rights_law_system': {
                'module': 'backend.services.rights_law_system',
                'points': ['rights_points', 'social_points'],
                'connected': True
            },
        }
    
    def connect_all_points(self, user_id: str) -> Dict[str, Any]:
        """
        Connect all points from all systems
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with all connected points
        """
        all_connected_points = {}
        connection_status = {}
        
        for system_name, system_info in self.connection_map.items():
            try:
                # Try to import and get points
                module_path = system_info['module']
                module = __import__(module_path, fromlist=[''])
                
                points = {}
                
                # Try different methods to get points
                if hasattr(module, 'get_user_points'):
                    points = module.get_user_points(user_id) or {}
                elif hasattr(module, 'get_points'):
                    points = module.get_points(user_id) or {}
                elif hasattr(module, 'get_user_stats'):
                    stats = module.get_user_stats(user_id) or {}
                    points = {k: v for k, v in stats.items() if 'point' in k.lower() or 'level' in k.lower()}
                elif system_name == 'xp_system' and hasattr(module, 'XPSystem'):
                    xp_system = module.XPSystem()
                    if hasattr(xp_system, 'get_user_xp'):
                        xp_data = xp_system.get_user_xp(user_id) or {}
                        points = {'xp': xp_data.get('xp', 0), 'level': xp_data.get('level', 1)}
                elif system_name == 'activity_points' and hasattr(module, 'activity_points'):
                    activity_system = module.activity_points
                    if hasattr(activity_system, 'get_user_stats'):
                        stats = activity_system.get_user_stats(user_id) or {}
                        points = {'activity_points': stats.get('total_points', 0)}
                
                # Merge points
                for point_key in system_info['points']:
                    if point_key in points:
                        all_connected_points[point_key] = points[point_key]
                
                connection_status[system_name] = {
                    'connected': True,
                    'points_found': len([p for p in system_info['points'] if p in all_connected_points]),
                    'total_points': len(points)
                }
                
            except Exception as e:
                connection_status[system_name] = {
                    'connected': False,
                    'error': str(e)
                }
        
        # Save to database
        if unified_points_db:
            unified_points_db.save_user_points(user_id, all_connected_points)
        
        return {
            'user_id': user_id,
            'all_points': all_connected_points,
            'connection_status': connection_status,
            'total_point_types': len(all_connected_points),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def ensure_point_counting(self, user_id: str, point_type: str, 
                             points: float, source: str) -> bool:
        """
        Ensure a point is counted in all relevant systems
        
        Args:
            user_id: User identifier
            point_type: Type of point
            points: Points to add
            source: Source system
            
        Returns:
            True if successfully connected
        """
        try:
            # Add to unified counter
            if self.unified_counter:
                all_points = self.unified_counter.get_all_points(user_id, force_refresh=True)
                if point_type in all_points:
                    all_points[point_type] = all_points.get(point_type, 0) + points
                else:
                    all_points[point_type] = points
            
            # Save to database
            if unified_points_db:
                unified_points_db.ensure_point_connection(user_id, point_type, points, source)
            
            return True
        except Exception as e:
            print(f"[PointConnectionSystem] Error ensuring point counting: {e}")
            return False
    
    def get_all_connected_points(self, user_id: str) -> Dict[str, Any]:
        """
        Get all connected points for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with all connected points
        """
        # Connect all points
        connection_result = self.connect_all_points(user_id)
        
        # Also get from unified counter if available
        if self.unified_counter:
            unified_points = self.unified_counter.get_all_points(user_id)
            connection_result['unified_points'] = unified_points
        
        # Get from database
        if unified_points_db:
            db_points = unified_points_db.load_user_points(user_id)
            connection_result['database_points'] = db_points
        
        return connection_result
    
    def verify_all_points_connected(self, user_id: str) -> Dict[str, Any]:
        """
        Verify that all points are properly connected
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with verification results
        """
        verification = {
            'user_id': user_id,
            'systems_checked': len(self.connection_map),
            'systems_connected': 0,
            'systems_failed': 0,
            'total_points_found': 0,
            'points_by_system': {},
            'missing_connections': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for system_name, system_info in self.connection_map.items():
            try:
                connection_result = self.connect_all_points(user_id)
                system_status = connection_result['connection_status'].get(system_name, {})
                
                if system_status.get('connected', False):
                    verification['systems_connected'] += 1
                    points_found = system_status.get('points_found', 0)
                    verification['total_points_found'] += points_found
                    verification['points_by_system'][system_name] = points_found
                else:
                    verification['systems_failed'] += 1
                    verification['missing_connections'].append({
                        'system': system_name,
                        'error': system_status.get('error', 'Unknown error')
                    })
            except Exception as e:
                verification['systems_failed'] += 1
                verification['missing_connections'].append({
                    'system': system_name,
                    'error': str(e)
                })
        
        verification['connection_rate'] = (verification['systems_connected'] / verification['systems_checked'] * 100) if verification['systems_checked'] > 0 else 0
        
        return verification


# Global instance
point_connection = PointConnectionSystem()

