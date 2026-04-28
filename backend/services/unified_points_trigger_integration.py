"""
Unified Points Trigger Integration
Integrates triggers into all unified points systems
"""
import logging
import os
from typing import Dict, Optional
from backend.services.agent_trigger_system import agent_trigger_system

_logger = logging.getLogger(__name__)

class UnifiedPointsTriggerIntegration:
    """Integration layer for triggers in unified points system"""
    
    def __init__(self):
        self.trigger_mapping = self._create_trigger_mapping()
    
    def _create_trigger_mapping(self) -> Dict:
        """Create mapping from point types to triggers"""
        return {
            # Generation triggers
            'video_generation': 'video_generation',
            'clip_generation': 'clip_generation',
            'image_generation': 'image_generation',
            'audio_generation': 'audio_generation',
            'text_generation': 'text_generation',
            'template_usage': 'template_used',
            'custom_creation': 'custom_creation',
            'quality': 'quality_content',
            'innovation': 'innovation',
            'trending': 'trending_content',
            'viral': 'viral_content',
            'collaboration': 'collaboration',
            'remix': 'remix',
            'edit': 'edit',
            'publish': 'publish',
            'schedule': 'schedule',
            'series': 'series',
            'playlist': 'playlist',
            'collection': 'collection',
            'production_mastery': 'production_mastery',
            
            # Battle triggers
            'pvp_battle': 'pvp_battle',
            'pve_battle': 'pve_battle',
            'team_battle': 'team_battle',
            'guild_battle': 'guild_battle',
            'arena_battle': 'arena_battle',
            'tournament': 'tournament',
            'ranked_battle': 'ranked_battle',
            'casual_battle': 'casual_battle',
            'victory': 'battle_victory',
            'defeat': 'battle_victory',  # Still awards points
            'perfect_victory': 'perfect_victory',
            'comeback': 'comeback',
            'streak_battle': 'streak_battle',
            'first_blood': 'first_blood',
            'multi_kill': 'multi_kill',
            'assist': 'assist',
            'defense': 'defense',
            'offense': 'offense',
            'tactical': 'tactical',
            'strategy': 'strategy',
            'combo': 'combo',
            'ultimate': 'ultimate',
            
            # Social triggers
            'friend': 'friend_added',
            'follow': 'follow',
            'follower': 'follower_gained',
            'message': 'message_sent',
            'group': 'group_joined',
            'community': 'community_activity',
            'event': 'event_participation',
            'meetup': 'meetup',
            'discussion': 'discussion',
            'forum': 'forum_post',
            'help': 'help_provided',
            'mentor': 'mentor',
            'share': 'share_content',
            'comment': 'comment_posted',
            
            # Engagement triggers
            'watch_time': 'watch_time',
            'scroll_depth': 'scroll_depth',
            'interaction_quality': 'interaction_quality',
            'return_visitor': 'return_visitor',
            'session_duration': 'session_duration',
            'page_depth': 'page_depth',
            'content_consumption': 'content_consumption',
            'search': 'search_performed',
            'filter': 'filter_used',
            'bookmark': 'bookmark_created',
            'rating': 'rating_given',
            
            # Activity triggers
            'activity': 'daily_activity',
            'daily_login': 'daily_login',
            'streak': 'streak',
            'theme': 'theme_points',
            'chat': 'chat_points',
            'metal': 'metal_points',
            'krimetime': 'krimetime',
            'shop': 'shop_purchase',
            'stats': 'stats_points',
            
            # Achievement triggers
            'achievement': 'achievement_unlocked',
            'trophy': 'trophy_earned',
            
            # Progression triggers
            'level_up': 'level_up',
            'prestige': 'prestige',
            'graduation': 'graduation',
            'skillset_mastery': 'skillset_mastery',
            
            # Special triggers
            'death_portal_teleport': 'death_portal_teleport',
            'production_10x': 'production_10x',
            'guild': 'guild_activity',
            'champions_league': 'champions_league',
            'rewards': 'achievement_unlocked',  # Rewards trigger achievement
            
            # Economy & Trade
            'purchase': 'purchase',
            'sale': 'sale',
            'trade': 'trade',
            'auction': 'auction',
            'market': 'market',
            'currency': 'currency',
            'investment': 'investment',
            'profit': 'profit',
            'deal': 'deal',
            'negotiation': 'negotiation',
            'collection_value': 'collection_value',
            'asset': 'asset',
            'wealth': 'wealth',
            'production_economy': 'production_economy',
            'teleport_trade': 'teleport_trade',
            
            # Exploration & Discovery
            'exploration': 'exploration',
            'discovery': 'discovery',
            'unlock': 'unlock',
            'reveal': 'reveal',
            'map': 'map',
            'location': 'location',
            'hidden': 'hidden',
            'secret': 'secret',
            'easter_egg': 'easter_egg',
            'landmark': 'landmark',
            'path': 'path',
            'route': 'route',
            
            # Learning & Education
            'learning': 'learning',
            'course': 'course',
            'lesson': 'lesson',
            'quiz': 'quiz',
            'test': 'test',
            'certification': 'certification',
            'knowledge': 'knowledge',
            'skill_development': 'skill_development',
            'practice': 'practice',
            'study': 'study',
            'education': 'education',
            
            # Events & Special Occasions
            'event_participation': 'event_participation',
            'holiday': 'holiday',
            'seasonal': 'seasonal',
            'limited_time': 'limited_time',
            'special_event': 'special_event',
            'anniversary': 'anniversary',
            'festival': 'festival',
            'competition': 'competition',
            'death_portal_event': 'death_portal_event',
            
            # Customization & Personalization
            'customization': 'customization',
            'avatar': 'avatar',
            'theme_custom': 'theme_custom',
            'layout': 'layout',
            'style': 'style',
            'personalization': 'personalization',
            'preference': 'preference',
            'settings': 'settings',
            'design': 'design',
            'aesthetic': 'aesthetic',
            
            # Creativity & Innovation
            'creativity': 'creativity',
            'experiment': 'experiment',
            'invention': 'invention',
            'design_creative': 'design_creative',
            'artistic': 'artistic',
            'originality': 'originality',
            'uniqueness': 'uniqueness',
            
            # System & Contribution
            'system': 'system',
            'meta': 'meta',
            'feedback': 'feedback',
            'bug_report': 'bug_report',
            'feature_request': 'feature_request',
            'beta_test': 'beta_test',
            'quality_assurance': 'quality_assurance',
            'system_contribution': 'system_contribution',
            
            # Additional Social
            'apprentice': 'apprentice',
            'referral': 'referral',
            'invite': 'invite',
            'gift': 'gift',
            'thank_you': 'thank_you',
            'recognition': 'recognition',
            'celebration': 'celebration',
            'community_mastery': 'community_mastery',
            
            # Additional Progression
            'skill': 'skill',
            'mastery': 'mastery',
            'rank': 'rank',
            'tier': 'tier',
            'badge': 'badge',
            'medal': 'medal',
            'title': 'title',
            'achievement_chain': 'achievement_chain',
            'milestone': 'milestone',
            'progress': 'progress',
            'completion': 'completion',
            'teleport_skillset': 'teleport_skillset',
            'death_portal_mastery': 'death_portal_mastery',
            
            # Automation & Engineering Points
            'automation_points': 'automation_activity',
            'engineering_points': 'engineering_activity',
            'devops_points': 'devops_activity',
            'ai_engineering_points': 'ai_engineering_activity',
            'data_engineering_points': 'data_engineering_activity',
            'platform_engineering_points': 'platform_engineering_activity',
            'reliability_points': 'reliability_activity',
            'automation_architect_points': 'automation_architect_activity',
            'engineering_leadership_points': 'engineering_leadership_activity',
            'qa_engineering_points': 'qa_engineering_activity',
            'security_engineering_points': 'security_engineering_activity',
            'ml_ops_points': 'ml_ops_activity',

            # DNA Tech (New)
            'dna_manipulation': 'dna_manipulation',
            'dna_cloning': 'dna_cloning',

            # Communication Psychology (25 theories, starmap, profile, trophies)
            'communication_psychology_points': 'communication_psychology',
            # Compendium (Rulebook V2.1 — 10 wiki pages)
            'compendium_points': 'compendium_view',

            # Galaxy / Hunters / Electric Magnet (PHD intelligence)
            'run_verification': 'run_verification',
            'run_dna_test': 'run_dna_test',
            'view_star_map': 'view_star_map',
            'game_points': 'game_points',
            'trophy_points': 'trophy_earned',
            'hunters_star_map_view': 'hunters_star_map_view',
            'hunters_spell_used': 'hunters_spell_used',
            'event_tracker_new_task': 'event_tracker_new_task',
            'geo_reference': 'skill_execution',
            'aggregator_fill': 'skill_execution',
            'checkpoint': 'skill_execution',
            'clickthrough': 'skill_execution',
            'extend_session': 'skill_execution',
            'speaker_ruler': 'skill_execution',
        }
    
    def award_points_with_trigger(self, point_type: str, user_id: str = 'agent_user', amount: int = 1, metadata: Dict = None) -> Dict:
        """Award points with automatic trigger"""
        trigger_id = self.trigger_mapping.get(point_type)
        try:
            if trigger_id:
                result = agent_trigger_system.award_points(trigger_id, user_id, {
                    'point_type': point_type,
                    'amount': amount,
                    **(metadata or {})
                })
                return result
            return agent_trigger_system.award_points('skill_execution', user_id, {
                'point_type': point_type,
                'amount': amount,
                **(metadata or {})
            })
        except Exception as e:
            _logger.debug("award_points_with_trigger failed: %s user=%s amount=%s err=%s", point_type, user_id, amount, e)
            return {'success': False, 'error': str(e)}
    
    def award_multiple_points(self, points: Dict, user_id: str = 'agent_user', metadata: Dict = None) -> Dict:
        """Award multiple point types with triggers"""
        results = []
        total_points = {
            'xp': 0,
            'generation_points': 0,
            'battle_points': 0
        }
        
        for point_type, amount in points.items():
            if amount > 0:
                result = self.award_points_with_trigger(point_type, user_id, amount, metadata)
                if result.get('success'):
                    points_awarded = result.get('points_awarded', {})
                    total_points['xp'] += points_awarded.get('xp', 0)
                    total_points['generation_points'] += points_awarded.get('generation_points', 0)
                    total_points['battle_points'] += points_awarded.get('battle_points', 0)
                    results.append({
                        'point_type': point_type,
                        'amount': amount,
                        'trigger': result.get('trigger'),
                        'success': True
                    })
        
        return {
            'success': True,
            'results': results,
            'total_points': total_points
        }

# Global instance
unified_points_trigger_integration = UnifiedPointsTriggerIntegration()
