"""
Shop Point Counter Service
Tracks and displays shop points for all 178 systems
"""
from typing import Dict, Any, List
from datetime import datetime

class ShopPointCounter:
    """
    Shop point counter for all 178 systems
    Integrates with shop system and displays point balances
    """
    
    def __init__(self):
        """Initialize shop point counter"""
        pass
    
    def get_shop_points_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Get shop points balance for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Shop points balance and available systems
        """
        try:
            from backend.services.unified_point_counter import unified_point_counter
            from backend.services.shop_v2_system import shop_v2
            
            # Get all points
            all_points = unified_point_counter.get_all_points(user_id)
            
            # Get shop-specific points
            shop_points = all_points.get('shop_points', 0)
            
            # Get available items (if shop system available)
            available_items = []
            if shop_v2:
                try:
                    items = shop_v2.get_all_items()
                    available_items = items.get('items', [])[:10]  # Limit to 10
                except:
                    pass
            
            # Calculate total spendable points
            total_spendable = shop_points
            
            return {
                'success': True,
                'user_id': user_id,
                'shop_points': shop_points,
                'total_spendable': total_spendable,
                'available_items': available_items,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'shop_points': 0
            }
    
    def can_afford_item(self, user_id: str, item_id: str, item_cost: int) -> bool:
        """Check if user can afford an item"""
        balance = self.get_shop_points_balance(user_id)
        return balance.get('shop_points', 0) >= item_cost
    
    def get_point_systems_for_shop(self, user_id: str) -> Dict[str, Any]:
        """Get all point systems that can be used in shop"""
        try:
            from backend.services.unified_point_counter import unified_point_counter
            
            all_points = unified_point_counter.get_all_points(user_id)
            
            # Filter point systems that can be used in shop
            shop_eligible = {}
            for key, value in all_points.items():
                if key.endswith('_points') and isinstance(value, (int, float)) and value > 0:
                    system_id = key.replace('_points', '')
                    shop_eligible[system_id] = {
                        'points': value,
                        'system_id': system_id,
                        'convertible': True  # Can be converted to shop points
                    }
            
            return {
                'success': True,
                'eligible_systems': shop_eligible,
                'total_systems': len(shop_eligible)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'eligible_systems': {}
            }


# Global instance
shop_point_counter = ShopPointCounter()

