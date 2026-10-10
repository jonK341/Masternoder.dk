"""
V3 Monetization Integration
Integrates monetization system with Shop v3, Battle v3, and VidGenerator v3
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

try:
    from backend.services.monetization_system import monetization_system
    from backend.services.shop_v3_ultimate import shop_v3_ultimate
    from backend.services.battle_v3_ultimate import battle_v3_ultimate
    from backend.services.vidgenerator_v3_ultimate import vidgenerator_v3_ultimate
except ImportError:
    monetization_system = None
    shop_v3_ultimate = None
    battle_v3_ultimate = None
    vidgenerator_v3_ultimate = None


class V3MonetizationIntegration:
    """Integrates monetization with all V3 systems"""
    
    def __init__(self):
        self.integrated_purchases = defaultdict(list)  # {user_id: [purchases]}
        self.v3_revenue = defaultdict(float)  # {system: revenue}
        self.unlock_tracking = defaultdict(dict)  # {user_id: {unlock: status}}
    
    def integrate_shop_v3_purchase(self, user_id: str, item_id: str, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate shop v3 purchase with monetization"""
        if not monetization_system or not shop_v3_ultimate:
            return {'success': False, 'error': 'Systems not available'}
        
        # Check if item unlocks monetization features
        item = shop_v3_ultimate.items.get(item_id) or shop_v3_ultimate.artifacts.get(item_id)
        
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        # Record monetization purchase if applicable
        unlocks = item.get('effect', {}).get('unlocks', [])
        if unlocks:
            for unlock in unlocks if isinstance(unlocks, list) else [unlocks]:
                if unlock in ['death_portal', 'production_10x', 'teleport_skillset']:
                    # Map to monetization stream
                    stream_id = f"{unlock}_unlock"
                    if stream_id in monetization_system.INCOME_STREAMS:
                        monetization_system.record_purchase(
                            user_id=user_id,
                            stream_id=stream_id,
                            amount=monetization_system.INCOME_STREAMS[stream_id]['price'],
                            currency='USD'
                        )
                        self.v3_revenue['shop_v3'] += monetization_system.INCOME_STREAMS[stream_id]['price']
                        
                        # Track unlock
                        if user_id not in self.unlock_tracking:
                            self.unlock_tracking[user_id] = {}
                        self.unlock_tracking[user_id][unlock] = {
                            'unlocked_at': datetime.utcnow().isoformat(),
                            'unlocked_via': 'shop_v3',
                            'item_id': item_id
                        }
        
        return {
            'success': True,
            'item': item,
            'unlocks': unlocks if unlocks else [],
            'monetization_tracked': bool(unlocks)
        }
    
    def integrate_battle_v3_purchase(self, user_id: str, battle_type: str, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate battle v3 with monetization"""
        if not monetization_system or not battle_v3_ultimate:
            return {'success': False, 'error': 'Systems not available'}
        
        # Premium battle types may require monetization
        premium_battles = ['death_portal_battle', 'production_10x_battle']
        
        if battle_type in premium_battles:
            # Check if user has unlock
            has_unlock = self.unlock_tracking.get(user_id, {}).get(
                'death_portal' if 'death_portal' in battle_type else 'production_10x',
                {}
            )
            
            if not has_unlock:
                # Offer purchase
                unlock_type = 'death_portal' if 'death_portal' in battle_type else 'production_10x'
                stream_id = f"{unlock_type}_unlock"
                
                return {
                    'success': False,
                    'requires_unlock': True,
                    'unlock_type': unlock_type,
                    'stream_id': stream_id,
                    'price': monetization_system.INCOME_STREAMS.get(stream_id, {}).get('price', 0),
                    'message': f'Unlock {unlock_type} to access this battle type'
                }
        
        return {'success': True, 'battle_type': battle_type}
    
    def integrate_vidgenerator_v3_purchase(self, user_id: str, quality_preset: str, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate vidgenerator v3 with monetization"""
        if not monetization_system or not vidgenerator_v3_ultimate:
            return {'success': False, 'error': 'Systems not available'}
        
        # Premium quality presets
        premium_qualities = ['death_portal', 'production_10x']
        
        if quality_preset in premium_qualities:
            # Check if user has unlock
            unlock_type = 'death_portal' if 'death_portal' in quality_preset else 'production_10x'
            has_unlock = self.unlock_tracking.get(user_id, {}).get(unlock_type, {})
            
            if not has_unlock:
                # Offer purchase
                stream_id = f"{unlock_type}_unlock"
                
                return {
                    'success': False,
                    'requires_unlock': True,
                    'unlock_type': unlock_type,
                    'stream_id': stream_id,
                    'price': monetization_system.INCOME_STREAMS.get(stream_id, {}).get('price', 0),
                    'message': f'Unlock {unlock_type} to use this quality preset'
                }
        
        # Track video generation credits if applicable
        if 'video_generation_credits' in purchase_data:
            monetization_system.record_purchase(
                user_id=user_id,
                stream_id='video_generation_credits',
                amount=monetization_system.INCOME_STREAMS['video_generation_credits']['price'],
                currency='USD'
            )
            self.v3_revenue['vidgenerator_v3'] += monetization_system.INCOME_STREAMS['video_generation_credits']['price']
        
        return {'success': True, 'quality_preset': quality_preset}
    
    def get_v3_monetization_stats(self) -> Dict[str, Any]:
        """Get monetization stats for V3 systems"""
        return {
            'success': True,
            'v3_revenue': dict(self.v3_revenue),
            'total_v3_revenue': sum(self.v3_revenue.values()),
            'unlocks_tracked': len(self.unlock_tracking),
            'integrated_systems': {
                'shop_v3': shop_v3_ultimate is not None,
                'battle_v3': battle_v3_ultimate is not None,
                'vidgenerator_v3': vidgenerator_v3_ultimate is not None,
                'monetization': monetization_system is not None
            }
        }
    
    def get_user_v3_unlocks(self, user_id: str) -> Dict[str, Any]:
        """Get user's V3 unlocks"""
        unlocks = self.unlock_tracking.get(user_id, {})
        
        return {
            'success': True,
            'user_id': user_id,
            'unlocks': unlocks,
            'has_death_portal': 'death_portal' in unlocks,
            'has_production_10x': 'production_10x' in unlocks,
            'has_teleport_skillset': 'teleport_skillset' in unlocks
        }


# Global instance
v3_monetization_integration = V3MonetizationIntegration()

