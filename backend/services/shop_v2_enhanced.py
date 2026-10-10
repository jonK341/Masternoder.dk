"""
Shop V2 Enhanced System
Enhanced UI/UX with category browsing, search, filters, wishlist, recommendations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class ShopV2Enhanced:
    """Enhanced shop system with advanced features"""
    
    def __init__(self):
        self.items = {
            'templates': [
                {'id': 'template_gold', 'name': 'Gold Template', 'price': 1000, 'category': 'templates', 'rarity': 'epic'},
                {'id': 'template_cyberpunk', 'name': 'Cyberpunk Template', 'price': 1500, 'category': 'templates', 'rarity': 'legendary'},
                {'id': 'template_royal', 'name': 'Royal Template', 'price': 2000, 'category': 'templates', 'rarity': 'mythic'},
            ],
            'trophies': [
                {'id': 'trophy_win', 'name': 'Win Trophy', 'price': 500, 'category': 'trophies', 'rarity': 'rare'},
                {'id': 'trophy_victory', 'name': 'Victory Trophy', 'price': 1000, 'category': 'trophies', 'rarity': 'epic'},
                {'id': 'trophy_killer', 'name': 'Killer Trophy', 'price': 2000, 'category': 'trophies', 'rarity': 'legendary'},
                {'id': 'trophy_familie_shield', 'name': 'Familie Shield Trophy', 'price': 1500, 'category': 'trophies', 'rarity': 'epic'},
            ],
            'agent_upgrades': [
                {'id': 'agent_power_boost', 'name': 'Power Boost Ability', 'price': 800, 'category': 'agent_upgrades', 'rarity': 'rare'},
                {'id': 'agent_energy_flow', 'name': 'Energy Flow Ability', 'price': 1200, 'category': 'agent_upgrades', 'rarity': 'epic'},
                {'id': 'agent_synergy_link', 'name': 'Synergy Link Ability', 'price': 1500, 'category': 'agent_upgrades', 'rarity': 'epic'},
            ],
            'skill_enhancements': [
                {'id': 'skill_multiplier_1.5x', 'name': '1.5x Skill Multiplier', 'price': 2000, 'category': 'skills', 'rarity': 'epic'},
                {'id': 'skill_multiplier_2x', 'name': '2x Skill Multiplier', 'price': 5000, 'category': 'skills', 'rarity': 'legendary'},
                {'id': 'skill_multiplier_2.5x', 'name': '2.5x Skill Multiplier', 'price': 10000, 'category': 'skills', 'rarity': 'mythic'},
            ],
            'bundles': [
                {'id': 'bundle_starter', 'name': 'Starter Bundle', 'price': 5000, 'category': 'bundles', 'items': ['template_gold', 'trophy_win'], 'discount': 0.2},
                {'id': 'bundle_pro', 'name': 'Pro Bundle', 'price': 15000, 'category': 'bundles', 'items': ['template_cyberpunk', 'trophy_victory', 'agent_power_boost'], 'discount': 0.3},
            ]
        }
        
        self.user_wishlists = {}  # user_id -> [item_ids]
        self.purchase_history = {}  # user_id -> [purchases]
        self.recommendations = {}  # user_id -> [recommended_items]
    
    def get_all_items(self, category: str = None, search: str = None, 
                     filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get all shop items with filtering"""
        all_items = []
        
        for category_items in self.items.values():
            all_items.extend(category_items)
        
        # Category filter
        if category and category != 'all':
            all_items = [item for item in all_items if item.get('category') == category]
        
        # Search filter
        if search:
            search_lower = search.lower()
            all_items = [
                item for item in all_items
                if search_lower in item.get('name', '').lower() or
                   search_lower in item.get('id', '').lower()
            ]
        
        # Additional filters
        if filters:
            if 'rarity' in filters:
                all_items = [item for item in all_items if item.get('rarity') == filters['rarity']]
            if 'max_price' in filters:
                all_items = [item for item in all_items if item.get('price', 0) <= filters['max_price']]
            if 'min_price' in filters:
                all_items = [item for item in all_items if item.get('price', 0) >= filters['min_price']]
        
        return {
            'success': True,
            'items': all_items,
            'total': len(all_items),
            'categories': list(set(item.get('category') for item in all_items))
        }
    
    def add_to_wishlist(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Add item to wishlist"""
        if user_id not in self.user_wishlists:
            self.user_wishlists[user_id] = []
        
        if item_id not in self.user_wishlists[user_id]:
            self.user_wishlists[user_id].append(item_id)
        
        return {
            'success': True,
            'user_id': user_id,
            'item_id': item_id,
            'wishlist': self.user_wishlists[user_id]
        }
    
    def remove_from_wishlist(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Remove item from wishlist"""
        if user_id in self.user_wishlists and item_id in self.user_wishlists[user_id]:
            self.user_wishlists[user_id].remove(item_id)
        
        return {
            'success': True,
            'user_id': user_id,
            'item_id': item_id,
            'wishlist': self.user_wishlists.get(user_id, [])
        }
    
    def get_wishlist(self, user_id: str) -> Dict[str, Any]:
        """Get user wishlist"""
        wishlist_ids = self.user_wishlists.get(user_id, [])
        wishlist_items = []
        
        for category_items in self.items.values():
            for item in category_items:
                if item['id'] in wishlist_ids:
                    wishlist_items.append(item)
        
        return {
            'success': True,
            'user_id': user_id,
            'wishlist': wishlist_items,
            'total': len(wishlist_items)
        }
    
    def purchase_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Purchase an item"""
        # Find item
        item = None
        for category_items in self.items.values():
            for i in category_items:
                if i['id'] == item_id:
                    item = i
                    break
            if item:
                break
        
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        # Check user points
        try:
            from backend.services.unified_points_database import unified_points_db
            user_points = unified_points_db.get_user_points(user_id)
            total_points = sum(user_points.values()) if user_points else 0
            
            if total_points < item['price']:
                return {
                    'success': False,
                    'error': 'Insufficient points',
                    'required': item['price'],
                    'available': total_points
                }
            
            # Deduct points
            unified_points_db.add_points(
                user_id,
                'shop',
                -item['price'],
                source='shop_purchase'
            )
            
            # Record purchase
            if user_id not in self.purchase_history:
                self.purchase_history[user_id] = []
            
            purchase = {
                'timestamp': datetime.utcnow().isoformat(),
                'item_id': item_id,
                'item_name': item['name'],
                'price': item['price'],
                'category': item.get('category')
            }
            self.purchase_history[user_id].append(purchase)
            
            # Remove from wishlist if present
            if user_id in self.user_wishlists and item_id in self.user_wishlists[user_id]:
                self.user_wishlists[user_id].remove(item_id)
            
            return {
                'success': True,
                'user_id': user_id,
                'item': item,
                'purchase': purchase,
                'remaining_points': total_points - item['price']
            }
        except Exception as e:
            logger.error(f"Error purchasing item: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_purchase_history(self, user_id: str) -> Dict[str, Any]:
        """Get user purchase history"""
        history = self.purchase_history.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'history': history,
            'total_purchases': len(history),
            'total_spent': sum(p['price'] for p in history)
        }
    
    def get_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get personalized recommendations"""
        # Simple recommendation algorithm
        purchase_history = self.purchase_history.get(user_id, [])
        wishlist = self.user_wishlists.get(user_id, [])
        
        # Get categories from purchases
        purchased_categories = set(p.get('category') for p in purchase_history)
        
        # Recommend items from same categories or popular items
        recommendations = []
        for category_items in self.items.values():
            for item in category_items:
                if item['id'] not in wishlist:
                    score = 0
                    if item.get('category') in purchased_categories:
                        score += 2
                    if item.get('rarity') in ['epic', 'legendary']:
                        score += 1
                    recommendations.append({**item, 'recommendation_score': score})
        
        # Sort by score and return top 10
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return {
            'success': True,
            'user_id': user_id,
            'recommendations': recommendations[:10]
        }

shop_v2_enhanced = ShopV2Enhanced()
