"""
Expanded Triggers System
Comprehensive triggers for all 178 point systems
"""
from backend.services.agent_trigger_system import agent_trigger_system
from typing import Dict, List

class ExpandedTriggersSystem:
    """Expanded triggers for all point systems"""
    
    def __init__(self):
        self.additional_triggers = self._create_additional_triggers()
    
    def _create_additional_triggers(self) -> List[Dict]:
        """Create additional triggers for all 178 systems"""
        return [
            # Economy & Trade Triggers
            {
                'id': 'purchase',
                'name': 'Purchase',
                'type': 'economy',
                'condition': 'purchase_completed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'sale',
                'name': 'Sale',
                'type': 'economy',
                'condition': 'sale_completed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'trade',
                'name': 'Trade',
                'type': 'economy',
                'condition': 'trade_completed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'auction',
                'name': 'Auction',
                'type': 'economy',
                'condition': 'auction_participated',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'market',
                'name': 'Market',
                'type': 'economy',
                'condition': 'market_activity',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'currency',
                'name': 'Currency',
                'type': 'economy',
                'condition': 'currency_earned',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'investment',
                'name': 'Investment',
                'type': 'economy',
                'condition': 'investment_made',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'profit',
                'name': 'Profit',
                'type': 'economy',
                'condition': 'profit_earned',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'deal',
                'name': 'Deal',
                'type': 'economy',
                'condition': 'deal_completed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'negotiation',
                'name': 'Negotiation',
                'type': 'economy',
                'condition': 'negotiation_completed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'collection_value',
                'name': 'Collection Value',
                'type': 'economy',
                'condition': 'collection_value_increased',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'asset',
                'name': 'Asset',
                'type': 'economy',
                'condition': 'asset_acquired',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'wealth',
                'name': 'Wealth',
                'type': 'economy',
                'condition': 'wealth_increased',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'production_economy',
                'name': 'Production Economy',
                'type': 'economy',
                'condition': 'production_economy_activity',
                'points': {'xp': 375, 'generation_points': 188, 'battle_points': 94},
                'enabled': True
            },
            {
                'id': 'teleport_trade',
                'name': 'Teleport Trade',
                'type': 'economy',
                'condition': 'teleport_trade_completed',
                'points': {'xp': 55, 'generation_points': 28, 'battle_points': 14},
                'enabled': True
            },
            
            # Exploration & Discovery Triggers
            {
                'id': 'exploration',
                'name': 'Exploration',
                'type': 'exploration',
                'condition': 'area_explored',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'discovery',
                'name': 'Discovery',
                'type': 'exploration',
                'condition': 'discovery_made',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'unlock',
                'name': 'Unlock',
                'type': 'exploration',
                'condition': 'content_unlocked',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'reveal',
                'name': 'Reveal',
                'type': 'exploration',
                'condition': 'secret_revealed',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'map',
                'name': 'Map',
                'type': 'exploration',
                'condition': 'map_discovered',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'location',
                'name': 'Location',
                'type': 'exploration',
                'condition': 'location_visited',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'hidden',
                'name': 'Hidden',
                'type': 'exploration',
                'condition': 'hidden_content_found',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'secret',
                'name': 'Secret',
                'type': 'exploration',
                'condition': 'secret_found',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'easter_egg',
                'name': 'Easter Egg',
                'type': 'exploration',
                'condition': 'easter_egg_found',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'landmark',
                'name': 'Landmark',
                'type': 'exploration',
                'condition': 'landmark_discovered',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'path',
                'name': 'Path',
                'type': 'exploration',
                'condition': 'path_discovered',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            {
                'id': 'route',
                'name': 'Route',
                'type': 'exploration',
                'condition': 'route_discovered',
                'points': {'xp': 30, 'generation_points': 15, 'battle_points': 8},
                'enabled': True
            },
            
            # Learning & Education Triggers
            {
                'id': 'learning',
                'name': 'Learning',
                'type': 'education',
                'condition': 'learning_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'course',
                'name': 'Course',
                'type': 'education',
                'condition': 'course_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'lesson',
                'name': 'Lesson',
                'type': 'education',
                'condition': 'lesson_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'quiz',
                'name': 'Quiz',
                'type': 'education',
                'condition': 'quiz_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'test',
                'name': 'Test',
                'type': 'education',
                'condition': 'test_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'certification',
                'name': 'Certification',
                'type': 'education',
                'condition': 'certification_earned',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'knowledge',
                'name': 'Knowledge',
                'type': 'education',
                'condition': 'knowledge_gained',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'skill_development',
                'name': 'Skill Development',
                'type': 'education',
                'condition': 'skill_developed',
                'points': {'xp': 60, 'generation_points': 30, 'battle_points': 15},
                'enabled': True
            },
            {
                'id': 'practice',
                'name': 'Practice',
                'type': 'education',
                'condition': 'practice_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'study',
                'name': 'Study',
                'type': 'education',
                'condition': 'study_session',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            {
                'id': 'education',
                'name': 'Education',
                'type': 'education',
                'condition': 'education_completed',
                'points': {'xp': 40, 'generation_points': 20, 'battle_points': 10},
                'enabled': True
            },
            
            # Events & Special Occasions Triggers
            {
                'id': 'event_participation',
                'name': 'Event Participation',
                'type': 'event',
                'condition': 'event_participated',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'holiday',
                'name': 'Holiday',
                'type': 'event',
                'condition': 'holiday_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'seasonal',
                'name': 'Seasonal',
                'type': 'event',
                'condition': 'seasonal_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'limited_time',
                'name': 'Limited Time',
                'type': 'event',
                'condition': 'limited_time_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'special_event',
                'name': 'Special Event',
                'type': 'event',
                'condition': 'special_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'anniversary',
                'name': 'Anniversary',
                'type': 'event',
                'condition': 'anniversary_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'festival',
                'name': 'Festival',
                'type': 'event',
                'condition': 'festival_event',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'competition',
                'name': 'Competition',
                'type': 'event',
                'condition': 'competition_participated',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'death_portal_event',
                'name': 'Death Portal Event',
                'type': 'event',
                'condition': 'death_portal_event',
                'points': {'xp': 750, 'generation_points': 375, 'battle_points': 188},
                'enabled': True
            },
            
            # Customization & Personalization Triggers
            {
                'id': 'customization',
                'name': 'Customization',
                'type': 'customization',
                'condition': 'customization_applied',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'avatar',
                'name': 'Avatar',
                'type': 'customization',
                'condition': 'avatar_updated',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'theme_custom',
                'name': 'Theme Custom',
                'type': 'customization',
                'condition': 'theme_customized',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'layout',
                'name': 'Layout',
                'type': 'customization',
                'condition': 'layout_changed',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'style',
                'name': 'Style',
                'type': 'customization',
                'condition': 'style_applied',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'personalization',
                'name': 'Personalization',
                'type': 'customization',
                'condition': 'personalization_applied',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'preference',
                'name': 'Preference',
                'type': 'customization',
                'condition': 'preference_set',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'settings',
                'name': 'Settings',
                'type': 'customization',
                'condition': 'settings_updated',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'design',
                'name': 'Design',
                'type': 'customization',
                'condition': 'design_applied',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            {
                'id': 'aesthetic',
                'name': 'Aesthetic',
                'type': 'customization',
                'condition': 'aesthetic_applied',
                'points': {'xp': 10, 'generation_points': 5, 'battle_points': 2},
                'enabled': True
            },
            
            # Creativity & Innovation Triggers
            {
                'id': 'creativity',
                'name': 'Creativity',
                'type': 'creativity',
                'condition': 'creative_content',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'experiment',
                'name': 'Experiment',
                'type': 'creativity',
                'condition': 'experiment_completed',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'invention',
                'name': 'Invention',
                'type': 'creativity',
                'condition': 'invention_created',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'design_creative',
                'name': 'Creative Design',
                'type': 'creativity',
                'condition': 'creative_design',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'artistic',
                'name': 'Artistic',
                'type': 'creativity',
                'condition': 'artistic_content',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'originality',
                'name': 'Originality',
                'type': 'creativity',
                'condition': 'original_content',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            {
                'id': 'uniqueness',
                'name': 'Uniqueness',
                'type': 'creativity',
                'condition': 'unique_content',
                'points': {'xp': 75, 'generation_points': 37, 'battle_points': 19},
                'enabled': True
            },
            
            # System & Contribution Triggers
            {
                'id': 'system',
                'name': 'System',
                'type': 'system',
                'condition': 'system_activity',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'meta',
                'name': 'Meta',
                'type': 'system',
                'condition': 'meta_activity',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'feedback',
                'name': 'Feedback',
                'type': 'system',
                'condition': 'feedback_provided',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'bug_report',
                'name': 'Bug Report',
                'type': 'system',
                'condition': 'bug_reported',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'feature_request',
                'name': 'Feature Request',
                'type': 'system',
                'condition': 'feature_requested',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'beta_test',
                'name': 'Beta Test',
                'type': 'system',
                'condition': 'beta_tested',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'quality_assurance',
                'name': 'Quality Assurance',
                'type': 'system',
                'condition': 'qa_completed',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'system_contribution',
                'name': 'System Contribution',
                'type': 'system',
                'condition': 'contribution_made',
                'points': {'xp': 20, 'generation_points': 10, 'battle_points': 5},
                'enabled': True
            },
            
            # Additional Social Triggers
            {
                'id': 'apprentice',
                'name': 'Apprentice',
                'type': 'social',
                'condition': 'apprentice_activity',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'referral',
                'name': 'Referral',
                'type': 'social',
                'condition': 'referral_made',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'invite',
                'name': 'Invite',
                'type': 'social',
                'condition': 'invite_sent',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'gift',
                'name': 'Gift',
                'type': 'social',
                'condition': 'gift_sent',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'thank_you',
                'name': 'Thank You',
                'type': 'social',
                'condition': 'thank_you_sent',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'recognition',
                'name': 'Recognition',
                'type': 'social',
                'condition': 'recognition_given',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            {
                'id': 'celebration',
                'name': 'Celebration',
                'type': 'social',
                'condition': 'celebration_held',
                'points': {'xp': 50, 'generation_points': 25, 'battle_points': 12},
                'enabled': True
            },
            {
                'id': 'community_mastery',
                'name': 'Community Mastery',
                'type': 'social',
                'condition': 'community_mastery',
                'points': {'xp': 18, 'generation_points': 9, 'battle_points': 5},
                'enabled': True
            },
            
            # Progression & Mastery Triggers
            {
                'id': 'skill',
                'name': 'Skill',
                'type': 'progression',
                'condition': 'skill_earned',
                'points': {'xp': 180, 'generation_points': 90, 'battle_points': 45},
                'enabled': True
            },
            {
                'id': 'mastery',
                'name': 'Mastery',
                'type': 'progression',
                'condition': 'mastery_achieved',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'rank',
                'name': 'Rank',
                'type': 'progression',
                'condition': 'rank_achieved',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'tier',
                'name': 'Tier',
                'type': 'progression',
                'condition': 'tier_achieved',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'badge',
                'name': 'Badge',
                'type': 'progression',
                'condition': 'badge_earned',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'medal',
                'name': 'Medal',
                'type': 'progression',
                'condition': 'medal_earned',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'title',
                'name': 'Title',
                'type': 'progression',
                'condition': 'title_earned',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'achievement_chain',
                'name': 'Achievement Chain',
                'type': 'progression',
                'condition': 'achievement_chain_completed',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'milestone',
                'name': 'Milestone',
                'type': 'progression',
                'condition': 'milestone_reached',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'progress',
                'name': 'Progress',
                'type': 'progression',
                'condition': 'progress_made',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'completion',
                'name': 'Completion',
                'type': 'progression',
                'condition': 'completion_achieved',
                'points': {'xp': 120, 'generation_points': 60, 'battle_points': 30},
                'enabled': True
            },
            {
                'id': 'teleport_skillset',
                'name': 'Teleport Skillset',
                'type': 'progression',
                'condition': 'teleport_skillset_earned',
                'points': {'xp': 225, 'generation_points': 113, 'battle_points': 56},
                'enabled': True
            },
            {
                'id': 'death_portal_mastery',
                'name': 'Death Portal Mastery',
                'type': 'progression',
                'condition': 'death_portal_mastery',
                'points': {'xp': 1500, 'generation_points': 750, 'battle_points': 375},
                'enabled': True
            }
        ]
    
    def register_all_triggers(self):
        """Register all additional triggers"""
        for trigger in self.additional_triggers:
            agent_trigger_system.create_trigger(trigger)
        return len(self.additional_triggers)

# Global instance
expanded_triggers_system = ExpandedTriggersSystem()
