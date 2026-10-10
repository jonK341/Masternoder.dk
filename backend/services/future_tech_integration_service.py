"""
Future Tech Integration Service
Integrates all future tech systems (Time Machine, Technology Intelligence) 
with Dashboard, Profile, Social, Gallery, Aggregator, Battle, and Arena Battle
Also integrates Advanced Intelligent Calculator for equation solving
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# Future Tech Imports
try:
    from backend.services.creative_timemashine_500plus import creative_timemashine_500plus
    from backend.services.technology_intelligence_battle import technology_intelligence_battle
    FUTURE_TECH_AVAILABLE = True
except ImportError:
    creative_timemashine_500plus = None
    technology_intelligence_battle = None
    FUTURE_TECH_AVAILABLE = False

# Calculator Import
try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    CALCULATOR_AVAILABLE = True
except ImportError:
    advanced_intelligent_calculator = None
    CALCULATOR_AVAILABLE = False

# Core Systems
try:
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.battle_v3_ultimate import battle_v3_ultimate
    from backend.services.battle_arena_gear_system import battle_arena_gear_system
    CORE_SYSTEMS_AVAILABLE = True
except ImportError:
    unified_point_counter = None
    battle_v3_ultimate = None
    battle_arena_gear_system = None
    CORE_SYSTEMS_AVAILABLE = False


class FutureTechIntegrationService:
    """
    Integration service that connects all components with future tech and calculator
    """
    
    def __init__(self):
        self.integrations = {}
        self.calculation_cache = {}
    
    def enhance_dashboard_stats(self, user_id: str, base_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance dashboard stats with future tech and calculator
        
        Args:
            user_id: User identifier
            base_stats: Base statistics from aggregator
        """
        enhanced_stats = base_stats.copy()
        
        # Add future tech projections
        if FUTURE_TECH_AVAILABLE:
            try:
                # Get user's future projections
                projections_result = creative_timemashine_500plus.get_user_projections(user_id)
                if projections_result.get('success'):
                    enhanced_stats['future_projections'] = {
                        'count': len(projections_result.get('projections', [])),
                        'latest_projection_year': self._get_latest_projection_year(projections_result.get('projections', []))
                    }
                
                # Get downloaded technologies
                tech_result = technology_intelligence_battle.get_downloaded_tech(user_id)
                if tech_result.get('success'):
                    downloaded_tech = tech_result.get('downloaded_technologies', [])
                    enhanced_stats['future_technologies'] = {
                        'count': len(downloaded_tech),
                        'total_power': sum(
                            tech.get('intelligence_data', {}).get('battle_power', 0)
                            for tech in downloaded_tech
                        )
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing dashboard stats: {e}")
        
        # Add calculator-enhanced calculations
        if CALCULATOR_AVAILABLE and unified_point_counter:
            try:
                point_data = unified_point_counter.get_all_points(user_id) or {}
                calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                    point_data, user_id
                )
                enhanced_stats['calculator_enhancements'] = {
                    'final_calculation': calc_result.get('final_calculation', {}),
                    'confidence_score': calc_result.get('confidence_score', 0),
                    'intelligent_multipliers': calc_result.get('intelligent_multipliers', {})
                }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding calculator enhancements: {e}")
        
        enhanced_stats['integration_timestamp'] = datetime.utcnow().isoformat()
        enhanced_stats['future_tech_enabled'] = FUTURE_TECH_AVAILABLE
        enhanced_stats['calculator_enabled'] = CALCULATOR_AVAILABLE
        
        return enhanced_stats
    
    def enhance_profile_data(self, user_id: str, base_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance profile data with future tech and calculator
        
        Args:
            user_id: User identifier
            base_profile: Base profile data
        """
        enhanced_profile = base_profile.copy()
        
        # Add future tech to profile
        if FUTURE_TECH_AVAILABLE:
            try:
                # Get future projections summary
                projections_result = creative_timemashine_500plus.get_user_projections(user_id)
                if projections_result.get('success'):
                    projections = projections_result.get('projections', [])
                    enhanced_profile['future_projections_summary'] = {
                        'total_projections': len(projections),
                        'furthest_year': self._get_latest_projection_year(projections),
                        'technologies_unlocked': len([
                            p for p in projections 
                            for tech in p.get('available_technologies', [])
                        ])
                    }
                
                # Get technology intelligence summary
                tech_result = technology_intelligence_battle.get_downloaded_tech(user_id)
                if tech_result.get('success'):
                    downloaded_tech = tech_result.get('downloaded_technologies', [])
                    enhanced_profile['technology_intelligence'] = {
                        'downloaded_technologies': len(downloaded_tech),
                        'integrated_technologies': sum(
                            1 for tech in downloaded_tech if tech.get('integrated', False)
                        ),
                        'total_intelligence_score': sum(
                            tech.get('intelligence_data', {}).get('intelligence_score', 0)
                            for tech in downloaded_tech
                        )
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing profile: {e}")
        
        # Add calculator intelligence to profile
        if CALCULATOR_AVAILABLE:
            try:
                if unified_point_counter:
                    point_data = unified_point_counter.get_all_points(user_id) or {}
                    calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                        point_data, user_id
                    )
                    enhanced_profile['calculator_intelligence'] = {
                        'calculations_performed': calc_result.get('calculation_id', ''),
                        'confidence_level': calc_result.get('confidence_score', 0),
                        'advanced_features_used': list(calc_result.get('advanced_features', {}).keys())
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding calculator to profile: {e}")
        
        enhanced_profile['enhanced_at'] = datetime.utcnow().isoformat()
        
        return enhanced_profile
    
    def enhance_social_data(self, user_id: str, base_social: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance social data with future tech
        
        Args:
            user_id: User identifier
            base_social: Base social data
        """
        enhanced_social = base_social.copy()
        
        # Add future tech social features
        if FUTURE_TECH_AVAILABLE:
            try:
                # Social sharing of future projections
                projections_result = creative_timemashine_500plus.get_user_projections(user_id)
                if projections_result.get('success'):
                    enhanced_social['shareable_projections'] = [
                        {
                            'projection_id': p.get('projection_id'),
                            'target_year': p.get('target_year'),
                            'years_ahead': p.get('years_ahead')
                        }
                        for p in projections_result.get('projections', [])[-5:]  # Last 5
                    ]
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing social data: {e}")
        
        enhanced_social['future_tech_enabled'] = FUTURE_TECH_AVAILABLE
        
        return enhanced_social
    
    def enhance_gallery_data(self, user_id: str, base_gallery: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance gallery data with future tech
        
        Args:
            user_id: User identifier
            base_gallery: Base gallery data
        """
        enhanced_gallery = base_gallery.copy()
        
        # Add future tech to gallery
        if FUTURE_TECH_AVAILABLE:
            try:
                # Add projection videos as "future content"
                projections_result = creative_timemashine_500plus.get_user_projections(user_id)
                if projections_result.get('success'):
                    enhanced_gallery['future_content_available'] = len(
                        projections_result.get('projections', [])
                    ) > 0
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing gallery: {e}")
        
        enhanced_gallery['enhanced_at'] = datetime.utcnow().isoformat()
        
        return enhanced_gallery
    
    def enhance_aggregator_data(self, user_id: str, base_aggregated: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance aggregator data with future tech and calculator
        
        Args:
            user_id: User identifier
            base_aggregated: Base aggregated data
        """
        enhanced = base_aggregated.copy()
        
        # Add future tech summary
        if FUTURE_TECH_AVAILABLE:
            try:
                # Get comprehensive future tech summary
                projections_result = creative_timemashine_500plus.get_user_projections(user_id)
                tech_result = technology_intelligence_battle.get_downloaded_tech(user_id)
                
                enhanced['future_tech_summary'] = {
                    'projections_count': len(projections_result.get('projections', [])) if projections_result.get('success') else 0,
                    'downloaded_tech_count': len(tech_result.get('downloaded_technologies', [])) if tech_result.get('success') else 0,
                    'future_tech_active': True
                }
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing aggregator: {e}")
        
        # Add calculator summary
        if CALCULATOR_AVAILABLE:
            try:
                if unified_point_counter:
                    point_data = unified_point_counter.get_all_points(user_id) or {}
                    calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                        point_data, user_id
                    )
                    enhanced['calculator_summary'] = {
                        'calculator_active': True,
                        'confidence_score': calc_result.get('confidence_score', 0),
                        'advanced_features_count': len(calc_result.get('advanced_features', {}))
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding calculator to aggregator: {e}")
        
        enhanced['integration_timestamp'] = datetime.utcnow().isoformat()
        
        return enhanced
    
    def enhance_battle_data(self, battle_id: str, user_id: str, 
                           base_battle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance battle data with future tech and calculator
        
        Args:
            battle_id: Battle identifier
            user_id: User identifier
            base_battle: Base battle data
        """
        enhanced_battle = base_battle.copy()
        
        # Add technology intelligence to battle
        if FUTURE_TECH_AVAILABLE:
            try:
                # Get battle logic with technology intelligence
                logic_result = technology_intelligence_battle.get_battle_logic(battle_id)
                if logic_result.get('success'):
                    battle_logic = logic_result.get('battle_logic', {})
                    enhanced_battle['technology_intelligence'] = {
                        'tech_integrations': battle_logic.get('total_tech_integrations', 0),
                        'combined_updates': battle_logic.get('combined_updates', {}),
                        'integrated_technologies': battle_logic.get('integrated_technologies', [])
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error enhancing battle with tech: {e}")
        
        # Add calculator calculations to battle
        if CALCULATOR_AVAILABLE:
            try:
                if unified_point_counter:
                    point_data = unified_point_counter.get_all_points(user_id) or {}
                    calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                        point_data, user_id
                    )
                    enhanced_battle['calculator_power'] = {
                        'base_power': base_battle.get('user_power', 0),
                        'calculated_power': calc_result.get('final_calculation', {}).get('total_points', 0),
                        'multipliers': calc_result.get('intelligent_multipliers', {})
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding calculator to battle: {e}")
        
        enhanced_battle['enhanced_at'] = datetime.utcnow().isoformat()
        
        return enhanced_battle
    
    def enhance_arena_battle_data(self, battle_id: str, user_id: str,
                                 base_arena_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance arena battle data with future tech, calculator, and gear
        
        Args:
            battle_id: Battle identifier
            user_id: User identifier
            base_arena_data: Base arena battle data
        """
        enhanced = base_arena_data.copy()
        
        # Add gear system data
        if CORE_SYSTEMS_AVAILABLE and battle_arena_gear_system:
            try:
                user_gear = battle_arena_gear_system.get_user_gear(user_id)
                enhanced['gear_stats'] = {
                    'total_stats': user_gear.get('total_stats', {}),
                    'equipped_gear': user_gear.get('equipped_gear', {}),
                    'gear_power_bonus': user_gear.get('total_stats', {}).get('power_bonus', 0)
                }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding gear to arena: {e}")
        
        # Add technology intelligence (same as regular battle)
        enhanced = self.enhance_battle_data(battle_id, user_id, enhanced)
        
        # Add calculator with gear considerations
        if CALCULATOR_AVAILABLE:
            try:
                if unified_point_counter:
                    point_data = unified_point_counter.get_all_points(user_id) or {}
                    # Include gear data in calculation
                    if 'gear_stats' in enhanced:
                        point_data['gear_stats'] = enhanced['gear_stats']
                    
                    calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                        point_data, user_id
                    )
                    enhanced['arena_calculator_power'] = {
                        'base_power': enhanced.get('user_power', 0),
                        'gear_bonus': enhanced.get('gear_stats', {}).get('gear_power_bonus', 0),
                        'calculated_total': calc_result.get('final_calculation', {}).get('total_points', 0),
                        'technology_boost': enhanced.get('technology_intelligence', {}).get('combined_updates', {}).get('power_multiplier', 1.0)
                    }
            except Exception as e:
                print(f"[FutureTechIntegration] Error adding calculator to arena: {e}")
        
        enhanced['arena_enhanced_at'] = datetime.utcnow().isoformat()
        
        return enhanced
    
    def solve_equation(self, equation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Solve equation using advanced intelligent calculator
        
        Args:
            equation: Equation to solve (can be point calculation equation)
            context: Context data (user_id, point_data, etc.)
        """
        if not CALCULATOR_AVAILABLE:
            return {
                'success': False,
                'error': 'Calculator not available'
            }
        
        try:
            user_id = context.get('user_id', 'default_user') if context else 'default_user'
            point_data = context.get('point_data', {}) if context else {}
            
            # If equation is in point data format, use calculator
            if point_data:
                result = advanced_intelligent_calculator.calculate_with_intelligence(
                    point_data, user_id
                )
                return {
                    'success': True,
                    'equation': equation,
                    'result': result.get('final_calculation', {}),
                    'calculation_id': result.get('calculation_id', ''),
                    'confidence': result.get('confidence_score', 0)
                }
            else:
                # Try to parse and solve equation
                return {
                    'success': False,
                    'error': 'Equation parsing not yet implemented. Provide point_data in context.'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        return {
            'future_tech_available': FUTURE_TECH_AVAILABLE,
            'calculator_available': CALCULATOR_AVAILABLE,
            'core_systems_available': CORE_SYSTEMS_AVAILABLE,
            'integrations_active': {
                'time_machine': creative_timemashine_500plus is not None,
                'technology_intelligence': technology_intelligence_battle is not None,
                'advanced_calculator': advanced_intelligent_calculator is not None,
                'unified_points': unified_point_counter is not None,
                'battle_v3': battle_v3_ultimate is not None,
                'arena_gear': battle_arena_gear_system is not None
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_latest_projection_year(self, projections: List[Dict]) -> Optional[int]:
        """Get the latest/furthest projection year"""
        if not projections:
            return None
        
        years = [p.get('target_year', 0) for p in projections if p.get('target_year')]
        return max(years) if years else None


# Global instance
future_tech_integration_service = FutureTechIntegrationService()

