"""
Experience Point (XP) System with Behavioral Tracking
Gathers psychological information about users for generation optimization
"""
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class XPSystem:
    """Experience Point and Behavioral Tracking System"""
    
    def __init__(self):
        self.behavioral_data = {}  # {user_id: BehavioralProfile}
        self.xp_history = {}  # {user_id: List[XPEvent]}
        self.psychological_profiles = {}  # {user_id: PsychologicalProfile}
        
    def track_action(self, user_id: str, action_type: str, metadata: Dict[str, Any] = None) -> int:
        """
        Track user action and award XP
        
        Args:
            user_id: Unique user identifier
            action_type: Type of action (e.g., 'generate_video', 'watch_video', 'share', 'like')
            metadata: Additional action metadata
        
        Returns:
            XP awarded for this action
        """
        if metadata is None:
            metadata = {}
        
        # XP values for different actions
        xp_values = {
            'generate_video': 100,
            'watch_video': 10,
            'share_video': 25,
            'like_video': 5,
            'comment': 15,
            'complete_generation': 50,
            'retry_generation': 20,
            'customize_prompt': 15,
            'use_advanced_features': 30,
            'return_user': 5,  # Daily return bonus
        }
        
        xp_awarded = xp_values.get(action_type, 5)
        
        # Record XP event
        if user_id not in self.xp_history:
            self.xp_history[user_id] = []
        
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action_type,
            'xp_awarded': xp_awarded,
            'metadata': metadata
        }
        self.xp_history[user_id].append(event)
        
        # Update behavioral profile
        self._update_behavioral_profile(user_id, action_type, metadata)
        
        # Update psychological profile
        self._update_psychological_profile(user_id, action_type, metadata)
        
        return xp_awarded
    
    def _update_behavioral_profile(self, user_id: str, action_type: str, metadata: Dict):
        """Update user's behavioral profile"""
        if user_id not in self.behavioral_data:
            self.behavioral_data[user_id] = {
                'total_xp': 0,
                'level': 1,
                'actions': defaultdict(int),
                'preferences': {},
                'patterns': {},
                'last_active': None,
                'session_count': 0,
                'total_generations': 0,
                'total_watches': 0,
                'avg_generation_time': 0,
                'preferred_durations': [],
                'preferred_themes': [],
                'engagement_score': 0.0
            }
        
        profile = self.behavioral_data[user_id]
        profile['total_xp'] += self.xp_history[user_id][-1]['xp_awarded']
        profile['actions'][action_type] += 1
        profile['last_active'] = datetime.utcnow().isoformat()
        
        # Calculate level (every 1000 XP = 1 level)
        old_level = profile.get('level', 1)
        profile['level'] = (profile['total_xp'] // 1000) + 1
        
        # Check for level milestone and award title
        if profile['level'] > old_level:
            try:
                from src.services.behavioral_tracking.trophy_system import trophy_system
                milestone = trophy_system.check_level_milestone(user_id, profile['level'])
                if milestone:
                    print(f"[Trophy] User {user_id} reached level {profile['level']} milestone: {milestone['title']}")
            except ImportError:
                pass  # Trophy system not available
        
        # Update specific metrics
        if action_type == 'generate_video':
            profile['total_generations'] += 1
            if 'duration' in metadata:
                profile['preferred_durations'].append(metadata['duration'])
        elif action_type == 'watch_video':
            profile['total_watches'] += 1
        elif action_type == 'customize_prompt':
            if 'theme' in metadata:
                profile['preferred_themes'].append(metadata['theme'])
        
        # Calculate engagement score (0-100)
        profile['engagement_score'] = self._calculate_engagement_score(profile)
    
    def _update_psychological_profile(self, user_id: str, action_type: str, metadata: Dict):
        """Update user's psychological profile for AI generation optimization"""
        if user_id not in self.psychological_profiles:
            self.psychological_profiles[user_id] = {
                'creativity_level': 0.5,  # 0-1 scale
                'patience_level': 0.5,    # 0-1 scale
                'detail_orientation': 0.5,  # 0-1 scale
                'risk_taking': 0.5,       # 0-1 scale
                'preferred_complexity': 0.5,  # 0-1 scale
                'emotional_resonance': {},  # Emotion -> frequency
                'attention_span': 0.0,    # Average watch time
                'preferred_content_type': [],
                'generation_patterns': {},
                'optimization_hints': {}
            }
        
        profile = self.psychological_profiles[user_id]
        
        # Analyze behavior patterns
        if action_type == 'generate_video':
            # Analyze prompt complexity
            if 'prompt_length' in metadata:
                complexity = min(metadata['prompt_length'] / 500, 1.0)
                profile['preferred_complexity'] = (profile['preferred_complexity'] * 0.9) + (complexity * 0.1)
            
            # Track retry behavior (indicates patience)
            if 'retry_count' in metadata:
                patience = max(0, 1.0 - (metadata['retry_count'] * 0.1))
                profile['patience_level'] = (profile['patience_level'] * 0.9) + (patience * 0.1)
        
        elif action_type == 'watch_video':
            # Track watch time (attention span)
            if 'watch_duration' in metadata and 'video_duration' in metadata:
                completion_rate = metadata['watch_duration'] / metadata['video_duration']
                profile['attention_span'] = (profile['attention_span'] * 0.9) + (completion_rate * 0.1)
        
        # Generate optimization hints for AI generation
        profile['optimization_hints'] = self._generate_optimization_hints(profile)
    
    def _calculate_engagement_score(self, profile: Dict) -> float:
        """Calculate user engagement score (0-100)"""
        score = 0.0
        
        # Base score from XP
        score += min(profile['total_xp'] / 100, 30.0)
        
        # Activity diversity
        unique_actions = len(profile['actions'])
        score += min(unique_actions * 5, 20.0)
        
        # Return frequency
        if profile['session_count'] > 0:
            score += min(profile['session_count'] * 2, 20.0)
        
        # Generation activity
        score += min(profile['total_generations'] * 3, 30.0)
        
        return min(score, 100.0)
    
    def _generate_optimization_hints(self, profile: Dict) -> Dict[str, Any]:
        """Generate optimization hints for AI generation based on psychological profile"""
        hints = {
            'preferred_clip_duration': 10,  # Default
            'preferred_documentary_duration': 300,  # Default 5 min
            'complexity_level': profile.get('preferred_complexity', 0.5),
            'detail_level': profile.get('detail_orientation', 0.5),
            'creativity_boost': profile.get('creativity_level', 0.5),
            'patience_factor': profile.get('patience_level', 0.5),
            'theme_preferences': [],
            'style_preferences': [],
            'optimization_priority': 'balanced'  # balanced, speed, quality, creativity
        }
        
        # Adjust based on psychological profile
        if profile.get('patience_level', 0.5) < 0.3:
            hints['optimization_priority'] = 'speed'
        elif profile.get('detail_orientation', 0.5) > 0.7:
            hints['optimization_priority'] = 'quality'
        elif profile.get('creativity_level', 0.5) > 0.7:
            hints['optimization_priority'] = 'creativity'
        
        # Adjust durations based on attention span
        attention = profile.get('attention_span', 0.5)
        if attention < 0.3:
            hints['preferred_clip_duration'] = 5  # Shorter clips
            hints['preferred_documentary_duration'] = 180  # 3 min
        elif attention > 0.7:
            hints['preferred_clip_duration'] = 15  # Longer clips
            hints['preferred_documentary_duration'] = 600  # 10 min
        
        return hints
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with XP, trophies, future knowledge, and psychological data"""
        behavioral = self.behavioral_data.get(user_id, {})
        psychological = self.psychological_profiles.get(user_id, {})
        
        # Get future knowledge and title (with fallback if trophy system unavailable)
        try:
            from src.services.behavioral_tracking.trophy_system import trophy_system
            future_knowledge = trophy_system.get_future_knowledge(user_id)
            title_progress = trophy_system.get_title_progress(user_id, behavioral.get('level', 1))
            psychological_research = trophy_system.get_psychological_profile(user_id)
        except ImportError:
            # Fallback if trophy system not available
            future_knowledge = {
                'current_title': 'Novice',
                'unlocked_titles': ['Novice'],
                'level_milestones': [],
                'knowledge_points': 0,
                'future_insights': []
            }
            title_progress = {
                'has_next': False,
                'current_title': 'Novice',
                'next_title': None,
                'progress': 100
            }
            psychological_research = {
                'creativity_score': 0,
                'patience_score': 0,
                'detail_orientation': 0,
                'engagement_level': 0,
                'behavioral_patterns': [],
                'psychological_insights': [],
                'research_data': {}
            }
        
        return {
            'user_id': user_id,
            'behavioral': behavioral,
            'psychological': psychological,
            'optimization_hints': psychological.get('optimization_hints', {}),
            'xp_total': behavioral.get('total_xp', 0),
            'level': behavioral.get('level', 1),
            'engagement_score': behavioral.get('engagement_score', 0.0),
            'future_knowledge': future_knowledge,
            'title': {
                'current': future_knowledge.get('current_title', 'Novice'),
                'unlocked': future_knowledge.get('unlocked_titles', ['Novice']),
                'progress': title_progress,
                'knowledge_points': future_knowledge.get('knowledge_points', 0)
            },
            'psychological_research': psychological_research
        }
    
    def get_generation_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get AI generation recommendations based on user profile"""
        profile = self.get_user_profile(user_id)
        hints = profile.get('optimization_hints', {})
        
        return {
            'clip_duration_range': (
                max(5, hints.get('preferred_clip_duration', 10) - 5),
                min(15, hints.get('preferred_clip_duration', 10) + 5)
            ),
            'target_duration_range': (
                max(180, hints.get('preferred_documentary_duration', 300) - 120),
                min(600, hints.get('preferred_documentary_duration', 300) + 120)
            ),
            'complexity_level': hints.get('complexity_level', 0.5),
            'optimization_priority': hints.get('optimization_priority', 'balanced'),
            'creativity_boost': hints.get('creativity_boost', 0.5),
            'quality_settings': {
                'resolution': '1280x768' if hints.get('detail_orientation', 0.5) < 0.7 else '1920x1080',
                'fps': 24 if hints.get('optimization_priority') == 'speed' else 30
            }
        }
    
    def save_to_storage(self, storage_key: str = 'xp_system_data'):
        """Save XP system data to browser storage (for service worker)"""
        data = {
            'behavioral_data': self.behavioral_data,
            'xp_history': self.xp_history,
            'psychological_profiles': self.psychological_profiles,
            'timestamp': datetime.utcnow().isoformat()
        }
        return json.dumps(data)
    
    def load_from_storage(self, data_json: str):
        """Load XP system data from browser storage"""
        data = json.loads(data_json)
        self.behavioral_data = data.get('behavioral_data', {})
        self.xp_history = data.get('xp_history', {})
        self.psychological_profiles = data.get('psychological_profiles', {})


# Global instance
xp_system = XPSystem()

