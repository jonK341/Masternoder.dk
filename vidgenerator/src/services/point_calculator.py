"""
Simple Point Calculator Service
Calculates total points across all 178 point systems
"""
import logging
from typing import Dict, Any, Optional

_log = logging.getLogger(__name__)


# Point Values for all 178 systems
POINT_VALUES = {
    'xp': 15,
    'activity': 1,
    'theme': 1,
    'chat': 1,
    'trophy': 1,
    'battle': 15,
    'achievement': 1,
    'stats': 1,
    'metal': 1,
    'graduation': 1,
    'generation': 15,
    'krimetime': 1,
    'guild': 1,
    'rewards': 1,
    'shop': 1,
    'social': 1,
    'champions_league': 1,
    'watch_time': 12,
    'scroll_depth': 1,
    'interaction_quality': 1,
    'return_visitor': 1,
    'session_duration': 1,
    'page_depth': 1,
    'content_consumption': 1,
    'search': 1,
    'filter': 1,
    'share': 1,
    'bookmark': 1,
    'comment': 1,
    'rating': 1,
    'pvp_battle': 240,
    'pve_battle': 240,
    'team_battle': 24,
    'guild_battle': 24,
    'arena_battle': 24,
    'tournament': 24,
    'ranked_battle': 24,
    'casual_battle': 24,
    'victory': 24,
    'defeat': 24,
    'perfect_victory': 24,
    'comeback': 24,
    'streak_battle': 24,
    'first_blood': 24,
    'multi_kill': 24,
    'assist': 24,
    'defense': 24,
    'offense': 24,
    'tactical': 24,
    'strategy': 24,
    'combo': 24,
    'ultimate': 24,
    'death_portal_teleport': 450,
    'production_10x': 3000,
    'skillset_mastery': 45,
    'video_generation': 600,
    'clip_generation': 600,
    'image_generation': 600,
    'audio_generation': 600,
    'text_generation': 60,
    'template_usage': 60,
    'custom_creation': 60,
    'quality': 60,
    'innovation': 75,
    'trending': 60,
    'viral': 60,
    'collaboration': 60,
    'remix': 60,
    'edit': 60,
    'publish': 60,
    'schedule': 60,
    'series': 60,
    'playlist': 60,
    'collection': 60,
    'production_mastery': 750,
    'friend': 18,
    'follow': 18,
    'follower': 18,
    'message': 18,
    'group': 18,
    'community': 18,
    'event': 18,
    'meetup': 18,
    'discussion': 18,
    'forum': 18,
    'help': 18,
    'mentor': 18,
    'apprentice': 18,
    'referral': 18,
    'invite': 18,
    'gift': 18,
    'thank_you': 18,
    'recognition': 18,
    'celebration': 50,
    'community_mastery': 18,
    'level_up': 120,
    'skill': 180,
    'mastery': 120,
    'prestige': 120,
    'rank': 120,
    'tier': 120,
    'badge': 120,
    'medal': 120,
    'title': 120,
    'achievement_chain': 120,
    'milestone': 120,
    'progress': 120,
    'completion': 120,
    'teleport_skillset': 225,
    'death_portal_mastery': 1500,
    'purchase': 30,
    'sale': 30,
    'trade': 30,
    'auction': 30,
    'market': 30,
    'currency': 30,
    'investment': 30,
    'profit': 30,
    'deal': 30,
    'negotiation': 30,
    'collection_value': 30,
    'asset': 30,
    'wealth': 30,
    'production_economy': 375,
    'teleport_trade': 55,
    'exploration': 30,
    'discovery': 30,
    'unlock': 30,
    'reveal': 30,
    'map': 30,
    'location': 30,
    'hidden': 30,
    'secret': 30,
    'easter_egg': 30,
    'landmark': 30,
    'path': 30,
    'route': 30,
    'learning': 40,
    'course': 40,
    'lesson': 40,
    'quiz': 40,
    'test': 40,
    'certification': 40,
    'knowledge': 40,
    'skill_development': 60,
    'practice': 40,
    'study': 40,
    'research': 40,
    'education': 40,
    'event_participation': 50,
    'holiday': 50,
    'seasonal': 50,
    'limited_time': 50,
    'special_event': 50,
    'anniversary': 50,
    'festival': 50,
    'competition': 50,
    'death_portal_event': 750,
    'customization': 10,
    'avatar': 10,
    'theme_custom': 10,
    'layout': 10,
    'style': 10,
    'personalization': 10,
    'preference': 10,
    'settings': 10,
    'design': 10,
    'aesthetic': 10,
    'creativity': 75,
    'experiment': 75,
    'invention': 75,
    'design_creative': 75,
    'artistic': 75,
    'originality': 75,
    'uniqueness': 75,
    'system': 20,
    'meta': 20,
    'feedback': 20,
    'bug_report': 20,
    'feature_request': 20,
    'beta_test': 20,
    'quality_assurance': 20,
    'system_contribution': 20,
}


