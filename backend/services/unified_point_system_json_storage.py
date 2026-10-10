"""
Unified Point System JSON Storage
Enhanced point system that saves to JSON file on computer
Fast refresh with calculator integration
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os

try:
    from backend.services.unified_point_counter import UnifiedPointCounter
    from backend.services.point_calculator_hardcoded import PointCalculatorHardcoded
    from backend.services.unified_points_database import UnifiedPointsDatabase
except ImportError:
    UnifiedPointCounter = None
    PointCalculatorHardcoded = None
    UnifiedPointsDatabase = None


class UnifiedPointSystemJSONStorage:
    """
    Unified Point System with JSON Storage
    - Saves all points to JSON file on computer
    - Fast refresh with calculator integration
    - Connected to point counters on front page
    """
    
    def __init__(self, data_dir: str = 'data/unified_points'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.point_counter = UnifiedPointCounter() if UnifiedPointCounter else None
        self.calculator = PointCalculatorHardcoded() if PointCalculatorHardcoded else None
        self.db = UnifiedPointsDatabase() if UnifiedPointsDatabase else None
        
        self.cache = {}  # {user_id: {data: {...}, timestamp: ...}}
        self.cache_ttl = 5  # 5 seconds for fast refresh
    
    def get_all_points(self, user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get all points with fast refresh"""
        # Check cache
        if not force_refresh and user_id in self.cache:
            cached = self.cache[user_id]
            age = (datetime.utcnow() - datetime.fromisoformat(cached['timestamp'])).total_seconds()
            if age < self.cache_ttl:
                return cached['data']
        
        # Get from point counter
        points = {}
        if self.point_counter:
            points = self.point_counter.get_all_points(user_id, force_refresh=True)
        else:
            # Fallback: load from file
            points = self.load_from_json(user_id)
        
        # Process through calculator if available
        if self.calculator:
            try:
                # Convert points to calculator format
                calculator_data = self._convert_to_calculator_format(points)
                calculated = self.calculator.calculate_all_points(calculator_data)
                
                # Merge calculated points
                if calculated.get('success'):
                    points.update(calculated.get('final_points', {}))
            except Exception as e:
                print(f"[UnifiedPointSystemJSON] Error in calculator: {e}")
        
        # Cache result
        self.cache[user_id] = {
            'data': points,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to JSON file
        self.save_to_json(user_id, points)
        
        return points
    
    def save_to_json(self, user_id: str, points: Dict[str, Any]) -> bool:
        """Save points to JSON file on computer"""
        try:
            file_path = os.path.join(self.data_dir, f'{user_id}_points.json')
            data = {
                'user_id': user_id,
                'points': points,
                'last_updated': datetime.utcnow().isoformat(),
                'version': '2.0'
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[UnifiedPointSystemJSON] Error saving to JSON: {e}")
            return False
    
    def load_from_json(self, user_id: str) -> Dict[str, Any]:
        """Load points from JSON file"""
        try:
            file_path = os.path.join(self.data_dir, f'{user_id}_points.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('points', {})
            return {}
        except Exception as e:
            print(f"[UnifiedPointSystemJSON] Error loading from JSON: {e}")
            return {}
    
    def increment_point(self, user_id: str, point_type: str, amount: int = 1) -> Dict[str, Any]:
        """Increment a point type (fast refresh)"""
        # Get current points
        points = self.get_all_points(user_id, force_refresh=False)
        
        # Increment
        if point_type in points:
            points[point_type] = (points.get(point_type, 0) or 0) + amount
        else:
            points[point_type] = amount
        
        # Save immediately
        self.save_to_json(user_id, points)
        
        # Clear cache for fast refresh
        if user_id in self.cache:
            del self.cache[user_id]
        
        return {
            'success': True,
            'point_type': point_type,
            'new_value': points.get(point_type, 0),
            'points': points
        }
    
    def _convert_to_calculator_format(self, points: Dict[str, Any]) -> Dict[str, Any]:
        """Convert points to calculator input format"""
        return {
            'page_views': points.get('page_views', 0),
            'clicks': points.get('clicks', 0),
            'scrolls': points.get('scrolls', 0),
            'time_minutes': points.get('time_minutes', 0),
            'battles': points.get('battle_wins', 0),
            'battle_victories': points.get('battle_wins', 0),
            'battle_defeats': points.get('battle_losses', 0),
            'generations': points.get('generations', 0),
            'trophies_unlocked': points.get('trophies_collected', 0),
            'achievements_unlocked': points.get('achievements_earned', 0),
            'interactions': points.get('social_interactions', 0)
        }


# Global instance
unified_point_json_storage = UnifiedPointSystemJSONStorage()

