"""
System Aggregator
Aggregates data from all systems and provides unified access
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class SystemAggregator:
    """
    Aggregates data from all systems and provides unified access
    for frontend integration and monitoring.
    """
    
    def __init__(self):
        self.systems = {}
        self.aggregated_data = {}
        self.last_update = {}
        
    def register_system(self, system_name: str, system_instance: Any):
        """Register a system with the aggregator"""
        self.systems[system_name] = system_instance
        logger.info(f"Registered system: {system_name}")
    
    def get_all_systems_data(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated data from all registered systems"""
        aggregated = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'systems': {},
            'summary': {
                'total_points': 0,
                'total_level': 0,
                'total_achievements': 0,
                'total_rewards': 0,
            }
        }
        
        # Aggregate from each system
        for system_name, system_instance in self.systems.items():
            try:
                system_data = self._get_system_data(system_instance, user_id, system_name)
                if system_data:
                    aggregated['systems'][system_name] = system_data
                    
                    # Update summary
                    if 'points' in system_data:
                        aggregated['summary']['total_points'] += system_data.get('points', 0)
                    if 'level' in system_data:
                        aggregated['summary']['total_level'] = max(
                            aggregated['summary']['total_level'],
                            system_data.get('level', 0)
                        )
                    if 'achievements' in system_data:
                        aggregated['summary']['total_achievements'] += len(
                            system_data.get('achievements', [])
                        )
                    if 'rewards' in system_data:
                        aggregated['summary']['total_rewards'] += len(
                            system_data.get('rewards', [])
                        )
            except Exception as e:
                logger.error(f"Error aggregating {system_name}: {e}")
                aggregated['systems'][system_name] = {'error': str(e)}
        
        self.aggregated_data[user_id] = aggregated
        self.last_update[user_id] = datetime.now()
        
        return aggregated
    
    def _get_system_data(self, system_instance: Any, user_id: str, system_name: str) -> Optional[Dict[str, Any]]:
        """Get data from a system instance"""
        try:
            # Try common method names
            methods = [
                'get_user_data',
                'get_data',
                'get_user_points',
                'get_user_stats',
                'get_user_profile',
                'get_user_info',
            ]
            
            for method_name in methods:
                if hasattr(system_instance, method_name):
                    method = getattr(system_instance, method_name)
                    data = method(user_id)
                    if data:
                        return {
                            'system': system_name,
                            'data': data,
                            'method': method_name
                        }
            
            # If no standard method, return basic info
            return {
                'system': system_name,
                'available': True,
                'methods': [m for m in dir(system_instance) if not m.startswith('_')]
            }
        
        except Exception as e:
            logger.error(f"Error getting data from {system_name}: {e}")
            return None
    
    def get_unified_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get data formatted for unified dashboard"""
        all_data = self.get_all_systems_data(user_id)
        
        dashboard_data = {
            'success': True,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'points': {
                'total': all_data['summary']['total_points'],
                'by_system': {}
            },
            'level': all_data['summary']['total_level'],
            'achievements': all_data['summary']['total_achievements'],
            'rewards': all_data['summary']['total_rewards'],
            'systems': {}
        }
        
        # Extract point data by system
        for system_name, system_data in all_data['systems'].items():
            if 'data' in system_data and isinstance(system_data['data'], dict):
                if 'points' in system_data['data']:
                    dashboard_data['points']['by_system'][system_name] = system_data['data']['points']
                if 'total_points' in system_data['data']:
                    dashboard_data['points']['by_system'][system_name] = system_data['data']['total_points']
        
        # Add system-specific data
        dashboard_data['systems'] = all_data['systems']
        
        return dashboard_data
    
    def get_leaderboard_data(self, system_id: str = None, limit: int = 100) -> Dict[str, Any]:
        """Get aggregated leaderboard data"""
        try:
            # Try to get from leaderboard system
            from backend.services.systems_leaderboard import systems_leaderboard
            if systems_leaderboard:
                return systems_leaderboard.get_leaderboard(system_id=system_id, limit=limit)
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
        
        return {
            'success': False,
            'error': 'Leaderboard system not available',
            'entries': []
        }
    
    def get_battle_data(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated battle data"""
        battle_data = {
            'user_id': user_id,
            'battles': [],
            'stats': {},
            'history': []
        }
        
        try:
            # Try battle system
            from backend.services.battle_system import battle_system
            if battle_system:
                if hasattr(battle_system, 'get_user_battles'):
                    battle_data['battles'] = battle_system.get_user_battles(user_id)
                if hasattr(battle_system, 'get_user_stats'):
                    battle_data['stats'] = battle_system.get_user_stats(user_id)
        except Exception as e:
            logger.error(f"Error getting battle data: {e}")
        
        return battle_data
    
    def get_shop_data(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated shop data"""
        shop_data = {
            'user_id': user_id,
            'items': [],
            'purchases': [],
            'balance': 0
        }
        
        try:
            # Try shop systems
            from backend.services.shop_v2_enhanced import shop_v2
            if shop_v2:
                if hasattr(shop_v2, 'get_available_items'):
                    shop_data['items'] = shop_v2.get_available_items()
                if hasattr(shop_v2, 'get_user_purchases'):
                    shop_data['purchases'] = shop_v2.get_user_purchases(user_id)
        except Exception as e:
            logger.error(f"Error getting shop data: {e}")
        
        return shop_data
    
    def get_quest_data(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated quest data"""
        quest_data = {
            'user_id': user_id,
            'active_quests': [],
            'completed_quests': [],
            'rewards': []
        }
        
        try:
            from backend.services.quest_system import quest_system
            if quest_system:
                if hasattr(quest_system, 'get_active_quests'):
                    quest_data['active_quests'] = quest_system.get_active_quests(user_id)
                if hasattr(quest_system, 'get_completed_quests'):
                    quest_data['completed_quests'] = quest_system.get_completed_quests(user_id)
        except Exception as e:
            logger.error(f"Error getting quest data: {e}")
        
        return quest_data
    
    def get_all_frontend_data(self, user_id: str) -> Dict[str, Any]:
        """Get all data needed for frontend pages"""
        return {
            'success': True,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'dashboard': self.get_unified_dashboard_data(user_id),
            'leaderboard': self.get_leaderboard_data(),
            'battle': self.get_battle_data(user_id),
            'shop': self.get_shop_data(user_id),
            'quest': self.get_quest_data(user_id),
            'points': self.get_all_systems_data(user_id)['summary']
        }


# Global instance
system_aggregator = SystemAggregator()

# Auto-register common systems
try:
    from backend.services.unified_point_counter import unified_point_counter
    if unified_point_counter:
        system_aggregator.register_system('unified_point_counter', unified_point_counter)
except ImportError:
    pass

try:
    from backend.services.agent_manager import agent_manager
    if agent_manager:
        system_aggregator.register_system('agent_manager', agent_manager)
except ImportError:
    pass

try:
    from backend.services.rewards_system_v2 import rewards_system_v2
    if rewards_system_v2:
        system_aggregator.register_system('rewards_system_v2', rewards_system_v2)
except ImportError:
    pass
