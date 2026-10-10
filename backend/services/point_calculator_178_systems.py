"""
Point Calculator - 178 Systems Enhanced
Includes Death Portal Teleport and 10x Production multipliers
All 178 point systems integrated
"""
from typing import Dict, Any
from datetime import datetime
import json
import os

# Load generated point values
POINT_VALUES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '178_systems_point_values.json')

class PointCalculator178Systems:
    """
    Enhanced calculator for all 178 point systems
    Includes Death Portal (10x) and Teleport Skillset multipliers
    """
    
    # Death Portal & Production Multipliers
    DEATH_PORTAL_MULTIPLIER = 10.0  # 10x production multiplier
    TELEPORT_SKILLSET_BONUS = 1.5   # Teleport skillset bonus
    PRODUCTION_10X_MULTIPLIER = 10.0  # 10x production multiplier
    
    def __init__(self):
        """Initialize calculator with all 178 systems"""
        self.point_values = self._load_point_values()
        self.death_portal_systems = self._get_death_portal_systems()
        self.production_10x_systems = self._get_production_10x_systems()
        self.teleport_skillset_systems = self._get_teleport_skillset_systems()
    
    def _load_point_values(self) -> Dict[str, int]:
        """Load point values from generated file"""
        try:
            if os.path.exists(POINT_VALUES_FILE):
                with open(POINT_VALUES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[PointCalculator178] Error loading point values: {e}", flush=True)
        
        # Fallback to default values
        return self._get_default_point_values()
    
    def _get_default_point_values(self) -> Dict[str, int]:
        """Get default point values if file not found"""
        return {
            'xp': 1,
            'activity': 1,
            'battle': 20,
            'generation': 100,
            'death_portal_teleport': 200,  # 10x base
            'production_10x': 1000,  # 10x base
        }
    
    def _get_death_portal_systems(self) -> list:
        """Get systems with Death Portal multiplier"""
        return [
            'xp', 'battle', 'pvp_battle', 'pve_battle',
            'death_portal_teleport', 'production_10x',
            'death_portal_mastery', 'death_portal_event'
        ]
    
    def _get_production_10x_systems(self) -> list:
        """Get systems with 10x Production multiplier"""
        return [
            'generation', 'watch_time', 'video_generation',
            'clip_generation', 'image_generation', 'audio_generation',
            'production_mastery', 'production_economy'
        ]
    
    def _get_teleport_skillset_systems(self) -> list:
        """Get systems with Teleport Skillset bonus"""
        return [
            'death_portal_teleport', 'skillset_mastery',
            'teleport_skillset', 'skill', 'skill_development',
            'teleport_trade'
        ]
    
    def calculate_all_178_systems(self, point_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all 178 point systems with multipliers
        
        Args:
            point_data: Dictionary with all point-related data
            
        Returns:
            Complete calculation with all 178 systems
        """
        # Initialize all base points
        base_points = self._initialize_all_base_points()
        
        # Calculate base points for each system
        for system_id, point_value in self.point_values.items():
            data_key = system_id.replace('_', '_')
            count = point_data.get(data_key, 0) or point_data.get(system_id, 0) or 0
            
            # Calculate base points
            base_points[f'{system_id}_points'] = count * point_value
        
        # Apply Death Portal multipliers (10x)
        for system_id in self.death_portal_systems:
            field_name = f'{system_id}_points'
            if field_name in base_points:
                base_points[field_name] = int(base_points[field_name] * self.DEATH_PORTAL_MULTIPLIER)
        
        # Apply 10x Production multipliers
        for system_id in self.production_10x_systems:
            field_name = f'{system_id}_points'
            if field_name in base_points:
                base_points[field_name] = int(base_points[field_name] * self.PRODUCTION_10X_MULTIPLIER)
        
        # Apply Teleport Skillset bonuses
        for system_id in self.teleport_skillset_systems:
            field_name = f'{system_id}_points'
            if field_name in base_points:
                base_points[field_name] = int(base_points[field_name] * self.TELEPORT_SKILLSET_BONUS)
        
        # Calculate totals
        base_total = sum([v for k, v in base_points.items() if isinstance(v, (int, float))])
        
        # Calculate bonuses
        bonus_points = self._calculate_bonuses(point_data, base_points)
        bonus_total = sum([v for k, v in bonus_points.items() if isinstance(v, (int, float))])
        
        # Calculate multipliers
        multipliers = self._calculate_multipliers(point_data)
        multiplier_product = self._calculate_multiplier_product(multipliers)
        
        # Final total
        final_total = int((base_total + bonus_total) * multiplier_product)
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'base_points': base_points,
            'bonus_points': bonus_points,
            'multipliers': multipliers,
            'totals': {
                'base_total': base_total,
                'bonus_total': bonus_total,
                'multiplier_product': multiplier_product,
                'final_total': final_total
            },
            'death_portal_active': point_data.get('death_portal_active', False),
            'production_10x_active': point_data.get('production_10x_active', False),
            'teleport_skillset_level': point_data.get('teleport_skillset_level', 0),
            'equation_breakdown': {
                'base_total': base_total,
                'bonus_total': bonus_total,
                'sum': base_total + bonus_total,
                'multiplier_product': multiplier_product,
                'final_total': final_total,
                'formula': 'Final = (Base + Bonus) × Multipliers × Death Portal × Production 10x'
            }
        }
    
    def _initialize_all_base_points(self) -> Dict[str, int]:
        """Initialize all 178 base point fields"""
        # This will be populated from generated config
        base_points = {}
        
        # Load from config if available
        config_file = os.path.join(os.path.dirname(__file__), '..', '..', '178_systems_config.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for system_id in config.get('systems', {}).keys():
                        base_points[f'{system_id}_points'] = 0
        except Exception as e:
            print(f"[PointCalculator178] Error loading config: {e}", flush=True)
        
        # Fallback: initialize common systems
        if not base_points:
            common_systems = [
                'xp', 'activity', 'theme', 'chat', 'trophy', 'battle', 'achievement',
                'stats', 'metal', 'graduation', 'generation', 'krimetime', 'guild',
                'rewards', 'shop', 'social', 'champions_league'
            ]
            for system_id in common_systems:
                base_points[f'{system_id}_points'] = 0
        
        return base_points
    
    def _calculate_bonuses(self, point_data: Dict[str, Any], base_points: Dict[str, int]) -> Dict[str, int]:
        """Calculate bonus points"""
        bonuses = {
            'intelligence_bonus': point_data.get('intelligence_score', 0) * 5,
            'streak_bonus': point_data.get('daily_streak', 0) * 10,
            'artifact_bonus': point_data.get('artifacts_collected', 0) * 25,
            'booster_bonus': 100 if point_data.get('booster_active', False) else 0,
            'death_portal_bonus': 1000 if point_data.get('death_portal_active', False) else 0,
            'production_10x_bonus': 5000 if point_data.get('production_10x_active', False) else 0,
            'teleport_skillset_bonus': point_data.get('teleport_skillset_level', 0) * 100,
        }
        return bonuses
    
    def _calculate_multipliers(self, point_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate all multipliers"""
        multipliers = {
            'difficulty_multiplier': self._get_difficulty_multiplier(point_data.get('difficulty', 'medium')),
            'streak_multiplier': 1.0 + (point_data.get('daily_streak', 0) * 0.01),
            'artifact_multiplier': 1.0 + (point_data.get('artifacts_collected', 0) * 0.02),
            'booster_multiplier': 1.5 if point_data.get('booster_active', False) else 1.0,
            'intelligence_multiplier': 1.0 + (point_data.get('intelligence_score', 0) * 0.005),
            'league_multiplier': 1.0 + (point_data.get('league_rank', 0) * 0.03),
            'death_portal_multiplier': self.DEATH_PORTAL_MULTIPLIER if point_data.get('death_portal_active', False) else 1.0,
            'production_10x_multiplier': self.PRODUCTION_10X_MULTIPLIER if point_data.get('production_10x_active', False) else 1.0,
            'teleport_skillset_multiplier': 1.0 + (point_data.get('teleport_skillset_level', 0) * 0.1),
        }
        return multipliers
    
    def _get_difficulty_multiplier(self, difficulty: str) -> float:
        """Get difficulty multiplier"""
        multipliers = {
            'easy': 0.8,
            'medium': 1.2,
            'hard': 1.5,
            'expert': 2.0
        }
        return multipliers.get(difficulty, 1.0)
    
    def _calculate_multiplier_product(self, multipliers: Dict[str, float]) -> float:
        """Calculate product of all multipliers"""
        product = 1.0
        for value in multipliers.values():
            product *= value
        return product


# Global instance
point_calculator_178 = PointCalculator178Systems()

