#!/usr/bin/env python3
"""
Generate 178 Point Systems - Complete System Allocation
Integrates with Death Portal Teleport and 10x Production theme
"""
import json
from typing import Dict, List, Any

# Death Portal & 10x Production Theme Integration
DEATH_PORTAL_MULTIPLIER = 10.0  # 10x production multiplier
TELEPORT_SKILLSET_BONUS = 1.5   # Teleport skillset bonus

# All 178 Point Systems from Expansion Plan
ALL_178_SYSTEMS = {
    # Category 1: Core Engagement (30 Systems)
    'core_engagement': {
        'category': 'Core Engagement',
        'icon': '⭐',
        'color': '#FFD700',
        'systems': [
            {'id': 'xp', 'name': 'XP Points', 'icon': '⭐', 'priority': 1, 'death_portal_multiplier': True},
            {'id': 'activity', 'name': 'Activity Points', 'icon': '📊', 'priority': 1},
            {'id': 'theme', 'name': 'Theme Points', 'icon': '🎨', 'priority': 1},
            {'id': 'chat', 'name': 'Chat Points', 'icon': '💬', 'priority': 1},
            {'id': 'trophy', 'name': 'Trophy Points', 'icon': '🏆', 'priority': 1},
            {'id': 'battle', 'name': 'Battle Points', 'icon': '⚔️', 'priority': 1, 'death_portal_multiplier': True},
            {'id': 'achievement', 'name': 'Achievement Points', 'icon': '🎖️', 'priority': 1},
            {'id': 'stats', 'name': 'Stats Points', 'icon': '📈', 'priority': 1},
            {'id': 'metal', 'name': 'Metal Points', 'icon': '🔩', 'priority': 1},
            {'id': 'graduation', 'name': 'Graduation Points', 'icon': '🎓', 'priority': 1},
            {'id': 'generation', 'name': 'Generation Points', 'icon': '🎬', 'priority': 1, 'production_10x': True},
            {'id': 'krimetime', 'name': 'Krimetime Points', 'icon': '⏰', 'priority': 1},
            {'id': 'guild', 'name': 'Guild Points', 'icon': '👥', 'priority': 1},
            {'id': 'rewards', 'name': 'Rewards Points', 'icon': '🎁', 'priority': 1},
            {'id': 'shop', 'name': 'Shop Points', 'icon': '🛒', 'priority': 1},
            {'id': 'social', 'name': 'Social Points', 'icon': '👤', 'priority': 1},
            {'id': 'champions_league', 'name': 'Champions League Points', 'icon': '🏅', 'priority': 1},
            {'id': 'watch_time', 'name': 'Watch Time Points', 'icon': '⏱️', 'priority': 2, 'production_10x': True},
            {'id': 'scroll_depth', 'name': 'Scroll Depth Points', 'icon': '📜', 'priority': 2},
            {'id': 'interaction_quality', 'name': 'Interaction Quality Points', 'icon': '✨', 'priority': 2},
            {'id': 'return_visitor', 'name': 'Return Visitor Points', 'icon': '🔄', 'priority': 2},
            {'id': 'session_duration', 'name': 'Session Duration Points', 'icon': '⏳', 'priority': 2},
            {'id': 'page_depth', 'name': 'Page Depth Points', 'icon': '📄', 'priority': 2},
            {'id': 'content_consumption', 'name': 'Content Consumption Points', 'icon': '📚', 'priority': 2},
            {'id': 'search', 'name': 'Search Points', 'icon': '🔍', 'priority': 2},
            {'id': 'filter', 'name': 'Filter Points', 'icon': '🔧', 'priority': 2},
            {'id': 'share', 'name': 'Share Points', 'icon': '📤', 'priority': 2},
            {'id': 'bookmark', 'name': 'Bookmark Points', 'icon': '🔖', 'priority': 2},
            {'id': 'comment', 'name': 'Comment Points', 'icon': '💭', 'priority': 2},
            {'id': 'rating', 'name': 'Rating Points', 'icon': '⭐', 'priority': 2},
        ]
    },
    
    # Category 2: Battle & Combat (25 Systems)
    'battle_combat': {
        'category': 'Battle & Combat',
        'icon': '⚔️',
        'color': '#FF4444',
        'systems': [
            {'id': 'pvp_battle', 'name': 'PvP Battle Points', 'icon': '⚔️', 'priority': 2, 'death_portal_multiplier': True},
            {'id': 'pve_battle', 'name': 'PvE Battle Points', 'icon': '🗡️', 'priority': 2, 'death_portal_multiplier': True},
            {'id': 'team_battle', 'name': 'Team Battle Points', 'icon': '👥', 'priority': 2},
            {'id': 'guild_battle', 'name': 'Guild Battle Points', 'icon': '🏰', 'priority': 2},
            {'id': 'arena_battle', 'name': 'Arena Battle Points', 'icon': '🎯', 'priority': 2},
            {'id': 'tournament', 'name': 'Tournament Points', 'icon': '🏆', 'priority': 2},
            {'id': 'ranked_battle', 'name': 'Ranked Battle Points', 'icon': '📊', 'priority': 2},
            {'id': 'casual_battle', 'name': 'Casual Battle Points', 'icon': '🎮', 'priority': 2},
            {'id': 'victory', 'name': 'Victory Points', 'icon': '✅', 'priority': 2},
            {'id': 'defeat', 'name': 'Defeat Points', 'icon': '❌', 'priority': 2},
            {'id': 'perfect_victory', 'name': 'Perfect Victory Points', 'icon': '💯', 'priority': 2},
            {'id': 'comeback', 'name': 'Comeback Points', 'icon': '🔄', 'priority': 2},
            {'id': 'streak_battle', 'name': 'Streak Battle Points', 'icon': '🔥', 'priority': 2},
            {'id': 'first_blood', 'name': 'First Blood Points', 'icon': '🩸', 'priority': 2},
            {'id': 'multi_kill', 'name': 'Multi-Kill Points', 'icon': '⚡', 'priority': 2},
            {'id': 'assist', 'name': 'Assist Points', 'icon': '🤝', 'priority': 2},
            {'id': 'defense', 'name': 'Defense Points', 'icon': '🛡️', 'priority': 2},
            {'id': 'offense', 'name': 'Offense Points', 'icon': '⚔️', 'priority': 2},
            {'id': 'tactical', 'name': 'Tactical Points', 'icon': '🧠', 'priority': 2},
            {'id': 'strategy', 'name': 'Strategy Points', 'icon': '📋', 'priority': 2},
            {'id': 'combo', 'name': 'Combo Points', 'icon': '💥', 'priority': 2},
            {'id': 'ultimate', 'name': 'Ultimate Points', 'icon': '🌟', 'priority': 2},
            {'id': 'death_portal_teleport', 'name': 'Death Portal Teleport Points', 'icon': '🌀', 'priority': 1, 'death_portal_multiplier': True, 'teleport_skillset': True},
            {'id': 'production_10x', 'name': '10x Production Points', 'icon': '🚀', 'priority': 1, 'production_10x': True, 'death_portal_multiplier': True},
            {'id': 'skillset_mastery', 'name': 'Skillset Mastery Points', 'icon': '🎯', 'priority': 1, 'teleport_skillset': True},
        ]
    },
    
    # Category 3: Content Creation (20 Systems)
    'content_creation': {
        'category': 'Content Creation',
        'icon': '🎬',
        'color': '#E74C3C',
        'systems': [
            {'id': 'video_generation', 'name': 'Video Generation Points', 'icon': '🎥', 'priority': 2, 'production_10x': True},
            {'id': 'clip_generation', 'name': 'Clip Generation Points', 'icon': '✂️', 'priority': 2, 'production_10x': True},
            {'id': 'image_generation', 'name': 'Image Generation Points', 'icon': '🖼️', 'priority': 2, 'production_10x': True},
            {'id': 'audio_generation', 'name': 'Audio Generation Points', 'icon': '🎵', 'priority': 2, 'production_10x': True},
            {'id': 'text_generation', 'name': 'Text Generation Points', 'icon': '📝', 'priority': 2},
            {'id': 'template_usage', 'name': 'Template Usage Points', 'icon': '📋', 'priority': 2},
            {'id': 'custom_creation', 'name': 'Custom Creation Points', 'icon': '🎨', 'priority': 2},
            {'id': 'quality', 'name': 'Quality Points', 'icon': '💎', 'priority': 2},
            {'id': 'innovation', 'name': 'Innovation Points', 'icon': '💡', 'priority': 2},
            {'id': 'trending', 'name': 'Trending Points', 'icon': '📈', 'priority': 2},
            {'id': 'viral', 'name': 'Viral Points', 'icon': '🔥', 'priority': 2},
            {'id': 'collaboration', 'name': 'Collaboration Points', 'icon': '🤝', 'priority': 2},
            {'id': 'remix', 'name': 'Remix Points', 'icon': '🔄', 'priority': 2},
            {'id': 'edit', 'name': 'Edit Points', 'icon': '✏️', 'priority': 2},
            {'id': 'publish', 'name': 'Publish Points', 'icon': '📢', 'priority': 2},
            {'id': 'schedule', 'name': 'Schedule Points', 'icon': '📅', 'priority': 2},
            {'id': 'series', 'name': 'Series Points', 'icon': '📺', 'priority': 2},
            {'id': 'playlist', 'name': 'Playlist Points', 'icon': '🎵', 'priority': 2},
            {'id': 'collection', 'name': 'Collection Points', 'icon': '📦', 'priority': 2},
            {'id': 'production_mastery', 'name': 'Production Mastery Points', 'icon': '🏭', 'priority': 1, 'production_10x': True},
        ]
    },
    
    # Category 4: Social & Community (20 Systems)
    'social_community': {
        'category': 'Social & Community',
        'icon': '👥',
        'color': '#3498DB',
        'systems': [
            {'id': 'friend', 'name': 'Friend Points', 'icon': '👫', 'priority': 2},
            {'id': 'follow', 'name': 'Follow Points', 'icon': '➕', 'priority': 2},
            {'id': 'follower', 'name': 'Follower Points', 'icon': '👤', 'priority': 2},
            {'id': 'message', 'name': 'Message Points', 'icon': '💬', 'priority': 2},
            {'id': 'group', 'name': 'Group Points', 'icon': '👥', 'priority': 2},
            {'id': 'community', 'name': 'Community Points', 'icon': '🌐', 'priority': 2},
            {'id': 'event', 'name': 'Event Points', 'icon': '🎉', 'priority': 2},
            {'id': 'meetup', 'name': 'Meetup Points', 'icon': '🤝', 'priority': 2},
            {'id': 'discussion', 'name': 'Discussion Points', 'icon': '💭', 'priority': 2},
            {'id': 'forum', 'name': 'Forum Points', 'icon': '📋', 'priority': 2},
            {'id': 'help', 'name': 'Help Points', 'icon': '🆘', 'priority': 2},
            {'id': 'mentor', 'name': 'Mentor Points', 'icon': '🎓', 'priority': 2},
            {'id': 'apprentice', 'name': 'Apprentice Points', 'icon': '📚', 'priority': 2},
            {'id': 'referral', 'name': 'Referral Points', 'icon': '🔗', 'priority': 2},
            {'id': 'invite', 'name': 'Invite Points', 'icon': '📨', 'priority': 2},
            {'id': 'gift', 'name': 'Gift Points', 'icon': '🎁', 'priority': 2},
            {'id': 'thank_you', 'name': 'Thank You Points', 'icon': '🙏', 'priority': 2},
            {'id': 'recognition', 'name': 'Recognition Points', 'icon': '👏', 'priority': 2},
            {'id': 'celebration', 'name': 'Celebration Points', 'icon': '🎊', 'priority': 2},
            {'id': 'community_mastery', 'name': 'Community Mastery Points', 'icon': '🌟', 'priority': 2},
        ]
    },
    
    # Category 5: Progression & Leveling (15 Systems)
    'progression_leveling': {
        'category': 'Progression & Leveling',
        'icon': '📈',
        'color': '#9B59B6',
        'systems': [
            {'id': 'level_up', 'name': 'Level Up Points', 'icon': '⬆️', 'priority': 2},
            {'id': 'skill', 'name': 'Skill Points', 'icon': '🎯', 'priority': 2, 'teleport_skillset': True},
            {'id': 'mastery', 'name': 'Mastery Points', 'icon': '🏆', 'priority': 2},
            {'id': 'prestige', 'name': 'Prestige Points', 'icon': '👑', 'priority': 2},
            {'id': 'rank', 'name': 'Rank Points', 'icon': '📊', 'priority': 2},
            {'id': 'tier', 'name': 'Tier Points', 'icon': '🎖️', 'priority': 2},
            {'id': 'badge', 'name': 'Badge Points', 'icon': '🏅', 'priority': 2},
            {'id': 'medal', 'name': 'Medal Points', 'icon': '🥇', 'priority': 2},
            {'id': 'title', 'name': 'Title Points', 'icon': '📜', 'priority': 2},
            {'id': 'achievement_chain', 'name': 'Achievement Chain Points', 'icon': '🔗', 'priority': 2},
            {'id': 'milestone', 'name': 'Milestone Points', 'icon': '🎯', 'priority': 2},
            {'id': 'progress', 'name': 'Progress Points', 'icon': '📈', 'priority': 2},
            {'id': 'completion', 'name': 'Completion Points', 'icon': '✅', 'priority': 2},
            {'id': 'teleport_skillset', 'name': 'Teleport Skillset Points', 'icon': '🌀', 'priority': 1, 'teleport_skillset': True},
            {'id': 'death_portal_mastery', 'name': 'Death Portal Mastery Points', 'icon': '💀', 'priority': 1, 'death_portal_multiplier': True},
        ]
    },
    
    # Category 6: Economy & Trading (15 Systems)
    'economy_trading': {
        'category': 'Economy & Trading',
        'icon': '💰',
        'color': '#27AE60',
        'systems': [
            {'id': 'purchase', 'name': 'Purchase Points', 'icon': '🛒', 'priority': 2},
            {'id': 'sale', 'name': 'Sale Points', 'icon': '💵', 'priority': 2},
            {'id': 'trade', 'name': 'Trade Points', 'icon': '🤝', 'priority': 2},
            {'id': 'auction', 'name': 'Auction Points', 'icon': '🔨', 'priority': 2},
            {'id': 'market', 'name': 'Market Points', 'icon': '📊', 'priority': 2},
            {'id': 'currency', 'name': 'Currency Points', 'icon': '💱', 'priority': 2},
            {'id': 'investment', 'name': 'Investment Points', 'icon': '📈', 'priority': 2},
            {'id': 'profit', 'name': 'Profit Points', 'icon': '💎', 'priority': 2},
            {'id': 'deal', 'name': 'Deal Points', 'icon': '🤝', 'priority': 2},
            {'id': 'negotiation', 'name': 'Negotiation Points', 'icon': '💼', 'priority': 2},
            {'id': 'collection_value', 'name': 'Collection Value Points', 'icon': '📦', 'priority': 2},
            {'id': 'asset', 'name': 'Asset Points', 'icon': '🏦', 'priority': 2},
            {'id': 'wealth', 'name': 'Wealth Points', 'icon': '💰', 'priority': 2},
            {'id': 'production_economy', 'name': 'Production Economy Points', 'icon': '🏭', 'priority': 1, 'production_10x': True},
            {'id': 'teleport_trade', 'name': 'Teleport Trade Points', 'icon': '🌀', 'priority': 1, 'teleport_skillset': True},
        ]
    },
    
    # Category 7: Exploration & Discovery (12 Systems)
    'exploration_discovery': {
        'category': 'Exploration & Discovery',
        'icon': '🗺️',
        'color': '#16A085',
        'systems': [
            {'id': 'exploration', 'name': 'Exploration Points', 'icon': '🗺️', 'priority': 3},
            {'id': 'discovery', 'name': 'Discovery Points', 'icon': '🔍', 'priority': 3},
            {'id': 'unlock', 'name': 'Unlock Points', 'icon': '🔓', 'priority': 3},
            {'id': 'reveal', 'name': 'Reveal Points', 'icon': '👁️', 'priority': 3},
            {'id': 'map', 'name': 'Map Points', 'icon': '🗺️', 'priority': 3},
            {'id': 'location', 'name': 'Location Points', 'icon': '📍', 'priority': 3},
            {'id': 'hidden', 'name': 'Hidden Points', 'icon': '👻', 'priority': 3},
            {'id': 'secret', 'name': 'Secret Points', 'icon': '🔐', 'priority': 3},
            {'id': 'easter_egg', 'name': 'Easter Egg Points', 'icon': '🥚', 'priority': 3},
            {'id': 'landmark', 'name': 'Landmark Points', 'icon': '🏛️', 'priority': 3},
            {'id': 'path', 'name': 'Path Points', 'icon': '🛤️', 'priority': 3},
            {'id': 'route', 'name': 'Route Points', 'icon': '🛣️', 'priority': 3},
        ]
    },
    
    # Category 8: Learning & Education (12 Systems)
    'learning_education': {
        'category': 'Learning & Education',
        'icon': '📚',
        'color': '#E67E22',
        'systems': [
            {'id': 'learning', 'name': 'Learning Points', 'icon': '📚', 'priority': 3},
            {'id': 'course', 'name': 'Course Points', 'icon': '📖', 'priority': 3},
            {'id': 'lesson', 'name': 'Lesson Points', 'icon': '📝', 'priority': 3},
            {'id': 'quiz', 'name': 'Quiz Points', 'icon': '❓', 'priority': 3},
            {'id': 'test', 'name': 'Test Points', 'icon': '📋', 'priority': 3},
            {'id': 'certification', 'name': 'Certification Points', 'icon': '🎓', 'priority': 3},
            {'id': 'knowledge', 'name': 'Knowledge Points', 'icon': '🧠', 'priority': 3},
            {'id': 'skill_development', 'name': 'Skill Development Points', 'icon': '🎯', 'priority': 3, 'teleport_skillset': True},
            {'id': 'practice', 'name': 'Practice Points', 'icon': '🏋️', 'priority': 3},
            {'id': 'study', 'name': 'Study Points', 'icon': '📚', 'priority': 3},
            {'id': 'research', 'name': 'Research Points', 'icon': '🔬', 'priority': 3},
            {'id': 'education', 'name': 'Education Points', 'icon': '🎓', 'priority': 3},
        ]
    },
    
    # Category 9: Events & Special Occasions (10 Systems)
    'events_special': {
        'category': 'Events & Special Occasions',
        'icon': '🎉',
        'color': '#F39C12',
        'systems': [
            {'id': 'event_participation', 'name': 'Event Participation Points', 'icon': '🎉', 'priority': 3},
            {'id': 'holiday', 'name': 'Holiday Points', 'icon': '🎄', 'priority': 3},
            {'id': 'seasonal', 'name': 'Seasonal Points', 'icon': '🍂', 'priority': 3},
            {'id': 'limited_time', 'name': 'Limited Time Points', 'icon': '⏰', 'priority': 3},
            {'id': 'special_event', 'name': 'Special Event Points', 'icon': '🎊', 'priority': 3},
            {'id': 'anniversary', 'name': 'Anniversary Points', 'icon': '🎂', 'priority': 3},
            {'id': 'celebration', 'name': 'Celebration Points', 'icon': '🎈', 'priority': 3},
            {'id': 'festival', 'name': 'Festival Points', 'icon': '🎪', 'priority': 3},
            {'id': 'competition', 'name': 'Competition Points', 'icon': '🏆', 'priority': 3},
            {'id': 'death_portal_event', 'name': 'Death Portal Event Points', 'icon': '💀', 'priority': 1, 'death_portal_multiplier': True},
        ]
    },
    
    # Category 10: Customization & Personalization (10 Systems)
    'customization_personalization': {
        'category': 'Customization & Personalization',
        'icon': '🎨',
        'color': '#FF6B9D',
        'systems': [
            {'id': 'customization', 'name': 'Customization Points', 'icon': '🎨', 'priority': 3},
            {'id': 'avatar', 'name': 'Avatar Points', 'icon': '👤', 'priority': 3},
            {'id': 'theme_custom', 'name': 'Theme Customization Points', 'icon': '🎨', 'priority': 3},
            {'id': 'layout', 'name': 'Layout Points', 'icon': '📐', 'priority': 3},
            {'id': 'style', 'name': 'Style Points', 'icon': '💅', 'priority': 3},
            {'id': 'personalization', 'name': 'Personalization Points', 'icon': '✨', 'priority': 3},
            {'id': 'preference', 'name': 'Preference Points', 'icon': '⚙️', 'priority': 3},
            {'id': 'settings', 'name': 'Settings Points', 'icon': '🔧', 'priority': 3},
            {'id': 'design', 'name': 'Design Points', 'icon': '🎨', 'priority': 3},
            {'id': 'aesthetic', 'name': 'Aesthetic Points', 'icon': '✨', 'priority': 3},
        ]
    },
    
    # Category 11: Innovation & Creativity (8 Systems)
    'innovation_creativity': {
        'category': 'Innovation & Creativity',
        'icon': '💡',
        'color': '#9B59B6',
        'systems': [
            {'id': 'innovation', 'name': 'Innovation Points', 'icon': '💡', 'priority': 3},
            {'id': 'creativity', 'name': 'Creativity Points', 'icon': '🎨', 'priority': 3},
            {'id': 'experiment', 'name': 'Experiment Points', 'icon': '🧪', 'priority': 3},
            {'id': 'invention', 'name': 'Invention Points', 'icon': '🔧', 'priority': 3},
            {'id': 'design_creative', 'name': 'Design Points', 'icon': '✏️', 'priority': 3},
            {'id': 'artistic', 'name': 'Artistic Points', 'icon': '🖼️', 'priority': 3},
            {'id': 'originality', 'name': 'Originality Points', 'icon': '✨', 'priority': 3},
            {'id': 'uniqueness', 'name': 'Uniqueness Points', 'icon': '🌟', 'priority': 3},
        ]
    },
    
    # Category 12: Meta & System (8 Systems)
    'meta_system': {
        'category': 'Meta & System',
        'icon': '⚙️',
        'color': '#95A5A6',
        'systems': [
            {'id': 'system', 'name': 'System Points', 'icon': '⚙️', 'priority': 3},
            {'id': 'meta', 'name': 'Meta Points', 'icon': '🌀', 'priority': 3},
            {'id': 'feedback', 'name': 'Feedback Points', 'icon': '💬', 'priority': 3},
            {'id': 'bug_report', 'name': 'Bug Report Points', 'icon': '🐛', 'priority': 3},
            {'id': 'feature_request', 'name': 'Feature Request Points', 'icon': '💡', 'priority': 3},
            {'id': 'beta_test', 'name': 'Beta Test Points', 'icon': '🧪', 'priority': 3},
            {'id': 'quality_assurance', 'name': 'Quality Assurance Points', 'icon': '✅', 'priority': 3},
            {'id': 'system_contribution', 'name': 'System Contribution Points', 'icon': '🤝', 'priority': 3},
        ]
    },
}