class PointCalculator:
    """Simple point calculator for all 178 systems"""
    
    def __init__(self):
        self.point_values = POINT_VALUES
    
    def calculate_total_points(self, point_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate total points from point data
        
        Args:
            point_data: Dictionary containing point values for each system
                       Keys should match system names (e.g., 'xp', 'activity', etc.)
        
        Returns:
            Dictionary with:
            - success: bool
            - total_points: float
            - breakdown: dict with points per system
            - systems_count: int
        """
        try:
            total_points = 0.0
            breakdown = {}
            systems_count = 0
            
            # Calculate points for each system
            for system_name, point_value in self.point_values.items():
                # Get the actual point count from point_data
                # Try different key formats
                point_count = 0
                
                # Try direct key match
                if system_name in point_data:
                    point_count = float(point_data[system_name] or 0)
                # Try with _points suffix
                elif f"{system_name}_points" in point_data:
                    point_count = float(point_data[f"{system_name}_points"] or 0)
                # Try with _point suffix
                elif f"{system_name}_point" in point_data:
                    point_count = float(point_data[f"{system_name}_point"] or 0)
                
                # Calculate points for this system
                calculated_points = point_count * point_value
                total_points += calculated_points
                
                if calculated_points > 0:
                    breakdown[system_name] = {
                        'count': point_count,
                        'point_value': point_value,
                        'calculated': calculated_points
                    }
                    systems_count += 1
                    
                    # Trigger points for this system
                    try:
                        from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
                        unified_points_trigger_integration.award_points_with_trigger(
                            system_name,
                            point_data.get('user_id', 'default_user'),
                            int(point_count),
                            {'calculated_points': calculated_points}
                        )
                    except Exception as ex:
                        _log.debug("Point calculator trigger skipped for %s: %s", system_name, ex)
            
            return {
                'success': True,
                'total_points': total_points,
                'breakdown': breakdown,
                'systems_count': systems_count,
                'total_systems': len(self.point_values)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'total_points': 0.0,
                'breakdown': {},
                'systems_count': 0
            }
    
    def calculate_system_points(self, system_name: str, point_count: float) -> float:
        """
        Calculate points for a single system
        
        Args:
            system_name: Name of the system (e.g., 'xp', 'battle')
            point_count: Number of points/actions for this system
        
        Returns:
            Calculated points (point_count * point_value)
        """
        point_value = self.point_values.get(system_name, 0)
        return float(point_count) * point_value
    
    def get_point_value(self, system_name: str) -> float:
        """
        Get the point value for a system
        
        Args:
            system_name: Name of the system
        
        Returns:
            Point value for the system, or 0 if not found
        """
        return self.point_values.get(system_name, 0)
    
    def get_all_systems(self) -> list:
        """
        Get list of all system names
        
        Returns:
            List of all 178 system names
        """
        return list(self.point_values.keys())
    
    def get_systems_count(self) -> int:
        """
        Get total number of systems
        
        Returns:
            Total number of systems (178)
        """
        return len(self.point_values)
