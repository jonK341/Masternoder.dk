"""
Unified Point Connector
Connects all point systems together
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.unified_points_database import unified_points_db
except ImportError:
    unified_point_counter = None
    unified_points_db = None

class UnifiedPointConnector:
    """Connects all point systems"""
    
    def __init__(self):
        self.connections = {}  # {user_id: connection_data}
    
    def connect_all_systems(self, user_id: str) -> Dict[str, Any]:
        """Connect all point systems for a user"""
        try:
            # Get points from unified counter
            all_points = {}
            if unified_point_counter:
                all_points = unified_point_counter.get_all_points(user_id)
            
            # Store connection
            self.connections[user_id] = {
                'user_id': user_id,
                'connected_systems': list(all_points.keys()) if all_points else [],
                'connected_at': datetime.utcnow().isoformat(),
                'points': all_points
            }
            
            return {
                'success': True,
                'user_id': user_id,
                'connected_systems': len(self.connections[user_id]['connected_systems']),
                'message': 'All point systems connected'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_unified_points(self, user_id: str) -> Dict[str, Any]:
        """Get unified points for user"""
        try:
            if unified_point_counter:
                points = unified_point_counter.get_all_points(user_id)
                return {
                    'success': True,
                    'user_id': user_id,
                    'points': points
                }
            else:
                return {
                    'success': False,
                    'error': 'Unified point counter not available'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

unified_point_connector = UnifiedPointConnector()