def generate_all_systems():
    """Generate all 178 point systems"""
    all_systems = []
    system_count = 0
    
    for category_key, category_data in ALL_178_SYSTEMS.items():
        for system in category_data['systems']:
            system_count += 1
            system_data = {
                'id': system['id'],
                'number': system_count,
                'name': system['name'],
                'icon': system['icon'],
                'category': category_data['category'],
                'category_icon': category_data['icon'],
                'color': category_data['color'],
                'priority': system.get('priority', 3),
                'death_portal_multiplier': system.get('death_portal_multiplier', False),
                'production_10x': system.get('production_10x', False),
                'teleport_skillset': system.get('teleport_skillset', False),
            }
            all_systems.append(system_data)
    
    return all_systems

def generate_point_values():
    """Generate point values for all 178 systems"""
    point_values = {}
    
    # Base point values by category
    base_values = {
        'core_engagement': 1,
        'battle_combat': 20,
        'content_creation': 50,
        'social_community': 15,
        'progression_leveling': 100,
        'economy_trading': 25,
        'exploration_discovery': 30,
        'learning_education': 40,
        'events_special': 50,
        'customization_personalization': 10,
        'innovation_creativity': 75,
        'meta_system': 20,
    }
    
    for category_key, category_data in ALL_178_SYSTEMS.items():
        base_value = base_values.get(category_key, 10)
        
        for system in category_data['systems']:
            system_id = system['id']
            
            # Calculate point value
            value = base_value
            
            # Apply multipliers
            if system.get('death_portal_multiplier'):
                value = int(value * DEATH_PORTAL_MULTIPLIER)
            
            if system.get('production_10x'):
                value = int(value * 10)
            
            if system.get('teleport_skillset'):
                value = int(value * TELEPORT_SKILLSET_BONUS)
            
            # Priority adjustment
            priority = system.get('priority', 3)
            if priority == 1:
                value = int(value * 1.5)
            elif priority == 2:
                value = int(value * 1.2)
            
            point_values[system_id] = value
    
    return point_values

