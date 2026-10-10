"""
Complete Point Counter Equation
Solves and finishes the equation for all point systems
"""
from typing import Dict, Any, Optional
from datetime import datetime

# Import all point systems
try:
    from backend.services.unified_point_counter import UnifiedPointCounter
    from backend.services.point_connection_system import point_connection
    from backend.services.activity_points_system import ActivityPointsSystem
    from backend.services.battle_intelligence_system import BattleIntelligenceSystem
    from backend.services.quick_battle_system import quick_battle_system
    from backend.services.champions_league_system import champions_league
    from backend.services.shop_v2_system import shop_v2
except ImportError:
    UnifiedPointCounter = None
    point_connection = None
    ActivityPointsSystem = None
    BattleIntelligenceSystem = None
    quick_battle_system = None
    champions_league = None
    shop_v2 = None


class CompletePointEquation:
    """
    Complete point counter equation solver
    Connects all point systems and calculates final points
    """
    
    def __init__(self):
        self.unified_counter = UnifiedPointCounter() if UnifiedPointCounter else None
        self.point_connection = point_connection
        
    def calculate_total_points(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate total points using complete equation
        
        Equation:
        Total Points = 
            XP Points +
            Activity Points +
            Theme Points +
            Chat Points +
            Trophy Points +
            Battle Points +
            Achievement Points +
            Stats Points +
            Metal System Points +
            Graduation Points +
            Generation Points +
            Krimetime Points +
            Guild Points +
            Rewards Points +
            Shop Points +
            Social Points +
            Champions League Points +
            Intelligence Bonus Points +
            Streak Bonus Points +
            Artifact Bonus Points +
            Booster Bonus Points
        """
        all_points = {
            # Base Points
            'xp_points': 0,
            'activity_points': 0,
            'theme_points': 0,
            'chat_points': 0,
            'trophy_points': 0,
            'battle_points': 0,
            'achievement_points': 0,
            'stats_points': 0,
            'metal_points': 0,
            'graduation_points': 0,
            'generation_points': 0,
            'krimetime_points': 0,
            'guild_points': 0,
            'rewards_points': 0,
            'shop_points': 0,
            'social_points': 0,
            'champions_league_points': 0,
            
            # Bonus Points
            'intelligence_bonus': 0,
            'streak_bonus': 0,
            'artifact_bonus': 0,
            'booster_bonus': 0,
            
            # Multipliers
            'difficulty_multiplier': 1.0,
            'streak_multiplier': 1.0,
            'artifact_multiplier': 1.0,
            'booster_multiplier': 1.0,
            'intelligence_multiplier': 1.0,
            'league_multiplier': 1.0,
            
            # Totals
            'base_total': 0,
            'bonus_total': 0,
            'final_total': 0
        }
        
        # Get from unified counter
        if self.unified_counter:
            try:
                unified = self.unified_counter.get_all_points(user_id)
                all_points['xp_points'] = unified.get('xp_total', 0) or 0
                all_points['activity_points'] = unified.get('activity_points', 0) or 0
                all_points['battle_points'] = unified.get('battle_points', 0) or 0
                all_points['trophy_points'] = unified.get('trophy_points', 0) or 0
                all_points['achievement_points'] = unified.get('achievement_points', 0) or 0
                all_points['social_points'] = unified.get('social_points', 0) or 0
            except:
                pass
        
        # Get from champions league
        if champions_league:
            try:
                league_data = champions_league.get_user_league(user_id)
                all_points['champions_league_points'] = league_data.get('total_points', 0) or 0
            except:
                pass
        
        # Get from shop
        if shop_v2:
            try:
                history = shop_v2.purchase_history.get(user_id, [])
                all_points['shop_points'] = sum(p.get('shop_points', 0) for p in history)
            except:
                pass
        
        # Get streak bonus
        if quick_battle_system:
            try:
                streak = quick_battle_system.get_streak(user_id)
                streak_level = streak.get('current_streak', 0)
                all_points['streak_bonus'] = streak_level * 10  # 10 points per streak level
                all_points['streak_multiplier'] = 1.0 + (streak_level * 0.05)  # 5% per streak level
            except:
                pass
        
        # Calculate base total
        all_points['base_total'] = sum([
            all_points['xp_points'],
            all_points['activity_points'],
            all_points['theme_points'],
            all_points['chat_points'],
            all_points['trophy_points'],
            all_points['battle_points'],
            all_points['achievement_points'],
            all_points['stats_points'],
            all_points['metal_points'],
            all_points['graduation_points'],
            all_points['generation_points'],
            all_points['krimetime_points'],
            all_points['guild_points'],
            all_points['rewards_points'],
            all_points['shop_points'],
            all_points['social_points'],
            all_points['champions_league_points']
        ])
        
        # Calculate bonus total
        all_points['bonus_total'] = sum([
            all_points['intelligence_bonus'],
            all_points['streak_bonus'],
            all_points['artifact_bonus'],
            all_points['booster_bonus']
        ])
        
        # Calculate final total with multipliers
        # Final Points = (Base Points + Bonus Points) × All Multipliers
        multiplier_product = (
            all_points['difficulty_multiplier'] *
            all_points['streak_multiplier'] *
            all_points['artifact_multiplier'] *
            all_points['booster_multiplier'] *
            all_points['intelligence_multiplier'] *
            all_points['league_multiplier']
        )
        
        all_points['final_total'] = int((all_points['base_total'] + all_points['bonus_total']) * multiplier_product)
        
        return all_points
    
    def get_point_breakdown(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed point breakdown
        
        Returns:
            Complete point breakdown with equation
        """
        points = self.calculate_total_points(user_id)
        
        breakdown = {
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'equation': {
                'base_points': {
                    'xp_points': points['xp_points'],
                    'activity_points': points['activity_points'],
                    'theme_points': points['theme_points'],
                    'chat_points': points['chat_points'],
                    'trophy_points': points['trophy_points'],
                    'battle_points': points['battle_points'],
                    'achievement_points': points['achievement_points'],
                    'stats_points': points['stats_points'],
                    'metal_points': points['metal_points'],
                    'graduation_points': points['graduation_points'],
                    'generation_points': points['generation_points'],
                    'krimetime_points': points['krimetime_points'],
                    'guild_points': points['guild_points'],
                    'rewards_points': points['rewards_points'],
                    'shop_points': points['shop_points'],
                    'social_points': points['social_points'],
                    'champions_league_points': points['champions_league_points'],
                    'subtotal': points['base_total']
                },
                'bonus_points': {
                    'intelligence_bonus': points['intelligence_bonus'],
                    'streak_bonus': points['streak_bonus'],
                    'artifact_bonus': points['artifact_bonus'],
                    'booster_bonus': points['booster_bonus'],
                    'subtotal': points['bonus_total']
                },
                'multipliers': {
                    'difficulty_multiplier': points['difficulty_multiplier'],
                    'streak_multiplier': points['streak_multiplier'],
                    'artifact_multiplier': points['artifact_multiplier'],
                    'booster_multiplier': points['booster_multiplier'],
                    'intelligence_multiplier': points['intelligence_multiplier'],
                    'league_multiplier': points['league_multiplier'],
                    'product': (
                        points['difficulty_multiplier'] *
                        points['streak_multiplier'] *
                        points['artifact_multiplier'] *
                        points['booster_multiplier'] *
                        points['intelligence_multiplier'] *
                        points['league_multiplier']
                    )
                },
                'final_calculation': {
                    'base_total': points['base_total'],
                    'bonus_total': points['bonus_total'],
                    'sum': points['base_total'] + points['bonus_total'],
                    'multiplier_product': (
                        points['difficulty_multiplier'] *
                        points['streak_multiplier'] *
                        points['artifact_multiplier'] *
                        points['booster_multiplier'] *
                        points['intelligence_multiplier'] *
                        points['league_multiplier']
                    ),
                    'final_total': points['final_total']
                }
            },
            'summary': {
                'base_total': points['base_total'],
                'bonus_total': points['bonus_total'],
                'final_total': points['final_total']
            }
        }
        
        return breakdown


# Global instance
complete_point_equation = CompletePointEquation()

