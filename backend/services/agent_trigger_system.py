"""
Agent Trigger System
Triggers that award points to unified points system
"""
import os
import json
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentTriggerSystem:
    """Trigger system that awards points to unified points system"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.triggers_file = os.path.join(self.base_dir, 'logs', 'agent_triggers', 'triggers.json')
        self.load_triggers()
    
    def load_triggers(self):
        """Load triggers"""
        os.makedirs(os.path.dirname(self.triggers_file), exist_ok=True)
        if os.path.exists(self.triggers_file):
            try:
                with open(self.triggers_file, 'r') as f:
                    self.triggers = json.load(f)
            except:
                self.triggers = self._default_triggers()
        else:
            self.triggers = self._default_triggers()
            self.save_triggers()
    
    def _default_triggers(self) -> Dict:
        """Default triggers"""
        return {
            'triggers': [
                {
                    'id': 'skill_execution',
                    'name': 'Skill Execution',
                    'type': 'skill',
                    'condition': 'skill_executed',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'mission_completed',
                    'name': 'Mission Completed',
                    'type': 'mission',
                    'condition': 'mission_completed',
                    'points': {
                        'xp': 50,
                        'generation_points': 25,
                        'battle_points': 10
                    },
                    'enabled': True
                },
                {
                    'id': 'quest_completed',
                    'name': 'Quest Completed',
                    'type': 'quest',
                    'condition': 'quest_completed',
                    'points': {
                        'xp': 100,
                        'generation_points': 50,
                        'battle_points': 25
                    },
                    'enabled': True
                },
                {
                    'id': 'research_completed',
                    'name': 'Research Completed',
                    'type': 'research',
                    'condition': 'research_completed',
                    'points': {
                        'xp': 75,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'python_execution',
                    'name': 'Python Execution',
                    'type': 'execution',
                    'condition': 'python_executed',
                    'points': {
                        'xp': 10,
                        'generation_points': 5,
                        'battle_points': 2
                    },
                    'enabled': True
                },
                {
                    'id': 'health_check',
                    'name': 'Health Check',
                    'type': 'monitoring',
                    'condition': 'health_check_completed',
                    'points': {
                        'xp': 3,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'issue_resolved',
                    'name': 'Issue Resolved',
                    'type': 'support',
                    'condition': 'issue_resolved',
                    'points': {
                        'xp': 30,
                        'generation_points': 15,
                        'battle_points': 8
                    },
                    'enabled': True
                },
                {
                    'id': 'automation_task',
                    'name': 'Automation Task',
                    'type': 'automation',
                    'condition': 'automation_task_completed',
                    'points': {
                        'xp': 2,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                # Unified Points System Triggers
                {
                    'id': 'video_generation',
                    'name': 'Video Generation',
                    'type': 'generation',
                    'condition': 'video_generated',
                    'points': {
                        'xp': 600,
                        'generation_points': 300,
                        'battle_points': 150
                    },
                    'enabled': True
                },
                {
                    'id': 'clip_generation',
                    'name': 'Clip Generation',
                    'type': 'generation',
                    'condition': 'clip_generated',
                    'points': {
                        'xp': 600,
                        'generation_points': 300,
                        'battle_points': 150
                    },
                    'enabled': True
                },
                {
                    'id': 'image_generation',
                    'name': 'Image Generation',
                    'type': 'generation',
                    'condition': 'image_generated',
                    'points': {
                        'xp': 600,
                        'generation_points': 300,
                        'battle_points': 150
                    },
                    'enabled': True
                },
                {
                    'id': 'audio_generation',
                    'name': 'Audio Generation',
                    'type': 'generation',
                    'condition': 'audio_generated',
                    'points': {
                        'xp': 600,
                        'generation_points': 300,
                        'battle_points': 150
                    },
                    'enabled': True
                },
                # DNA Tech Triggers (New)
                {
                    'id': 'dna_manipulation',
                    'name': 'DNA Manipulation',
                    'type': 'research',
                    'condition': 'dna_manipulation_completed',
                    'points': {
                        'xp': 180,
                        'knowledge_points': 40,
                        'dna_manipulation_points': 25
                    },
                    'enabled': True
                },
                {
                    'id': 'dna_cloning',
                    'name': 'DNA Cloning',
                    'type': 'research',
                    'condition': 'dna_cloning_completed',
                    'points': {
                        'xp': 220,
                        'knowledge_points': 55,
                        'dna_cloning_points': 30
                    },
                    'enabled': True
                },
                {
                    'id': 'pvp_battle',
                    'name': 'PvP Battle',
                    'type': 'battle',
                    'condition': 'pvp_battle_completed',
                    'points': {
                        'xp': 240,
                        'generation_points': 120,
                        'battle_points': 240
                    },
                    'enabled': True
                },
                {
                    'id': 'pve_battle',
                    'name': 'PvE Battle',
                    'type': 'battle',
                    'condition': 'pve_battle_completed',
                    'points': {
                        'xp': 240,
                        'generation_points': 120,
                        'battle_points': 240
                    },
                    'enabled': True
                },
                {
                    'id': 'battle_victory',
                    'name': 'Battle Victory',
                    'type': 'battle',
                    'condition': 'battle_victory',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'social_action',
                    'name': 'Social Action',
                    'type': 'social',
                    'condition': 'social_action_completed',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'achievement_unlocked',
                    'name': 'Achievement Unlocked',
                    'type': 'achievement',
                    'condition': 'achievement_unlocked',
                    'points': {
                        'xp': 50,
                        'generation_points': 25,
                        'battle_points': 12
                    },
                    'enabled': True
                },
                {
                    'id': 'trophy_earned',
                    'name': 'Trophy Earned',
                    'type': 'trophy',
                    'condition': 'trophy_earned',
                    'points': {
                        'xp': 30,
                        'generation_points': 15,
                        'battle_points': 8
                    },
                    'enabled': True
                },
                {
                    'id': 'daily_activity',
                    'name': 'Daily Activity',
                    'type': 'activity',
                    'condition': 'daily_activity_completed',
                    'points': {
                        'xp': 10,
                        'generation_points': 5,
                        'battle_points': 2
                    },
                    'enabled': True
                },
                {
                    'id': 'content_consumption',
                    'name': 'Content Consumption',
                    'type': 'engagement',
                    'condition': 'content_consumed',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'interaction_quality',
                    'name': 'Quality Interaction',
                    'type': 'engagement',
                    'condition': 'quality_interaction',
                    'points': {
                        'xp': 8,
                        'generation_points': 4,
                        'battle_points': 2
                    },
                    'enabled': True
                },
                {
                    'id': 'production_mastery',
                    'name': 'Production Mastery',
                    'type': 'mastery',
                    'condition': 'production_mastery',
                    'points': {
                        'xp': 750,
                        'generation_points': 375,
                        'battle_points': 188
                    },
                    'enabled': True
                },
                {
                    'id': 'skillset_mastery',
                    'name': 'Skillset Mastery',
                    'type': 'mastery',
                    'condition': 'skillset_mastery',
                    'points': {
                        'xp': 45,
                        'generation_points': 22,
                        'battle_points': 11
                    },
                    'enabled': True
                },
                {
                    'id': 'watch_time',
                    'name': 'Watch Time',
                    'type': 'engagement',
                    'condition': 'watch_time_accumulated',
                    'points': {
                        'xp': 12,
                        'generation_points': 6,
                        'battle_points': 3
                    },
                    'enabled': True
                },
                {
                    'id': 'share_content',
                    'name': 'Share Content',
                    'type': 'social',
                    'condition': 'content_shared',
                    'points': {
                        'xp': 15,
                        'generation_points': 7,
                        'battle_points': 4
                    },
                    'enabled': True
                },
                {
                    'id': 'comment_posted',
                    'name': 'Comment Posted',
                    'type': 'social',
                    'condition': 'comment_posted',
                    'points': {
                        'xp': 8,
                        'generation_points': 4,
                        'battle_points': 2
                    },
                    'enabled': True
                },
                {
                    'id': 'rating_given',
                    'name': 'Rating Given',
                    'type': 'engagement',
                    'condition': 'rating_given',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'template_used',
                    'name': 'Template Used',
                    'type': 'generation',
                    'condition': 'template_used',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'custom_creation',
                    'name': 'Custom Creation',
                    'type': 'generation',
                    'condition': 'custom_created',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'quality_content',
                    'name': 'Quality Content',
                    'type': 'generation',
                    'condition': 'quality_content_created',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'innovation',
                    'name': 'Innovation',
                    'type': 'generation',
                    'condition': 'innovation_created',
                    'points': {
                        'xp': 75,
                        'generation_points': 37,
                        'battle_points': 19
                    },
                    'enabled': True
                },
                {
                    'id': 'trending_content',
                    'name': 'Trending Content',
                    'type': 'generation',
                    'condition': 'trending_content',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'viral_content',
                    'name': 'Viral Content',
                    'type': 'generation',
                    'condition': 'viral_content',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'collaboration',
                    'name': 'Collaboration',
                    'type': 'social',
                    'condition': 'collaboration_completed',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'guild_activity',
                    'name': 'Guild Activity',
                    'type': 'social',
                    'condition': 'guild_activity',
                    'points': {
                        'xp': 20,
                        'generation_points': 10,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'champions_league',
                    'name': 'Champions League',
                    'type': 'competition',
                    'condition': 'champions_league_participation',
                    'points': {
                        'xp': 100,
                        'generation_points': 50,
                        'battle_points': 25
                    },
                    'enabled': True
                },
                {
                    'id': 'tournament',
                    'name': 'Tournament',
                    'type': 'competition',
                    'condition': 'tournament_participation',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'level_up',
                    'name': 'Level Up',
                    'type': 'progression',
                    'condition': 'level_up',
                    'points': {
                        'xp': 0,  # Already awarded XP
                        'generation_points': 50,
                        'battle_points': 25
                    },
                    'enabled': True
                },
                {
                    'id': 'prestige',
                    'name': 'Prestige',
                    'type': 'progression',
                    'condition': 'prestige_achieved',
                    'points': {
                        'xp': 500,
                        'generation_points': 250,
                        'battle_points': 125
                    },
                    'enabled': True
                },
                {
                    'id': 'daily_login',
                    'name': 'Daily Login',
                    'type': 'activity',
                    'condition': 'daily_login',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'streak',
                    'name': 'Streak',
                    'type': 'activity',
                    'condition': 'streak_maintained',
                    'points': {
                        'xp': 10,
                        'generation_points': 5,
                        'battle_points': 2
                    },
                    'enabled': True
                },
                {
                    'id': 'return_visitor',
                    'name': 'Return Visitor',
                    'type': 'engagement',
                    'condition': 'return_visitor',
                    'points': {
                        'xp': 3,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'session_duration',
                    'name': 'Session Duration',
                    'type': 'engagement',
                    'condition': 'long_session',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'page_depth',
                    'name': 'Page Depth',
                    'type': 'engagement',
                    'condition': 'deep_navigation',
                    'points': {
                        'xp': 3,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'search_performed',
                    'name': 'Search Performed',
                    'type': 'engagement',
                    'condition': 'search_performed',
                    'points': {
                        'xp': 2,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'filter_used',
                    'name': 'Filter Used',
                    'type': 'engagement',
                    'condition': 'filter_used',
                    'points': {
                        'xp': 2,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'bookmark_created',
                    'name': 'Bookmark Created',
                    'type': 'engagement',
                    'condition': 'bookmark_created',
                    'points': {
                        'xp': 3,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'scroll_depth',
                    'name': 'Scroll Depth',
                    'type': 'engagement',
                    'condition': 'deep_scroll',
                    'points': {
                        'xp': 2,
                        'generation_points': 1,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'friend_added',
                    'name': 'Friend Added',
                    'type': 'social',
                    'condition': 'friend_added',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'follow',
                    'name': 'Follow',
                    'type': 'social',
                    'condition': 'follow_created',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'follower_gained',
                    'name': 'Follower Gained',
                    'type': 'social',
                    'condition': 'follower_gained',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'message_sent',
                    'name': 'Message Sent',
                    'type': 'social',
                    'condition': 'message_sent',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'group_joined',
                    'name': 'Group Joined',
                    'type': 'social',
                    'condition': 'group_joined',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'community_activity',
                    'name': 'Community Activity',
                    'type': 'social',
                    'condition': 'community_activity',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'event_participation',
                    'name': 'Event Participation',
                    'type': 'social',
                    'condition': 'event_participated',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'meetup',
                    'name': 'Meetup',
                    'type': 'social',
                    'condition': 'meetup_attended',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'discussion',
                    'name': 'Discussion',
                    'type': 'social',
                    'condition': 'discussion_participated',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'forum_post',
                    'name': 'Forum Post',
                    'type': 'social',
                    'condition': 'forum_posted',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'help_provided',
                    'name': 'Help Provided',
                    'type': 'social',
                    'condition': 'help_provided',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'mentor',
                    'name': 'Mentor',
                    'type': 'social',
                    'condition': 'mentor_activity',
                    'points': {
                        'xp': 18,
                        'generation_points': 9,
                        'battle_points': 5
                    },
                    'enabled': True
                },
                {
                    'id': 'team_battle',
                    'name': 'Team Battle',
                    'type': 'battle',
                    'condition': 'team_battle_completed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'guild_battle',
                    'name': 'Guild Battle',
                    'type': 'battle',
                    'condition': 'guild_battle_completed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'arena_battle',
                    'name': 'Arena Battle',
                    'type': 'battle',
                    'condition': 'arena_battle_completed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'ranked_battle',
                    'name': 'Ranked Battle',
                    'type': 'battle',
                    'condition': 'ranked_battle_completed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'casual_battle',
                    'name': 'Casual Battle',
                    'type': 'battle',
                    'condition': 'casual_battle_completed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'perfect_victory',
                    'name': 'Perfect Victory',
                    'type': 'battle',
                    'condition': 'perfect_victory',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'comeback',
                    'name': 'Comeback',
                    'type': 'battle',
                    'condition': 'comeback_achieved',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'streak_battle',
                    'name': 'Battle Streak',
                    'type': 'battle',
                    'condition': 'battle_streak',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'first_blood',
                    'name': 'First Blood',
                    'type': 'battle',
                    'condition': 'first_blood',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'multi_kill',
                    'name': 'Multi Kill',
                    'type': 'battle',
                    'condition': 'multi_kill',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'assist',
                    'name': 'Assist',
                    'type': 'battle',
                    'condition': 'assist_given',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'defense',
                    'name': 'Defense',
                    'type': 'battle',
                    'condition': 'defense_performed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'offense',
                    'name': 'Offense',
                    'type': 'battle',
                    'condition': 'offense_performed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'tactical',
                    'name': 'Tactical',
                    'type': 'battle',
                    'condition': 'tactical_move',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'strategy',
                    'name': 'Strategy',
                    'type': 'battle',
                    'condition': 'strategy_used',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'combo',
                    'name': 'Combo',
                    'type': 'battle',
                    'condition': 'combo_executed',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'ultimate',
                    'name': 'Ultimate',
                    'type': 'battle',
                    'condition': 'ultimate_used',
                    'points': {
                        'xp': 24,
                        'generation_points': 12,
                        'battle_points': 24
                    },
                    'enabled': True
                },
                {
                    'id': 'death_portal_teleport',
                    'name': 'Death Portal Teleport',
                    'type': 'special',
                    'condition': 'death_portal_teleport',
                    'points': {
                        'xp': 450,
                        'generation_points': 225,
                        'battle_points': 113
                    },
                    'enabled': True
                },
                {
                    'id': 'production_10x',
                    'name': 'Production 10x',
                    'type': 'special',
                    'condition': 'production_10x',
                    'points': {
                        'xp': 3000,
                        'generation_points': 1500,
                        'battle_points': 750
                    },
                    'enabled': True
                },
                {
                    'id': 'text_generation',
                    'name': 'Text Generation',
                    'type': 'generation',
                    'condition': 'text_generated',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'remix',
                    'name': 'Remix',
                    'type': 'generation',
                    'condition': 'content_remixed',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'edit',
                    'name': 'Edit',
                    'type': 'generation',
                    'condition': 'content_edited',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'publish',
                    'name': 'Publish',
                    'type': 'generation',
                    'condition': 'content_published',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'schedule',
                    'name': 'Schedule',
                    'type': 'generation',
                    'condition': 'content_scheduled',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'series',
                    'name': 'Series',
                    'type': 'generation',
                    'condition': 'series_created',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'playlist',
                    'name': 'Playlist',
                    'type': 'generation',
                    'condition': 'playlist_created',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'collection',
                    'name': 'Collection',
                    'type': 'generation',
                    'condition': 'collection_created',
                    'points': {
                        'xp': 60,
                        'generation_points': 30,
                        'battle_points': 15
                    },
                    'enabled': True
                },
                {
                    'id': 'theme_points',
                    'name': 'Theme Points',
                    'type': 'activity',
                    'condition': 'theme_points_earned',
                    'points': {
                        'xp': 1,
                        'generation_points': 1,
                        'battle_points': 0
                    },
                    'enabled': True
                },
                {
                    'id': 'chat_points',
                    'name': 'Chat Points',
                    'type': 'activity',
                    'condition': 'chat_activity',
                    'points': {
                        'xp': 1,
                        'generation_points': 1,
                        'battle_points': 0
                    },
                    'enabled': True
                },
                {
                    'id': 'metal_points',
                    'name': 'Metal Points',
                    'type': 'activity',
                    'condition': 'metal_activity',
                    'points': {
                        'xp': 1,
                        'generation_points': 1,
                        'battle_points': 0
                    },
                    'enabled': True
                },
                {
                    'id': 'graduation',
                    'name': 'Graduation',
                    'type': 'progression',
                    'condition': 'graduation_achieved',
                    'points': {
                        'xp': 100,
                        'generation_points': 50,
                        'battle_points': 25
                    },
                    'enabled': True
                },
                {
                    'id': 'krimetime',
                    'name': 'Krimetime',
                    'type': 'activity',
                    'condition': 'krimetime_activity',
                    'points': {
                        'xp': 1,
                        'generation_points': 1,
                        'battle_points': 0
                    },
                    'enabled': True
                },
                {
                    'id': 'shop_purchase',
                    'name': 'Shop Purchase',
                    'type': 'activity',
                    'condition': 'shop_purchase',
                    'points': {
                        'xp': 5,
                        'generation_points': 2,
                        'battle_points': 1
                    },
                    'enabled': True
                },
                {
                    'id': 'stats_points',
                    'name': 'Stats Points',
                    'type': 'activity',
                    'condition': 'stats_points_earned',
                    'points': {
                        'xp': 1,
                        'generation_points': 1,
                        'battle_points': 0
                    },
                    'enabled': True
                }
            ],
            'trigger_history': [],
            'points_awarded': {
                'total_xp': 0,
                'total_generation_points': 0,
                'total_battle_points': 0
            }
        }
    
    def save_triggers(self):
        """Save triggers"""
        try:
            with open(self.triggers_file, 'w') as f:
                json.dump(self.triggers, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving triggers: {e}")
    
    def award_points(self, trigger_id: str, user_id: str = 'agent_user', metadata: Dict = None) -> Dict:
        """Award points via trigger"""
        trigger = next((t for t in self.triggers['triggers'] if t.get('id') == trigger_id), None)
        if not trigger:
            return {'success': False, 'error': 'Trigger not found'}
        
        if not trigger.get('enabled', True):
            return {'success': False, 'error': 'Trigger disabled'}
        
        points = trigger.get('points', {})
        
        # Award points to unified points system
        try:
            # Try multiple import paths
            result = None
            try:
                from backend.routes.hunters_game import award_xp
                result = award_xp(user_id, points)
            except ImportError:
                try:
                    # Try alternative import
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
                    from backend.routes.hunters_game import award_xp
                    result = award_xp(user_id, points)
                except:
                    # Fallback: just record the points without database
                    result = {
                        'success': True,
                        'xp_awarded': points.get('xp', 0),
                        'message': 'Points recorded (database not available)'
                    }

            # Also persist any non-core point keys via UnifiedPointsDatabase (e.g. dna_manipulation_points)
            try:
                from backend.services.unified_points_database import unified_points_db
                core_keys = {'xp', 'generation_points', 'battle_points'}
                for k, v in (points or {}).items():
                    if k in core_keys:
                        continue
                    if v is None:
                        continue
                    try:
                        amt = float(v)
                    except Exception:
                        continue
                    if amt == 0:
                        continue
                    unified_points_db.add_points(
                        user_id=user_id,
                        point_type=k,
                        amount=amt,
                        source=f"trigger:{trigger_id}",
                        metadata=metadata or {},
                    )
            except Exception:
                pass
            
            # Record trigger execution
            trigger_record = {
                'trigger_id': trigger_id,
                'trigger_name': trigger['name'],
                'user_id': user_id,
                'points': points,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            self.triggers['trigger_history'].append(trigger_record)
            
            # Update totals
            self.triggers['points_awarded']['total_xp'] += points.get('xp', 0)
            self.triggers['points_awarded']['total_generation_points'] += points.get('generation_points', 0)
            self.triggers['points_awarded']['total_battle_points'] += points.get('battle_points', 0)
            
            # Keep only last 1000 records
            if len(self.triggers['trigger_history']) > 1000:
                self.triggers['trigger_history'] = self.triggers['trigger_history'][-1000:]
            
            self.save_triggers()
            
            return {
                'success': True,
                'trigger': trigger['name'],
                'points_awarded': points,
                'result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'points': points
            }
    
    def create_trigger(self, trigger_data: Dict) -> Dict:
        """Create a new trigger"""
        trigger = {
            'id': trigger_data.get('id', f"trigger_{len(self.triggers['triggers']) + 1}"),
            'name': trigger_data.get('name', 'New Trigger'),
            'type': trigger_data.get('type', 'custom'),
            'condition': trigger_data.get('condition', ''),
            'points': trigger_data.get('points', {}),
            'enabled': trigger_data.get('enabled', True)
        }
        
        self.triggers['triggers'].append(trigger)
        self.save_triggers()
        
        return {
            'success': True,
            'trigger': trigger
        }
    
    def get_trigger_stats(self) -> Dict:
        """Get trigger statistics"""
        enabled_triggers = [t for t in self.triggers['triggers'] if t.get('enabled', True)]
        recent_triggers = self.triggers['trigger_history'][-100:] if len(self.triggers['trigger_history']) > 0 else []
        
        return {
            'success': True,
            'total_triggers': len(self.triggers['triggers']),
            'enabled_triggers': len(enabled_triggers),
            'total_executions': len(self.triggers['trigger_history']),
            'points_awarded': self.triggers['points_awarded'],
            'recent_triggers': recent_triggers
        }

# Global instance
agent_trigger_system = AgentTriggerSystem()