def generate_control_board_config():
    """Generate control board configuration for all systems"""
    all_systems = generate_all_systems()
    
    config = {
        'total_systems': len(all_systems),
        'categories': {},
        'systems': {}
    }
    
    for system in all_systems:
        category = system['category']
        
        if category not in config['categories']:
            config['categories'][category] = {
                'name': category,
                'systems': []
            }
        
        config['categories'][category]['systems'].append(system['id'])
        config['systems'][system['id']] = system
    
    return config

def generate_calculator_updates():
    """Generate calculator code updates for all 178 systems"""
    all_systems = generate_all_systems()
    point_values = generate_point_values()
    
    # Generate base_points dictionary
    base_points_code = "        base_points = {\n"
    for system in all_systems:
        system_id = system['id']
        field_name = f"{system_id}_points"
        base_points_code += f"            '{field_name}': 0,\n"
    base_points_code += "        }\n"
    
    # Generate calculation code
    calculation_code = ""
    for system in all_systems:
        system_id = system['id']
        field_name = f"{system_id}_points"
        data_key = system_id.replace('_', '_')
        
        calculation_code += f"        # {system['name']}\n"
        calculation_code += f"        base_points['{field_name}'] = point_data.get('{data_key}', 0) * {point_values[system_id]}\n"
    
    return {
        'base_points_dict': base_points_code,
        'calculation_code': calculation_code,
        'point_values': point_values
    }

