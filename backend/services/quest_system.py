"""
Quest System - Progression Quests with Levels
- Multi-level quest chains
- Progressive difficulty
- Quest points integration
- Reward integration
- Database persistence
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    unified_points_db = UnifiedPointsDatabase()
except ImportError:
    unified_points_db = None

try:
    from backend.services.point_connection_system import PointConnectionSystem
    point_connection = PointConnectionSystem()
except ImportError:
    point_connection = None

try:
    from backend.services.rewards_system_v2 import rewards_system_v2
except ImportError:
    rewards_system_v2 = None


class QuestSystem:
    """Progression quest system with levels and chains"""
    
    def __init__(self):
        self.quest_templates = self._initialize_quest_templates()
        self.quest_levels = {
            'beginner': {'min_level': 1, 'max_level': 10, 'points_multiplier': 1.0},
            'intermediate': {'min_level': 11, 'max_level': 25, 'points_multiplier': 1.5},
            'advanced': {'min_level': 26, 'max_level': 50, 'points_multiplier': 2.0},
            'expert': {'min_level': 51, 'max_level': 100, 'points_multiplier': 3.0},
            'master': {'min_level': 101, 'max_level': 200, 'points_multiplier': 5.0},
            'legendary': {'min_level': 201, 'max_level': 999, 'points_multiplier': 10.0},
        }
    
    def _initialize_quest_templates(self) -> Dict[str, Dict]:
        """Initialize quest templates"""
        return {
            'video_generation': {
                'name': 'Video Creator',
                'description': 'Create videos to progress',
                'icon': '🎬',
                'objectives': [
                    {'type': 'create_videos', 'target': 1, 'points': 50},
                    {'type': 'create_videos', 'target': 5, 'points': 250},
                    {'type': 'create_videos', 'target': 10, 'points': 500},
                    {'type': 'create_videos', 'target': 25, 'points': 1250},
                    {'type': 'create_videos', 'target': 50, 'points': 2500},
                    {'type': 'create_videos', 'target': 100, 'points': 5000},
                ],
                'rewards': {
                    'points': [50, 250, 500, 1250, 2500, 5000],
                    'xp': [25, 125, 250, 625, 1250, 2500],
                    'stat_points': [0, 1, 2, 5, 10, 20],
                }
            },
            'battle_master': {
                'name': 'Battle Master',
                'description': 'Win battles to become a master',
                'icon': '⚔️',
                'objectives': [
                    {'type': 'win_battles', 'target': 1, 'points': 100},
                    {'type': 'win_battles', 'target': 5, 'points': 500},
                    {'type': 'win_battles', 'target': 10, 'points': 1000},
                    {'type': 'win_battles', 'target': 25, 'points': 2500},
                    {'type': 'win_battles', 'target': 50, 'points': 5000},
                    {'type': 'win_battles', 'target': 100, 'points': 10000},
                ],
                'rewards': {
                    'points': [100, 500, 1000, 2500, 5000, 10000],
                    'xp': [50, 250, 500, 1250, 2500, 5000],
                    'trophies': [0, 1, 2, 5, 10, 20],
                }
            },
            'social_networker': {
                'name': 'Social Networker',
                'description': 'Build your social network',
                'icon': '👥',
                'objectives': [
                    {'type': 'add_friends', 'target': 1, 'points': 25},
                    {'type': 'add_friends', 'target': 5, 'points': 125},
                    {'type': 'add_friends', 'target': 10, 'points': 250},
                    {'type': 'add_friends', 'target': 25, 'points': 625},
                    {'type': 'add_friends', 'target': 50, 'points': 1250},
                    {'type': 'add_friends', 'target': 100, 'points': 2500},
                ],
                'rewards': {
                    'points': [25, 125, 250, 625, 1250, 2500],
                    'xp': [12, 62, 125, 312, 625, 1250],
                }
            },
            'quality_seeker': {
                'name': 'Quality Seeker',
                'description': 'Create high-quality videos',
                'icon': '⭐',
                'objectives': [
                    {'type': 'high_quality_videos', 'target': 1, 'points': 100},
                    {'type': 'high_quality_videos', 'target': 5, 'points': 500},
                    {'type': 'high_quality_videos', 'target': 10, 'points': 1000},
                    {'type': 'high_quality_videos', 'target': 25, 'points': 2500},
                    {'type': 'high_quality_videos', 'target': 50, 'points': 5000},
                ],
                'rewards': {
                    'points': [100, 500, 1000, 2500, 5000],
                    'xp': [50, 250, 500, 1250, 2500],
                    'stat_points': [0, 1, 2, 5, 10],
                }
            },
            'daily_warrior': {
                'name': 'Daily Warrior',
                'description': 'Login daily to maintain your streak',
                'icon': '🔥',
                'objectives': [
                    {'type': 'daily_login', 'target': 3, 'points': 75},
                    {'type': 'daily_login', 'target': 7, 'points': 175},
                    {'type': 'daily_login', 'target': 14, 'points': 350},
                    {'type': 'daily_login', 'target': 30, 'points': 750},
                    {'type': 'daily_login', 'target': 60, 'points': 1500},
                    {'type': 'daily_login', 'target': 100, 'points': 2500},
                ],
                'rewards': {
                    'points': [75, 175, 350, 750, 1500, 2500],
                    'xp': [37, 87, 175, 375, 750, 1250],
                    'coins': [50, 100, 200, 500, 1000, 2000],
                }
            },
            'achievement_hunter': {
                'name': 'Achievement Hunter',
                'description': 'Unlock achievements',
                'icon': '🏆',
                'objectives': [
                    {'type': 'unlock_achievements', 'target': 1, 'points': 50},
                    {'type': 'unlock_achievements', 'target': 5, 'points': 250},
                    {'type': 'unlock_achievements', 'target': 10, 'points': 500},
                    {'type': 'unlock_achievements', 'target': 25, 'points': 1250},
                    {'type': 'unlock_achievements', 'target': 50, 'points': 2500},
                ],
                'rewards': {
                    'points': [50, 250, 500, 1250, 2500],
                    'xp': [25, 125, 250, 625, 1250],
                    'trophies': [0, 1, 2, 5, 10],
                }
            },
            'level_climber': {
                'name': 'Level Climber',
                'description': 'Reach new levels',
                'icon': '⬆️',
                'objectives': [
                    {'type': 'reach_level', 'target': 5, 'points': 100},
                    {'type': 'reach_level', 'target': 10, 'points': 200},
                    {'type': 'reach_level', 'target': 25, 'points': 500},
                    {'type': 'reach_level', 'target': 50, 'points': 1000},
                    {'type': 'reach_level', 'target': 100, 'points': 2000},
                    {'type': 'reach_level', 'target': 200, 'points': 5000},
                ],
                'rewards': {
                    'points': [100, 200, 500, 1000, 2000, 5000],
                    'xp': [50, 100, 250, 500, 1000, 2500],
                    'stat_points': [1, 2, 5, 10, 20, 50],
                }
            },
            'point_collector': {
                'name': 'Point Collector',
                'description': 'Collect points from all sources',
                'icon': '💎',
                'objectives': [
                    {'type': 'total_points', 'target': 1000, 'points': 100},
                    {'type': 'total_points', 'target': 5000, 'points': 500},
                    {'type': 'total_points', 'target': 10000, 'points': 1000},
                    {'type': 'total_points', 'target': 50000, 'points': 5000},
                    {'type': 'total_points', 'target': 100000, 'points': 10000},
                ],
                'rewards': {
                    'points': [100, 500, 1000, 5000, 10000],
                    'xp': [50, 250, 500, 2500, 5000],
                    'coins': [100, 500, 1000, 5000, 10000],
                }
            },
            # 50 NEW QUESTS START HERE
            'trophy_hunter': {
                'name': 'Trophy Hunter',
                'description': 'Collect trophies from battles and achievements',
                'icon': '🏆',
                'objectives': [
                    {'type': 'collect_trophies', 'target': 1, 'points': 150},
                    {'type': 'collect_trophies', 'target': 5, 'points': 750},
                    {'type': 'collect_trophies', 'target': 10, 'points': 1500},
                    {'type': 'collect_trophies', 'target': 25, 'points': 3750},
                    {'type': 'collect_trophies', 'target': 50, 'points': 7500},
                ],
                'rewards': {
                    'points': [150, 750, 1500, 3750, 7500],
                    'xp': [75, 375, 750, 1875, 3750],
                    'trophies': [1, 2, 5, 10, 20],
                }
            },
            'milestone_master': {
                'name': 'Milestone Master',
                'description': 'Reach important milestones',
                'icon': '🎯',
                'objectives': [
                    {'type': 'reach_milestones', 'target': 1, 'points': 200},
                    {'type': 'reach_milestones', 'target': 5, 'points': 1000},
                    {'type': 'reach_milestones', 'target': 10, 'points': 2000},
                    {'type': 'reach_milestones', 'target': 20, 'points': 4000},
                ],
                'rewards': {
                    'points': [200, 1000, 2000, 4000],
                    'xp': [100, 500, 1000, 2000],
                    'stat_points': [2, 5, 10, 20],
                }
            },
            'theme_explorer': {
                'name': 'Theme Explorer',
                'description': 'Try different video themes',
                'icon': '🎨',
                'objectives': [
                    {'type': 'use_themes', 'target': 3, 'points': 120},
                    {'type': 'use_themes', 'target': 10, 'points': 400},
                    {'type': 'use_themes', 'target': 20, 'points': 800},
                    {'type': 'use_themes', 'target': 30, 'points': 1200},
                ],
                'rewards': {
                    'points': [120, 400, 800, 1200],
                    'xp': [60, 200, 400, 600],
                    'theme_points': [50, 150, 300, 500],
                }
            },
            'chat_enthusiast': {
                'name': 'Chat Enthusiast',
                'description': 'Engage in community chat',
                'icon': '💬',
                'objectives': [
                    {'type': 'chat_messages', 'target': 10, 'points': 50},
                    {'type': 'chat_messages', 'target': 50, 'points': 250},
                    {'type': 'chat_messages', 'target': 100, 'points': 500},
                    {'type': 'chat_messages', 'target': 250, 'points': 1250},
                    {'type': 'chat_messages', 'target': 500, 'points': 2500},
                ],
                'rewards': {
                    'points': [50, 250, 500, 1250, 2500],
                    'xp': [25, 125, 250, 625, 1250],
                    'chat_points': [20, 100, 200, 500, 1000],
                }
            },
            'shop_spender': {
                'name': 'Shop Spender',
                'description': 'Make purchases in the shop',
                'icon': '🛒',
                'objectives': [
                    {'type': 'shop_purchases', 'target': 1, 'points': 100},
                    {'type': 'shop_purchases', 'target': 5, 'points': 500},
                    {'type': 'shop_purchases', 'target': 10, 'points': 1000},
                    {'type': 'shop_purchases', 'target': 25, 'points': 2500},
                ],
                'rewards': {
                    'points': [100, 500, 1000, 2500],
                    'xp': [50, 250, 500, 1250],
                    'coins': [200, 1000, 2000, 5000],
                }
            },
            'generation_specialist': {
                'name': 'Generation Specialist',
                'description': 'Generate content across different categories',
                'icon': '⚡',
                'objectives': [
                    {'type': 'generations', 'target': 10, 'points': 200},
                    {'type': 'generations', 'target': 25, 'points': 500},
                    {'type': 'generations', 'target': 50, 'points': 1000},
                    {'type': 'generations', 'target': 100, 'points': 2000},
                ],
                'rewards': {
                    'points': [200, 500, 1000, 2000],
                    'xp': [100, 250, 500, 1000],
                    'generation_points': [100, 250, 500, 1000],
                }
            },
            'streak_champion': {
                'name': 'Streak Champion',
                'description': 'Maintain win streaks in battles',
                'icon': '🔥',
                'objectives': [
                    {'type': 'win_streak', 'target': 3, 'points': 300},
                    {'type': 'win_streak', 'target': 5, 'points': 500},
                    {'type': 'win_streak', 'target': 10, 'points': 1000},
                    {'type': 'win_streak', 'target': 15, 'points': 1500},
                ],
                'rewards': {
                    'points': [300, 500, 1000, 1500],
                    'xp': [150, 250, 500, 750],
                    'battle_points': [200, 350, 700, 1050],
                }
            },
            'social_butterfly': {
                'name': 'Social Butterfly',
                'description': 'Interact with other players',
                'icon': '🦋',
                'objectives': [
                    {'type': 'social_interactions', 'target': 5, 'points': 75},
                    {'type': 'social_interactions', 'target': 15, 'points': 225},
                    {'type': 'social_interactions', 'target': 30, 'points': 450},
                    {'type': 'social_interactions', 'target': 50, 'points': 750},
                ],
                'rewards': {
                    'points': [75, 225, 450, 750],
                    'xp': [37, 112, 225, 375],
                    'social_points': [50, 150, 300, 500],
                }
            },
            'explorer': {
                'name': 'Explorer',
                'description': 'Explore different game features',
                'icon': '🗺️',
                'objectives': [
                    {'type': 'explore_features', 'target': 5, 'points': 150},
                    {'type': 'explore_features', 'target': 10, 'points': 300},
                    {'type': 'explore_features', 'target': 20, 'points': 600},
                ],
                'rewards': {
                    'points': [150, 300, 600],
                    'xp': [75, 150, 300],
                    'activity_points': [100, 200, 400],
                }
            },
            'perfectionist': {
                'name': 'Perfectionist',
                'description': 'Achieve perfect scores',
                'icon': '✨',
                'objectives': [
                    {'type': 'perfect_scores', 'target': 1, 'points': 500},
                    {'type': 'perfect_scores', 'target': 3, 'points': 1500},
                    {'type': 'perfect_scores', 'target': 5, 'points': 2500},
                ],
                'rewards': {
                    'points': [500, 1500, 2500],
                    'xp': [250, 750, 1250],
                    'stat_points': [5, 15, 25],
                }
            },
            'night_owl': {
                'name': 'Night Owl',
                'description': 'Play during night hours',
                'icon': '🦉',
                'objectives': [
                    {'type': 'night_sessions', 'target': 5, 'points': 200},
                    {'type': 'night_sessions', 'target': 10, 'points': 400},
                    {'type': 'night_sessions', 'target': 20, 'points': 800},
                ],
                'rewards': {
                    'points': [200, 400, 800],
                    'xp': [100, 200, 400],
                    'coins': [150, 300, 600],
                }
            },
            'early_bird': {
                'name': 'Early Bird',
                'description': 'Play during morning hours',
                'icon': '🌅',
                'objectives': [
                    {'type': 'morning_sessions', 'target': 5, 'points': 200},
                    {'type': 'morning_sessions', 'target': 10, 'points': 400},
                    {'type': 'morning_sessions', 'target': 20, 'points': 800},
                ],
                'rewards': {
                    'points': [200, 400, 800],
                    'xp': [100, 200, 400],
                    'coins': [150, 300, 600],
                }
            },
            'speed_demon': {
                'name': 'Speed Demon',
                'description': 'Complete actions quickly',
                'icon': '⚡',
                'objectives': [
                    {'type': 'quick_completions', 'target': 10, 'points': 250},
                    {'type': 'quick_completions', 'target': 25, 'points': 625},
                    {'type': 'quick_completions', 'target': 50, 'points': 1250},
                ],
                'rewards': {
                    'points': [250, 625, 1250],
                    'xp': [125, 312, 625],
                    'activity_points': [150, 375, 750],
                }
            },
            'collector': {
                'name': 'Collector',
                'description': 'Collect various items',
                'icon': '📦',
                'objectives': [
                    {'type': 'collect_items', 'target': 10, 'points': 180},
                    {'type': 'collect_items', 'target': 25, 'points': 450},
                    {'type': 'collect_items', 'target': 50, 'points': 900},
                ],
                'rewards': {
                    'points': [180, 450, 900],
                    'xp': [90, 225, 450],
                    'coins': [200, 500, 1000],
                }
            },
            'strategist': {
                'name': 'Strategist',
                'description': 'Plan and execute strategies',
                'icon': '🧠',
                'objectives': [
                    {'type': 'strategic_actions', 'target': 5, 'points': 300},
                    {'type': 'strategic_actions', 'target': 10, 'points': 600},
                    {'type': 'strategic_actions', 'target': 20, 'points': 1200},
                ],
                'rewards': {
                    'points': [300, 600, 1200],
                    'xp': [150, 300, 600],
                    'stat_points': [3, 6, 12],
                }
            },
            'team_player': {
                'name': 'Team Player',
                'description': 'Participate in team activities',
                'icon': '👥',
                'objectives': [
                    {'type': 'team_activities', 'target': 3, 'points': 200},
                    {'type': 'team_activities', 'target': 10, 'points': 667},
                    {'type': 'team_activities', 'target': 20, 'points': 1333},
                ],
                'rewards': {
                    'points': [200, 667, 1333],
                    'xp': [100, 333, 666],
                    'social_points': [150, 500, 1000],
                }
            },
            'lucky_charm': {
                'name': 'Lucky Charm',
                'description': 'Get lucky rewards',
                'icon': '🍀',
                'objectives': [
                    {'type': 'lucky_rewards', 'target': 5, 'points': 250},
                    {'type': 'lucky_rewards', 'target': 10, 'points': 500},
                    {'type': 'lucky_rewards', 'target': 20, 'points': 1000},
                ],
                'rewards': {
                    'points': [250, 500, 1000],
                    'xp': [125, 250, 500],
                    'coins': [300, 600, 1200],
                }
            },
            'dedicated_player': {
                'name': 'Dedicated Player',
                'description': 'Play consistently over time',
                'icon': '💪',
                'objectives': [
                    {'type': 'consistent_play', 'target': 7, 'points': 350},
                    {'type': 'consistent_play', 'target': 14, 'points': 700},
                    {'type': 'consistent_play', 'target': 30, 'points': 1500},
                ],
                'rewards': {
                    'points': [350, 700, 1500],
                    'xp': [175, 350, 750],
                    'activity_points': [250, 500, 1000],
                }
            },
            'skill_master': {
                'name': 'Skill Master',
                'description': 'Master various skills',
                'icon': '🎓',
                'objectives': [
                    {'type': 'master_skills', 'target': 3, 'points': 400},
                    {'type': 'master_skills', 'target': 5, 'points': 667},
                    {'type': 'master_skills', 'target': 10, 'points': 1333},
                ],
                'rewards': {
                    'points': [400, 667, 1333],
                    'xp': [200, 333, 666],
                    'stat_points': [5, 8, 15],
                }
            },
            'event_participant': {
                'name': 'Event Participant',
                'description': 'Participate in special events',
                'icon': '🎉',
                'objectives': [
                    {'type': 'event_participation', 'target': 1, 'points': 300},
                    {'type': 'event_participation', 'target': 3, 'points': 900},
                    {'type': 'event_participation', 'target': 5, 'points': 1500},
                ],
                'rewards': {
                    'points': [300, 900, 1500],
                    'xp': [150, 450, 750],
                    'event_points': [200, 600, 1000],
                }
            },
            'challenge_seeker': {
                'name': 'Challenge Seeker',
                'description': 'Complete challenges',
                'icon': '🎯',
                'objectives': [
                    {'type': 'complete_challenges', 'target': 5, 'points': 400},
                    {'type': 'complete_challenges', 'target': 10, 'points': 800},
                    {'type': 'complete_challenges', 'target': 20, 'points': 1600},
                ],
                'rewards': {
                    'points': [400, 800, 1600],
                    'xp': [200, 400, 800],
                    'stat_points': [4, 8, 16],
                }
            },
            'resource_manager': {
                'name': 'Resource Manager',
                'description': 'Manage resources efficiently',
                'icon': '📊',
                'objectives': [
                    {'type': 'resource_management', 'target': 10, 'points': 300},
                    {'type': 'resource_management', 'target': 25, 'points': 750},
                    {'type': 'resource_management', 'target': 50, 'points': 1500},
                ],
                'rewards': {
                    'points': [300, 750, 1500],
                    'xp': [150, 375, 750],
                    'coins': [400, 1000, 2000],
                }
            },
            'creative_genius': {
                'name': 'Creative Genius',
                'description': 'Create unique content',
                'icon': '🎨',
                'objectives': [
                    {'type': 'creative_content', 'target': 5, 'points': 350},
                    {'type': 'creative_content', 'target': 10, 'points': 700},
                    {'type': 'creative_content', 'target': 20, 'points': 1400},
                ],
                'rewards': {
                    'points': [350, 700, 1400],
                    'xp': [175, 350, 700],
                    'generation_points': [200, 400, 800],
                }
            },
            'leaderboard_climber': {
                'name': 'Leaderboard Climber',
                'description': 'Climb the leaderboards',
                'icon': '📈',
                'objectives': [
                    {'type': 'leaderboard_rank', 'target': 100, 'points': 500},
                    {'type': 'leaderboard_rank', 'target': 50, 'points': 1000},
                    {'type': 'leaderboard_rank', 'target': 25, 'points': 2000},
                    {'type': 'leaderboard_rank', 'target': 10, 'points': 4000},
                ],
                'rewards': {
                    'points': [500, 1000, 2000, 4000],
                    'xp': [250, 500, 1000, 2000],
                    'trophies': [1, 2, 4, 8],
                }
            },
            'multi_tasker': {
                'name': 'Multi-Tasker',
                'description': 'Complete multiple tasks simultaneously',
                'icon': '🔄',
                'objectives': [
                    {'type': 'multi_tasks', 'target': 3, 'points': 250},
                    {'type': 'multi_tasks', 'target': 5, 'points': 417},
                    {'type': 'multi_tasks', 'target': 10, 'points': 833},
                ],
                'rewards': {
                    'points': [250, 417, 833],
                    'xp': [125, 208, 416],
                    'activity_points': [200, 333, 666],
                }
            },
            'time_traveler': {
                'name': 'Time Traveler',
                'description': 'Play at different times',
                'icon': '⏰',
                'objectives': [
                    {'type': 'time_variety', 'target': 5, 'points': 200},
                    {'type': 'time_variety', 'target': 10, 'points': 400},
                    {'type': 'time_variety', 'target': 20, 'points': 800},
                ],
                'rewards': {
                    'points': [200, 400, 800],
                    'xp': [100, 200, 400],
                    'coins': [250, 500, 1000],
                }
            },
            'veteran': {
                'name': 'Veteran',
                'description': 'Play for extended periods',
                'icon': '🎖️',
                'objectives': [
                    {'type': 'long_sessions', 'target': 5, 'points': 400},
                    {'type': 'long_sessions', 'target': 10, 'points': 800},
                    {'type': 'long_sessions', 'target': 20, 'points': 1600},
                ],
                'rewards': {
                    'points': [400, 800, 1600],
                    'xp': [200, 400, 800],
                    'stat_points': [5, 10, 20],
                }
            },
            'social_media_star': {
                'name': 'Social Media Star',
                'description': 'Share and promote content',
                'icon': '📱',
                'objectives': [
                    {'type': 'social_shares', 'target': 5, 'points': 300},
                    {'type': 'social_shares', 'target': 10, 'points': 600},
                    {'type': 'social_shares', 'target': 20, 'points': 1200},
                ],
                'rewards': {
                    'points': [300, 600, 1200],
                    'xp': [150, 300, 600],
                    'social_points': [250, 500, 1000],
                }
            },
            'treasure_hunter': {
                'name': 'Treasure Hunter',
                'description': 'Find hidden treasures',
                'icon': '💎',
                'objectives': [
                    {'type': 'find_treasures', 'target': 1, 'points': 500},
                    {'type': 'find_treasures', 'target': 3, 'points': 1500},
                    {'type': 'find_treasures', 'target': 5, 'points': 2500},
                ],
                'rewards': {
                    'points': [500, 1500, 2500],
                    'xp': [250, 750, 1250],
                    'coins': [1000, 3000, 5000],
                }
            },
            'mentor': {
                'name': 'Mentor',
                'description': 'Help other players',
                'icon': '👨‍🏫',
                'objectives': [
                    {'type': 'help_others', 'target': 5, 'points': 400},
                    {'type': 'help_others', 'target': 10, 'points': 800},
                    {'type': 'help_others', 'target': 20, 'points': 1600},
                ],
                'rewards': {
                    'points': [400, 800, 1600],
                    'xp': [200, 400, 800],
                    'social_points': [300, 600, 1200],
                }
            },
            'completionist': {
                'name': 'Completionist',
                'description': 'Complete everything',
                'icon': '✅',
                'objectives': [
                    {'type': 'complete_all', 'target': 10, 'points': 600},
                    {'type': 'complete_all', 'target': 25, 'points': 1500},
                    {'type': 'complete_all', 'target': 50, 'points': 3000},
                ],
                'rewards': {
                    'points': [600, 1500, 3000],
                    'xp': [300, 750, 1500],
                    'stat_points': [10, 25, 50],
                }
            },
            'speed_runner': {
                'name': 'Speed Runner',
                'description': 'Complete tasks in record time',
                'icon': '🏃',
                'objectives': [
                    {'type': 'speed_runs', 'target': 3, 'points': 450},
                    {'type': 'speed_runs', 'target': 5, 'points': 750},
                    {'type': 'speed_runs', 'target': 10, 'points': 1500},
                ],
                'rewards': {
                    'points': [450, 750, 1500],
                    'xp': [225, 375, 750],
                    'activity_points': [350, 583, 1166],
                }
            },
            'innovator': {
                'name': 'Innovator',
                'description': 'Try new features first',
                'icon': '💡',
                'objectives': [
                    {'type': 'try_new_features', 'target': 3, 'points': 350},
                    {'type': 'try_new_features', 'target': 5, 'points': 583},
                    {'type': 'try_new_features', 'target': 10, 'points': 1166},
                ],
                'rewards': {
                    'points': [350, 583, 1166],
                    'xp': [175, 291, 583],
                    'stat_points': [4, 7, 14],
                }
            },
            'guild_member': {
                'name': 'Guild Member',
                'description': 'Participate in guild activities',
                'icon': '🏰',
                'objectives': [
                    {'type': 'guild_activities', 'target': 5, 'points': 300},
                    {'type': 'guild_activities', 'target': 10, 'points': 600},
                    {'type': 'guild_activities', 'target': 20, 'points': 1200},
                ],
                'rewards': {
                    'points': [300, 600, 1200],
                    'xp': [150, 300, 600],
                    'guild_points': [250, 500, 1000],
                }
            },
            'pvp_warrior': {
                'name': 'PVP Warrior',
                'description': 'Excel in player vs player battles',
                'icon': '⚔️',
                'objectives': [
                    {'type': 'pvp_wins', 'target': 5, 'points': 500},
                    {'type': 'pvp_wins', 'target': 10, 'points': 1000},
                    {'type': 'pvp_wins', 'target': 25, 'points': 2500},
                ],
                'rewards': {
                    'points': [500, 1000, 2500],
                    'xp': [250, 500, 1250],
                    'battle_points': [400, 800, 2000],
                }
            },
            'economist': {
                'name': 'Economist',
                'description': 'Manage economy efficiently',
                'icon': '💰',
                'objectives': [
                    {'type': 'economic_actions', 'target': 10, 'points': 400},
                    {'type': 'economic_actions', 'target': 25, 'points': 1000},
                    {'type': 'economic_actions', 'target': 50, 'points': 2000},
                ],
                'rewards': {
                    'points': [400, 1000, 2000],
                    'xp': [200, 500, 1000],
                    'coins': [800, 2000, 4000],
                }
            },
            'researcher': {
                'name': 'Researcher',
                'description': 'Research and discover',
                'icon': '🔬',
                'objectives': [
                    {'type': 'research_actions', 'target': 5, 'points': 350},
                    {'type': 'research_actions', 'target': 10, 'points': 700},
                    {'type': 'research_actions', 'target': 20, 'points': 1400},
                ],
                'rewards': {
                    'points': [350, 700, 1400],
                    'xp': [175, 350, 700],
                    'stat_points': [4, 8, 16],
                }
            },
            'builder': {
                'name': 'Builder',
                'description': 'Build and construct',
                'icon': '🏗️',
                'objectives': [
                    {'type': 'build_actions', 'target': 5, 'points': 300},
                    {'type': 'build_actions', 'target': 10, 'points': 600},
                    {'type': 'build_actions', 'target': 20, 'points': 1200},
                ],
                'rewards': {
                    'points': [300, 600, 1200],
                    'xp': [150, 300, 600],
                    'coins': [500, 1000, 2000],
                }
            },
            'explorer_advanced': {
                'name': 'Advanced Explorer',
                'description': 'Explore advanced features',
                'icon': '🗺️',
                'objectives': [
                    {'type': 'advanced_exploration', 'target': 3, 'points': 500},
                    {'type': 'advanced_exploration', 'target': 5, 'points': 833},
                    {'type': 'advanced_exploration', 'target': 10, 'points': 1666},
                ],
                'rewards': {
                    'points': [500, 833, 1666],
                    'xp': [250, 416, 833],
                    'stat_points': [6, 10, 20],
                }
            },
            'festival_goer': {
                'name': 'Festival Goer',
                'description': 'Participate in festivals',
                'icon': '🎊',
                'objectives': [
                    {'type': 'festival_participation', 'target': 1, 'points': 400},
                    {'type': 'festival_participation', 'target': 3, 'points': 1200},
                    {'type': 'festival_participation', 'target': 5, 'points': 2000},
                ],
                'rewards': {
                    'points': [400, 1200, 2000],
                    'xp': [200, 600, 1000],
                    'event_points': [300, 900, 1500],
                }
            },
            'legend': {
                'name': 'Legend',
                'description': 'Achieve legendary status',
                'icon': '👑',
                'objectives': [
                    {'type': 'legendary_achievements', 'target': 1, 'points': 2000},
                    {'type': 'legendary_achievements', 'target': 3, 'points': 6000},
                    {'type': 'legendary_achievements', 'target': 5, 'points': 10000},
                ],
                'rewards': {
                    'points': [2000, 6000, 10000],
                    'xp': [1000, 3000, 5000],
                    'trophies': [10, 30, 50],
                }
            },
            'master_builder': {
                'name': 'Master Builder',
                'description': 'Build complex structures',
                'icon': '🏛️',
                'objectives': [
                    {'type': 'complex_builds', 'target': 3, 'points': 600},
                    {'type': 'complex_builds', 'target': 5, 'points': 1000},
                    {'type': 'complex_builds', 'target': 10, 'points': 2000},
                ],
                'rewards': {
                    'points': [600, 1000, 2000],
                    'xp': [300, 500, 1000],
                    'coins': [1200, 2000, 4000],
                }
            },
            'diplomat': {
                'name': 'Diplomat',
                'description': 'Engage in diplomacy',
                'icon': '🤝',
                'objectives': [
                    {'type': 'diplomatic_actions', 'target': 5, 'points': 400},
                    {'type': 'diplomatic_actions', 'target': 10, 'points': 800},
                    {'type': 'diplomatic_actions', 'target': 20, 'points': 1600},
                ],
                'rewards': {
                    'points': [400, 800, 1600],
                    'xp': [200, 400, 800],
                    'social_points': [350, 700, 1400],
                }
            },
            'guardian': {
                'name': 'Guardian',
                'description': 'Protect and defend',
                'icon': '🛡️',
                'objectives': [
                    {'type': 'defensive_actions', 'target': 5, 'points': 350},
                    {'type': 'defensive_actions', 'target': 10, 'points': 700},
                    {'type': 'defensive_actions', 'target': 20, 'points': 1400},
                ],
                'rewards': {
                    'points': [350, 700, 1400],
                    'xp': [175, 350, 700],
                    'battle_points': [300, 600, 1200],
                }
            },
            'merchant': {
                'name': 'Merchant',
                'description': 'Trade and commerce',
                'icon': '🏪',
                'objectives': [
                    {'type': 'trade_actions', 'target': 10, 'points': 450},
                    {'type': 'trade_actions', 'target': 25, 'points': 1125},
                    {'type': 'trade_actions', 'target': 50, 'points': 2250},
                ],
                'rewards': {
                    'points': [450, 1125, 2250],
                    'xp': [225, 562, 1125],
                    'coins': [900, 2250, 4500],
                }
            },
            'scholar': {
                'name': 'Scholar',
                'description': 'Learn and study',
                'icon': '📚',
                'objectives': [
                    {'type': 'learning_actions', 'target': 10, 'points': 300},
                    {'type': 'learning_actions', 'target': 25, 'points': 750},
                    {'type': 'learning_actions', 'target': 50, 'points': 1500},
                ],
                'rewards': {
                    'points': [300, 750, 1500],
                    'xp': [150, 375, 750],
                    'stat_points': [5, 12, 25],
                }
            },
            'adventurer': {
                'name': 'Adventurer',
                'description': 'Go on adventures',
                'icon': '🗡️',
                'objectives': [
                    {'type': 'adventures', 'target': 3, 'points': 400},
                    {'type': 'adventures', 'target': 5, 'points': 667},
                    {'type': 'adventures', 'target': 10, 'points': 1333},
                ],
                'rewards': {
                    'points': [400, 667, 1333],
                    'xp': [200, 333, 666],
                    'activity_points': [300, 500, 1000],
                }
            },
            'celebrity': {
                'name': 'Celebrity',
                'description': 'Gain recognition',
                'icon': '⭐',
                'objectives': [
                    {'type': 'recognition', 'target': 10, 'points': 500},
                    {'type': 'recognition', 'target': 25, 'points': 1250},
                    {'type': 'recognition', 'target': 50, 'points': 2500},
                ],
                'rewards': {
                    'points': [500, 1250, 2500],
                    'xp': [250, 625, 1250],
                    'social_points': [400, 1000, 2000],
                }
            },
            'philanthropist': {
                'name': 'Philanthropist',
                'description': 'Give back to community',
                'icon': '❤️',
                'objectives': [
                    {'type': 'community_contributions', 'target': 5, 'points': 450},
                    {'type': 'community_contributions', 'target': 10, 'points': 900},
                    {'type': 'community_contributions', 'target': 20, 'points': 1800},
                ],
                'rewards': {
                    'points': [450, 900, 1800],
                    'xp': [225, 450, 900],
                    'social_points': [400, 800, 1600],
                }
            },
            'pioneer': {
                'name': 'Pioneer',
                'description': 'Be first to discover',
                'icon': '🚀',
                'objectives': [
                    {'type': 'first_discoveries', 'target': 1, 'points': 1000},
                    {'type': 'first_discoveries', 'target': 3, 'points': 3000},
                    {'type': 'first_discoveries', 'target': 5, 'points': 5000},
                ],
                'rewards': {
                    'points': [1000, 3000, 5000],
                    'xp': [500, 1500, 2500],
                    'trophies': [5, 15, 25],
                }
            },
            'architect': {
                'name': 'Architect',
                'description': 'Design and plan',
                'icon': '📐',
                'objectives': [
                    {'type': 'design_actions', 'target': 5, 'points': 400},
                    {'type': 'design_actions', 'target': 10, 'points': 800},
                    {'type': 'design_actions', 'target': 20, 'points': 1600},
                ],
                'rewards': {
                    'points': [400, 800, 1600],
                    'xp': [200, 400, 800],
                    'stat_points': [5, 10, 20],
                }
            },
            'champion': {
                'name': 'Champion',
                'description': 'Win championships',
                'icon': '🏅',
                'objectives': [
                    {'type': 'championship_wins', 'target': 1, 'points': 1500},
                    {'type': 'championship_wins', 'target': 3, 'points': 4500},
                    {'type': 'championship_wins', 'target': 5, 'points': 7500},
                ],
                'rewards': {
                    'points': [1500, 4500, 7500],
                    'xp': [750, 2250, 3750],
                    'trophies': [10, 30, 50],
                }
            },
            'sage': {
                'name': 'Sage',
                'description': 'Share wisdom',
                'icon': '🧙',
                'objectives': [
                    {'type': 'wisdom_sharing', 'target': 5, 'points': 350},
                    {'type': 'wisdom_sharing', 'target': 10, 'points': 700},
                    {'type': 'wisdom_sharing', 'target': 20, 'points': 1400},
                ],
                'rewards': {
                    'points': [350, 700, 1400],
                    'xp': [175, 350, 700],
                    'social_points': [300, 600, 1200],
                }
            },
            'hero': {
                'name': 'Hero',
                'description': 'Perform heroic deeds',
                'icon': '🦸',
                'objectives': [
                    {'type': 'heroic_deeds', 'target': 3, 'points': 600},
                    {'type': 'heroic_deeds', 'target': 5, 'points': 1000},
                    {'type': 'heroic_deeds', 'target': 10, 'points': 2000},
                ],
                'rewards': {
                    'points': [600, 1000, 2000],
                    'xp': [300, 500, 1000],
                    'trophies': [5, 8, 15],
                }
            },
        }
    
    def get_user_quests(self, user_id: str) -> Dict[str, Any]:
        """Get all quests for user"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        try:
            profile = unified_points_db.get_user_profile(user_id)
            preferences = profile.get('preferences', {})
            
            # Get user level for quest level calculation
            user_level = profile.get('level', 1)
            quest_level = self._get_quest_level(user_level)
            
            # Get active and completed quests
            active_quests = preferences.get('active_quests', {})
            completed_quests = preferences.get('completed_quests', [])
            quest_progress = preferences.get('quest_progress', {})
            
            # Initialize quests if needed
            if not active_quests:
                active_quests = self._initialize_user_quests(user_id, user_level)
                preferences['active_quests'] = active_quests
                unified_points_db.save_user_profile(user_id, profile)
            
            # Calculate progress for each quest
            quests_with_progress = []
            for quest_id, quest_data in active_quests.items():
                progress = quest_progress.get(quest_id, {})
                current_stage = quest_data.get('current_stage', 0)
                template = self.quest_templates.get(quest_data.get('template_id', ''))
                
                if template:
                    objectives = template.get('objectives', [])
                    if current_stage < len(objectives):
                        current_objective = objectives[current_stage]
                        progress_value = progress.get('value', 0)
                        target = current_objective.get('target', 1)
                        progress_percent = min((progress_value / target) * 100, 100)
                        
                        quests_with_progress.append({
                            'quest_id': quest_id,
                            'name': quest_data.get('name', template.get('name', '')),
                            'description': quest_data.get('description', template.get('description', '')),
                            'icon': template.get('icon', '📋'),
                            'level': quest_level,
                            'current_stage': current_stage,
                            'total_stages': len(objectives),
                            'current_objective': current_objective,
                            'progress': {
                                'value': progress_value,
                                'target': target,
                                'percent': progress_percent
                            },
                            'rewards': self._get_stage_rewards(template, current_stage),
                            'completed': False
                        })
            
            return {
                'success': True,
                'quests': quests_with_progress,
                'completed_count': len(completed_quests),
                'active_count': len(quests_with_progress),
                'quest_level': quest_level
            }
        except Exception as e:
            print(f"[QuestSystem] Error getting quests: {e}")
            return {'success': False, 'error': str(e)}
    
    def _initialize_user_quests(self, user_id: str, user_level: int) -> Dict[str, Dict]:
        """Initialize quests for new user"""
        quest_level = self._get_quest_level(user_level)
        active_quests = {}
        
        # Add quests based on level
        for template_id, template in self.quest_templates.items():
            quest_id = f"{template_id}_{user_id}_{uuid.uuid4().hex[:8]}"
            active_quests[quest_id] = {
                'template_id': template_id,
                'name': template.get('name', ''),
                'description': template.get('description', ''),
                'user_id': user_id,
                'quest_level': quest_level,
                'current_stage': 0,
                'created_at': datetime.utcnow().isoformat()
            }
        
        return active_quests
    
    def _get_quest_level(self, user_level: int) -> str:
        """Get quest level based on user level"""
        for level_name, level_data in self.quest_levels.items():
            if level_data['min_level'] <= user_level <= level_data['max_level']:
                return level_name
        return 'beginner'
    
    def _get_stage_rewards(self, template: Dict, stage: int) -> Dict[str, Any]:
        """Get rewards for a quest stage"""
        rewards_data = template.get('rewards', {})
        rewards = {}
        
        for reward_type, reward_list in rewards_data.items():
            if stage < len(reward_list):
                rewards[reward_type] = reward_list[stage]
        
        return rewards
    
    def update_quest_progress(
        self,
        user_id: str,
        objective_type: str,
        amount: int = 1
    ) -> Dict[str, Any]:
        """Update quest progress"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        try:
            profile = unified_points_db.get_user_profile(user_id)
            preferences = profile.get('preferences', {})
            active_quests = preferences.get('active_quests', {})
            quest_progress = preferences.get('quest_progress', {})
            
            completed_stages = []
            points_earned = 0
            xp_earned = 0
            
            # Update progress for each quest
            for quest_id, quest_data in active_quests.items():
                template_id = quest_data.get('template_id', '')
                template = self.quest_templates.get(template_id)
                
                if not template:
                    continue
                
                current_stage = quest_data.get('current_stage', 0)
                objectives = template.get('objectives', [])
                
                if current_stage >= len(objectives):
                    continue
                
                current_objective = objectives[current_stage]
                
                # Check if this objective matches
                if current_objective.get('type') == objective_type:
                    # Update progress
                    if quest_id not in quest_progress:
                        quest_progress[quest_id] = {}
                    
                    current_value = quest_progress[quest_id].get('value', 0)
                    new_value = current_value + amount
                    target = current_objective.get('target', 1)
                    
                    quest_progress[quest_id]['value'] = new_value
                    quest_progress[quest_id]['type'] = objective_type
                    quest_progress[quest_id]['last_updated'] = datetime.utcnow().isoformat()
                    
                    # Check if stage completed
                    if new_value >= target:
                        # Award rewards
                        stage_rewards = self._get_stage_rewards(template, current_stage)
                        points = stage_rewards.get('points', 0)
                        xp = stage_rewards.get('xp', 0)
                        
                        # Apply level multiplier
                        quest_level = quest_data.get('quest_level', 'beginner')
                        multiplier = self.quest_levels.get(quest_level, {}).get('points_multiplier', 1.0)
                        points = int(points * multiplier)
                        xp = int(xp * multiplier)
                        
                        points_earned += points
                        xp_earned += xp
                        
                        # Add quest points
                        if point_connection:
                            point_connection.ensure_point_counting(user_id, 'quest_points', points, 'quest_system')
                            point_connection.ensure_point_counting(user_id, 'xp', xp, 'quest_system')
                        
                        # Add rewards
                        if rewards_system_v2:
                            rewards_system_v2.create_reward(
                                user_id=user_id,
                                category='quest',
                                reward_type='points',
                                amount=points,
                                rarity='uncommon',
                                description=f"Quest stage completion: {quest_data.get('name', '')}",
                                source='quest_system',
                                metadata={'quest_id': quest_id, 'stage': current_stage}
                            )
                        
                        # Move to next stage
                        quest_data['current_stage'] = current_stage + 1
                        quest_progress[quest_id]['value'] = 0  # Reset for next stage
                        
                        completed_stages.append({
                            'quest_id': quest_id,
                            'quest_name': quest_data.get('name', ''),
                            'stage': current_stage,
                            'rewards': stage_rewards
                        })
                        
                        # Check if quest completed
                        if quest_data['current_stage'] >= len(objectives):
                            # Quest completed
                            if 'completed_quests' not in preferences:
                                preferences['completed_quests'] = []
                            preferences['completed_quests'].append({
                                'quest_id': quest_id,
                                'template_id': template_id,
                                'completed_at': datetime.utcnow().isoformat()
                            })
                            del active_quests[quest_id]
            
            # Save progress
            preferences['active_quests'] = active_quests
            preferences['quest_progress'] = quest_progress
            profile['preferences'] = preferences
            unified_points_db.save_user_profile(user_id, profile)
            
            return {
                'success': True,
                'points_earned': points_earned,
                'xp_earned': xp_earned,
                'completed_stages': completed_stages,
                'updated_quests': len(active_quests)
            }
        except Exception as e:
            print(f"[QuestSystem] Error updating progress: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_quest_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get quest statistics"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        try:
            profile = unified_points_db.get_user_profile(user_id)
            preferences = profile.get('preferences', {})
            
            active_quests = preferences.get('active_quests', {})
            completed_quests = preferences.get('completed_quests', [])
            quest_progress = preferences.get('quest_progress', {})
            
            # Calculate statistics
            total_quest_points = 0
            quests_by_level = defaultdict(int)
            
            for quest_data in active_quests.values():
                quest_level = quest_data.get('quest_level', 'beginner')
                quests_by_level[quest_level] += 1
            
            return {
                'success': True,
                'active_quests': len(active_quests),
                'completed_quests': len(completed_quests),
                'total_quests': len(active_quests) + len(completed_quests),
                'quests_by_level': dict(quests_by_level),
                'total_quest_points': total_quest_points
            }
        except Exception as e:
            print(f"[QuestSystem] Error getting statistics: {e}")
            return {'success': False, 'error': str(e)}


# Global instance
quest_system = QuestSystem()

