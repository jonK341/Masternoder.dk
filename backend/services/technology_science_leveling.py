"""
Technology & Science Leveling System
Maxout levels with +5% daily increase or DeathTeleport
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random

class TechnologyScienceLeveling:
    """Technology and Science Leveling System"""
    
    def __init__(self):
        self.user_levels = defaultdict(lambda: {
            'technology_level': 1,
            'science_level': 1,
            'max_technology': 100,
            'max_science': 100,
            'daily_increase': 0.05,  # 5% daily
            'last_update': None,
            'death_teleport_used': False
        })
        self.daily_increases = defaultdict(list)  # {user_id: [increase_history]}
        self.death_teleports = defaultdict(list)  # {user_id: [teleport_data]}
    
    def get_user_levels(self, user_id: str) -> Dict[str, Any]:
        """Get user's technology and science levels"""
        user_data = self.user_levels[user_id]
        
        # Check if daily increase should be applied
        if user_data['last_update']:
            last_update = datetime.fromisoformat(user_data['last_update'])
            if (datetime.utcnow() - last_update).days >= 1:
                self._apply_daily_increase(user_id)
        
        return {
            'success': True,
            'technology_level': user_data['technology_level'],
            'science_level': user_data['science_level'],
            'max_technology': user_data['max_technology'],
            'max_science': user_data['max_science'],
            'technology_progress': (user_data['technology_level'] / user_data['max_technology']) * 100,
            'science_progress': (user_data['science_level'] / user_data['max_science']) * 100,
            'is_maxed_technology': user_data['technology_level'] >= user_data['max_technology'],
            'is_maxed_science': user_data['science_level'] >= user_data['max_science'],
            'daily_increase': user_data['daily_increase'],
            'death_teleport_available': not user_data['death_teleport_used']
        }
    
    def _apply_daily_increase(self, user_id: str) -> None:
        """Apply daily 5% increase"""
        user_data = self.user_levels[user_id]
        
        # Increase technology
        if user_data['technology_level'] < user_data['max_technology']:
            increase = user_data['technology_level'] * user_data['daily_increase']
            user_data['technology_level'] = min(
                user_data['technology_level'] + increase,
                user_data['max_technology']
            )
        
        # Increase science
        if user_data['science_level'] < user_data['max_science']:
            increase = user_data['science_level'] * user_data['daily_increase']
            user_data['science_level'] = min(
                user_data['science_level'] + increase,
                user_data['max_science']
            )
        
        user_data['last_update'] = datetime.utcnow().isoformat()
        
        # Record increase
        self.daily_increases[user_id].append({
            'date': datetime.utcnow().isoformat(),
            'technology_increase': increase if user_data['technology_level'] < user_data['max_technology'] else 0,
            'science_increase': increase if user_data['science_level'] < user_data['max_science'] else 0
        })
    
    def use_death_teleport(self, user_id: str) -> Dict[str, Any]:
        """Use DeathTeleport to maxout levels instantly"""
        user_data = self.user_levels[user_id]
        
        if user_data['death_teleport_used']:
            return {
                'success': False,
                'error': 'DeathTeleport already used'
            }
        
        # Maxout both levels
        user_data['technology_level'] = user_data['max_technology']
        user_data['science_level'] = user_data['max_science']
        user_data['death_teleport_used'] = True
        user_data['last_update'] = datetime.utcnow().isoformat()
        
        # Record teleport
        teleport_data = {
            'teleport_id': f"death_teleport_{datetime.utcnow().timestamp()}",
            'user_id': user_id,
            'used_at': datetime.utcnow().isoformat(),
            'technology_before': user_data['technology_level'],
            'science_before': user_data['science_level'],
            'technology_after': user_data['max_technology'],
            'science_after': user_data['max_science']
        }
        self.death_teleports[user_id].append(teleport_data)
        
        return {
            'success': True,
            'teleport': teleport_data,
            'technology_level': user_data['technology_level'],
            'science_level': user_data['science_level']
        }
    
    def increase_levels(self, user_id: str, technology_amount: float = 0, science_amount: float = 0) -> Dict[str, Any]:
        """Manually increase levels"""
        user_data = self.user_levels[user_id]
        
        if technology_amount > 0:
            user_data['technology_level'] = min(
                user_data['technology_level'] + technology_amount,
                user_data['max_technology']
            )
        
        if science_amount > 0:
            user_data['science_level'] = min(
                user_data['science_level'] + science_amount,
                user_data['max_science']
            )
        
        return {
            'success': True,
            'technology_level': user_data['technology_level'],
            'science_level': user_data['science_level']
        }


# Global instance
technology_science_leveling = TechnologyScienceLeveling()