if __name__ == '__main__':
    print("=" * 80)
    print("GENERATING 178 POINT SYSTEMS")
    print("=" * 80)
    print()
    
    # Generate all systems
    all_systems = generate_all_systems()
    print(f"[OK] Generated {len(all_systems)} point systems")
    
    # Generate point values
    point_values = generate_point_values()
    print(f"[OK] Generated point values for {len(point_values)} systems")
    
    # Generate control board config
    config = generate_control_board_config()
    print(f"[OK] Generated control board config with {len(config['categories'])} categories")
    
    # Generate calculator updates
    calculator_updates = generate_calculator_updates()
    print(f"[OK] Generated calculator code updates")
    
    # Save to files
    with open('178_systems_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("[OK] Saved config to 178_systems_config.json")
    
    with open('178_systems_point_values.json', 'w', encoding='utf-8') as f:
        json.dump(point_values, f, indent=2, ensure_ascii=False)
    print("[OK] Saved point values to 178_systems_point_values.json")
    
    with open('178_systems_calculator_code.py', 'w', encoding='utf-8') as f:
        f.write("# Generated Calculator Code for 178 Systems\n\n")
        f.write("BASE_POINTS_DICT = {\n")
        for system in all_systems:
            f.write(f"    '{system['id']}_points': 0,\n")
        f.write("}\n\n")
        f.write("# Point Values\n")
        f.write("POINT_VALUES = {\n")
        for system_id, value in point_values.items():
            f.write(f"    '{system_id}': {value},\n")
        f.write("}\n")
    print("[OK] Saved calculator code to 178_systems_calculator_code.py")
    
    print()
    print("=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Total Systems: {len(all_systems)}")
    print(f"Categories: {len(config['categories'])}")
    print(f"Death Portal Systems: {sum(1 for s in all_systems if s.get('death_portal_multiplier'))}")
    print(f"10x Production Systems: {sum(1 for s in all_systems if s.get('production_10x'))}")
    print(f"Teleport Skillset Systems: {sum(1 for s in all_systems if s.get('teleport_skillset'))}")

