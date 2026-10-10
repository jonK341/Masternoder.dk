"""
Trophy Point System (Trofæ System)
Awards trophies for achievements - part of behavioral research program
Includes future knowledge tracking, leveling milestones, and title rewards
"""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class TrophySystem:
    """Trophy/Achievement System for Behavioral Research"""
    
    def __init__(self):
        self.trophies = {}  # {user_id: List[Trophy]}
        self.trophy_definitions = self._initialize_trophy_definitions()
        self.future_knowledge = {}  # {user_id: Dict[str, Any]} - Future knowledge tracking
        self.leveling_milestones = self._initialize_leveling_milestones()
        self.psychological_profiles = {}  # {user_id: Dict[str, Any]} - Psychological research data
    
    def _initialize_trophy_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all available trophies"""
        return {
            # Generation Trophies
            'first_generation': {
                'id': 'first_generation',
                'name': 'First Steps',
                'description': 'Created your first documentary',
                'icon': '🎬',
                'points': 50,
                'category': 'generation'
            },
            'ten_generations': {
                'id': 'ten_generations',
                'name': 'Documentary Creator',
                'description': 'Created 10 documentaries',
                'icon': '🏆',
                'points': 200,
                'category': 'generation'
            },
            'hundred_generations': {
                'id': 'hundred_generations',
                'name': 'Master Filmmaker',
                'description': 'Created 100 documentaries',
                'icon': '👑',
                'points': 1000,
                'category': 'generation'
            },
            
            # Quality Trophies
            'perfect_generation': {
                'id': 'perfect_generation',
                'name': 'Perfect Score',
                'description': 'Generated documentary with 100% quality score',
                'icon': '⭐',
                'points': 150,
                'category': 'quality'
            },
            'long_documentary': {
                'id': 'long_documentary',
                'name': 'Epic Storyteller',
                'description': 'Created documentary longer than 10 minutes',
                'icon': '📽️',
                'points': 100,
                'category': 'quality'
            },
            
            # Engagement Trophies
            'daily_user': {
                'id': 'daily_user',
                'name': 'Daily Visitor',
                'description': 'Visited site 7 days in a row',
                'icon': '📅',
                'points': 75,
                'category': 'engagement'
            },
            'watch_master': {
                'id': 'watch_master',
                'name': 'Viewer',
                'description': 'Watched 50 documentaries',
                'icon': '👁️',
                'points': 150,
                'category': 'engagement'
            },
            
            # Sharing Trophies
            'first_share': {
                'id': 'first_share',
                'name': 'Sharing is Caring',
                'description': 'Shared your first documentary',
                'icon': '📤',
                'points': 50,
                'category': 'sharing'
            },
            'viral_creator': {
                'id': 'viral_creator',
                'name': 'Viral Creator',
                'description': 'Shared 10 documentaries',
                'icon': '🔥',
                'points': 200,
                'category': 'sharing'
            },
            
            # Skill Trophies
            'prompt_master': {
                'id': 'prompt_master',
                'name': 'Prompt Master',
                'description': 'Created 20 unique prompts',
                'icon': '✍️',
                'points': 100,
                'category': 'skill'
            },
            'speed_generator': {
                'id': 'speed_generator',
                'name': 'Speed Demon',
                'description': 'Completed generation in under 2 minutes',
                'icon': '⚡',
                'points': 125,
                'category': 'skill'
            },
            
            # Special Trophies
            'matrix_explorer': {
                'id': 'matrix_explorer',
                'name': 'Matrix Explorer',
                'description': 'Used Matrix theme 10 times',
                'icon': '🌐',
                'points': 150,
                'category': 'special'
            },
            'data_collector': {
                'id': 'data_collector',
                'name': 'Data Collector',
                'description': 'Gathered data from 5 different sources',
                'icon': '📊',
                'points': 100,
                'category': 'special'
            }
        }
    
    def check_and_award_trophies(self, user_id: str, action_type: str, metadata: Dict = None) -> List[Dict[str, Any]]:
        """
        Check if user qualifies for any trophies and award them
        
        Args:
            user_id: User identifier
            action_type: Type of action performed
            metadata: Additional metadata about the action
        
        Returns:
            List of newly awarded trophies
        """
        if metadata is None:
            metadata = {}
        
        newly_awarded = []
        
        # Get user's current trophy list
        if user_id not in self.trophies:
            self.trophies[user_id] = []
        
        user_trophies = [t['id'] for t in self.trophies[user_id]]
        
        # Check generation trophies
        if action_type == 'complete_generation':
            generation_count = metadata.get('total_generations', 0) + 1
            
            if 'first_generation' not in user_trophies and generation_count >= 1:
                trophy = self._award_trophy(user_id, 'first_generation')
                if trophy:
                    newly_awarded.append(trophy)
            
            if 'ten_generations' not in user_trophies and generation_count >= 10:
                trophy = self._award_trophy(user_id, 'ten_generations')
                if trophy:
                    newly_awarded.append(trophy)
            
            if 'hundred_generations' not in user_trophies and generation_count >= 100:
                trophy = self._award_trophy(user_id, 'hundred_generations')
                if trophy:
                    newly_awarded.append(trophy)
            
            # Check quality trophies
            quality_score = metadata.get('quality_score', 0)
            if quality_score >= 1.0 and 'perfect_generation' not in user_trophies:
                trophy = self._award_trophy(user_id, 'perfect_generation')
                if trophy:
                    newly_awarded.append(trophy)
            
            duration = metadata.get('duration', 0)
            if duration >= 600 and 'long_documentary' not in user_trophies:
                trophy = self._award_trophy(user_id, 'long_documentary')
                if trophy:
                    newly_awarded.append(trophy)
        
        # Check sharing trophies
        elif action_type == 'share_video':
            share_count = metadata.get('total_shares', 0) + 1
            
            if 'first_share' not in user_trophies and share_count >= 1:
                trophy = self._award_trophy(user_id, 'first_share')
                if trophy:
                    newly_awarded.append(trophy)
            
            if 'viral_creator' not in user_trophies and share_count >= 10:
                trophy = self._award_trophy(user_id, 'viral_creator')
                if trophy:
                    newly_awarded.append(trophy)
        
        # Check watch trophies
        elif action_type == 'watch_video':
            watch_count = metadata.get('total_watches', 0) + 1
            
            if 'watch_master' not in user_trophies and watch_count >= 50:
                trophy = self._award_trophy(user_id, 'watch_master')
                if trophy:
                    newly_awarded.append(trophy)
        
        return newly_awarded
    
    def _award_trophy(self, user_id: str, trophy_id: str) -> Optional[Dict[str, Any]]:
        """Award a trophy to a user"""
        if trophy_id not in self.trophy_definitions:
            return None
        
        trophy_def = self.trophy_definitions[trophy_id]
        
        # Check if already awarded
        if user_id in self.trophies:
            if any(t['id'] == trophy_id for t in self.trophies[user_id]):
                return None  # Already awarded
        
        # Award trophy
        trophy = {
            'id': trophy_id,
            'name': trophy_def['name'],
            'description': trophy_def['description'],
            'icon': trophy_def['icon'],
            'points': trophy_def['points'],
            'category': trophy_def['category'],
            'awarded_at': datetime.utcnow().isoformat()
        }
        
        if user_id not in self.trophies:
            self.trophies[user_id] = []
        
        self.trophies[user_id].append(trophy)
        
        return trophy
    
    def get_user_trophies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trophies for a user with earned status"""
        user_trophies = self.trophies.get(user_id, [])
        # Format trophies to match expected structure
        result = []
        for trophy in user_trophies:
            trophy_data = {
                'id': trophy.get('id'),
                'name': trophy.get('name'),
                'description': trophy.get('description'),
                'icon': trophy.get('icon'),
                'points': trophy.get('points'),
                'category': trophy.get('category'),
                'earned': True,  # All trophies in list are earned
                'earnedDate': trophy.get('awarded_at', datetime.utcnow().isoformat())
            }
            result.append(trophy_data)
        
        # Also include all available trophies with earned status
        earned_ids = {t.get('id') for t in user_trophies}
        for trophy_id, trophy_def in self.trophy_definitions.items():
            if trophy_id not in earned_ids:
                result.append({
                    'id': trophy_id,
                    'name': trophy_def['name'],
                    'description': trophy_def['description'],
                    'icon': trophy_def['icon'],
                    'points': trophy_def['points'],
                    'category': trophy_def['category'],
                    'earned': False,
                    'earnedDate': None
                })
        
        return result
    
    def get_user_trophy_points(self, user_id: str) -> int:
        """Get total trophy points for a user"""
        raw_trophies = self.trophies.get(user_id, [])
        return sum(t.get('points', 0) for t in raw_trophies)
    
    def get_trophy_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get trophy statistics for a user"""
        # Get raw trophies (earned only) for statistics
        raw_trophies = self.trophies.get(user_id, [])
        
        stats = {
            'total_trophies': len(raw_trophies),
            'total_points': self.get_user_trophy_points(user_id),
            'by_category': defaultdict(int),
            'recent_trophies': sorted(raw_trophies, key=lambda x: x.get('awarded_at', ''), reverse=True)[:5]
        }
        
        for trophy in raw_trophies:
            category = trophy.get('category', 'other')
            stats['by_category'][category] += 1
        
        return stats
    
    def _initialize_leveling_milestones(self) -> Dict[int, Dict[str, Any]]:
        """Initialize leveling milestones with title rewards"""
        return {
            1: {'title': 'Novice', 'description': 'Just starting your journey', 'reward_points': 0},
            5: {'title': 'Apprentice', 'description': 'Learning the craft', 'reward_points': 50},
            10: {'title': 'Creator', 'description': 'Making your mark', 'reward_points': 100},
            15: {'title': 'Storyteller', 'description': 'Weaving narratives', 'reward_points': 200},
            20: {'title': 'Director', 'description': 'Leading the vision', 'reward_points': 300},
            25: {'title': 'Producer', 'description': 'Bringing ideas to life', 'reward_points': 400},
            30: {'title': 'Master', 'description': 'Master of the craft', 'reward_points': 500},
            35: {'title': 'Virtuoso', 'description': 'Exceptional skill', 'reward_points': 600},
            40: {'title': 'Legend', 'description': 'Legendary status', 'reward_points': 750},
            50: {'title': 'Mythic', 'description': 'Mythical achievements', 'reward_points': 1000},
            60: {'title': 'Transcendent', 'description': 'Beyond ordinary limits', 'reward_points': 1500},
            75: {'title': 'Cosmic', 'description': 'Cosmic understanding', 'reward_points': 2000},
            100: {'title': 'Omniscient', 'description': 'All-knowing creator', 'reward_points': 3000}
        }
    
    def check_level_milestone(self, user_id: str, level: int) -> Optional[Dict[str, Any]]:
        """Check if user reached a level milestone and award title"""
        if level not in self.leveling_milestones:
            return None
        
        milestone = self.leveling_milestones[level]
        
        # Check if already awarded
        if user_id not in self.future_knowledge:
            self.future_knowledge[user_id] = {
                'current_title': 'Novice',
                'unlocked_titles': ['Novice'],
                'level_milestones': [],
                'knowledge_points': 0,
                'future_insights': []
            }
        
        user_knowledge = self.future_knowledge[user_id]
        
        # Check if milestone already reached
        if level in user_knowledge.get('level_milestones', []):
            return None
        
        # Award milestone
        user_knowledge['level_milestones'].append(level)
        user_knowledge['current_title'] = milestone['title']
        if milestone['title'] not in user_knowledge['unlocked_titles']:
            user_knowledge['unlocked_titles'].append(milestone['title'])
        user_knowledge['knowledge_points'] += milestone['reward_points']
        
        return {
            'level': level,
            'title': milestone['title'],
            'description': milestone['description'],
            'reward_points': milestone['reward_points'],
            'unlocked_at': datetime.utcnow().isoformat()
        }
    
    def add_future_knowledge(self, user_id: str, knowledge_type: str, data: Dict[str, Any]) -> None:
        """Add future knowledge insight to user profile"""
        if user_id not in self.future_knowledge:
            self.future_knowledge[user_id] = {
                'current_title': 'Novice',
                'unlocked_titles': ['Novice'],
                'level_milestones': [],
                'knowledge_points': 0,
                'future_insights': []
            }
        
        insight = {
            'type': knowledge_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
            'knowledge_points': data.get('points', 10)
        }
        
        self.future_knowledge[user_id]['future_insights'].append(insight)
        self.future_knowledge[user_id]['knowledge_points'] += insight['knowledge_points']
        
        # Limit to last 100 insights
        if len(self.future_knowledge[user_id]['future_insights']) > 100:
            self.future_knowledge[user_id]['future_insights'] = \
                self.future_knowledge[user_id]['future_insights'][-100:]
    
    def get_future_knowledge(self, user_id: str) -> Dict[str, Any]:
        """Get user's future knowledge profile"""
        if user_id not in self.future_knowledge:
            return {
                'current_title': 'Novice',
                'unlocked_titles': ['Novice'],
                'level_milestones': [],
                'knowledge_points': 0,
                'future_insights': []
            }
        return self.future_knowledge[user_id]
    
    def update_psychological_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        """Update psychological research profile"""
        if user_id not in self.psychological_profiles:
            self.psychological_profiles[user_id] = {
                'creativity_score': 0,
                'patience_score': 0,
                'detail_orientation': 0,
                'engagement_level': 0,
                'behavioral_patterns': [],
                'psychological_insights': [],
                'research_data': {}
            }
        
        profile = self.psychological_profiles[user_id]
        
        # Update scores
        if 'creativity' in profile_data:
            profile['creativity_score'] = profile_data['creativity']
        if 'patience' in profile_data:
            profile['patience_score'] = profile_data['patience']
        if 'detail_orientation' in profile_data:
            profile['detail_orientation'] = profile_data['detail_orientation']
        if 'engagement' in profile_data:
            profile['engagement_level'] = profile_data['engagement']
        
        # Add behavioral pattern
        if 'pattern' in profile_data:
            pattern = {
                'type': profile_data['pattern'],
                'timestamp': datetime.utcnow().isoformat(),
                'data': profile_data.get('pattern_data', {})
            }
            profile['behavioral_patterns'].append(pattern)
            
            # Limit to last 50 patterns
            if len(profile['behavioral_patterns']) > 50:
                profile['behavioral_patterns'] = profile['behavioral_patterns'][-50:]
        
        # Add psychological insight
        if 'insight' in profile_data:
            insight = {
                'type': profile_data['insight'],
                'timestamp': datetime.utcnow().isoformat(),
                'data': profile_data.get('insight_data', {})
            }
            profile['psychological_insights'].append(insight)
            
            # Limit to last 30 insights
            if len(profile['psychological_insights']) > 30:
                profile['psychological_insights'] = profile['psychological_insights'][-30:]
        
        # Merge research data
        if 'research_data' in profile_data:
            profile['research_data'].update(profile_data['research_data'])
    
    def get_psychological_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user's psychological research profile"""
        if user_id not in self.psychological_profiles:
            return {
                'creativity_score': 0,
                'patience_score': 0,
                'detail_orientation': 0,
                'engagement_level': 0,
                'behavioral_patterns': [],
                'psychological_insights': [],
                'research_data': {}
            }
        return self.psychological_profiles[user_id]
    
    def get_user_title(self, user_id: str) -> str:
        """Get user's current title"""
        knowledge = self.get_future_knowledge(user_id)
        return knowledge.get('current_title', 'Novice')
    
    def get_leveling_milestones(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all leveling milestones with completion status"""
        knowledge = self.get_future_knowledge(user_id)
        completed_milestones = knowledge.get('level_milestones', [])
        current_level = knowledge.get('current_level', 1)
        
        milestones = []
        for level, milestone_data in sorted(self.leveling_milestones.items()):
            is_completed = level in completed_milestones or level <= current_level
            milestones.append({
                'level_required': level,
                'title': milestone_data['title'],
                'description': milestone_data['description'],
                'reward_points': milestone_data['reward_points'],
                'completed': is_completed,
                'completed_at': None if not is_completed else datetime.utcnow().isoformat()
            })
        
        return milestones
    
    def get_title_progress(self, user_id: str, current_level: int) -> Dict[str, Any]:
        """Get progress towards next title milestone"""
        # Find next milestone
        next_milestone = None
        for level in sorted(self.leveling_milestones.keys()):
            if level > current_level:
                next_milestone = level
                break
        
        if not next_milestone:
            return {
                'has_next': False,
                'current_title': self.get_user_title(user_id),
                'next_title': None,
                'progress': 100
            }
        
        current_milestone = None
        for level in sorted(self.leveling_milestones.keys(), reverse=True):
            if level <= current_level:
                current_milestone = level
                break
        
        progress = ((current_level - (current_milestone or 0)) / 
                   (next_milestone - (current_milestone or 0))) * 100
        
        return {
            'has_next': True,
            'current_title': self.get_user_title(user_id),
            'next_title': self.leveling_milestones[next_milestone]['title'],
            'next_level': next_milestone,
            'current_level': current_level,
            'progress': min(100, max(0, progress))
        }


# Global instance
trophy_system = TrophySystem()

