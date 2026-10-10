"""
Enhanced Click Activity System
Awards more points per click with multipliers and bonuses
"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EnhancedClickActivity:
    """Enhanced click activity tracking with increased point rewards"""
    
    def __init__(self):
        self.base_click_points = 5  # Increased from 1-2
        self.combo_multiplier = 0.10  # 10% per combo
        self.streak_multiplier = 0.05  # 5% per streak
        self.critical_chance = 0.05  # 5% critical hit chance
        self.critical_multiplier = 3.0  # 3x for critical hits
        
    def calculate_click_points(self, user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate enhanced points for a click"""
        metadata = metadata or {}
        
        # Base points (increased)
        base_points = self.base_click_points
        
        # Combo multiplier
        combo_count = metadata.get('combo', 0)
        combo_bonus = base_points * (combo_count * self.combo_multiplier)
        
        # Streak multiplier
        streak_count = metadata.get('streak', 0)
        streak_bonus = base_points * (streak_count * self.streak_multiplier)
        
        # Level bonus
        user_level = metadata.get('level', 1)
        level_bonus = base_points * (user_level * 0.005)  # 0.5% per level
        
        # Critical hit check
        import random
        is_critical = random.random() < self.critical_chance
        critical_bonus = base_points * (self.critical_multiplier - 1) if is_critical else 0
        
        # Total points
        total_points = int(
            base_points + 
            combo_bonus + 
            streak_bonus + 
            level_bonus + 
            critical_bonus
        )
        
        return {
            'base_points': base_points,
            'combo_bonus': int(combo_bonus),
            'streak_bonus': int(streak_bonus),
            'level_bonus': int(level_bonus),
            'critical_bonus': int(critical_bonus),
            'is_critical': is_critical,
            'total_points': total_points,
            'multiplier': total_points / base_points if base_points > 0 else 1.0
        }

enhanced_click_activity = EnhancedClickActivity()
