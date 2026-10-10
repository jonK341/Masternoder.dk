"""
Nudging Behavior Modification System
Changes human behavior patterns through subtle psychological nudges
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random
import json
import uuid

try:
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.behavior_pattern_tracker import BehaviorPatternTracker
except ImportError:
    unified_point_counter = None
    BehaviorPatternTracker = None


class NudgingBehaviorSystem:
    """
    Nudging System - Subtle behavior modification through psychological nudges
    """
    
    def __init__(self):
        self.user_nudges = {}  # {user_id: nudge_data}
        self.nudge_history = defaultdict(list)  # {user_id: [nudge_events]}
        self.behavior_targets = {}  # {user_id: target_behaviors}
        self.nudge_types = self._initialize_nudge_types()
        self.nudge_effectiveness = defaultdict(dict)  # {user_id: {nudge_type: effectiveness}}
    
    def _initialize_nudge_types(self) -> Dict[str, Dict[str, Any]]:
        """Initialize types of nudges available"""
        return {
            'positive_reinforcement': {
                'name': 'Positive Reinforcement',
                'description': 'Reward desired behaviors',
                'strength': 0.3,
                'persistence': 0.5,
                'subtlety': 0.8
            },
            'social_proof': {
                'name': 'Social Proof',
                'description': 'Show others doing the desired behavior',
                'strength': 0.4,
                'persistence': 0.6,
                'subtlety': 0.7
            },
            'loss_aversion': {
                'name': 'Loss Aversion',
                'description': 'Highlight what they might lose',
                'strength': 0.5,
                'persistence': 0.7,
                'subtlety': 0.6
            },
            'default_effect': {
                'name': 'Default Effect',
                'description': 'Set desired behavior as default',
                'strength': 0.6,
                'persistence': 0.8,
                'subtlety': 0.5
            },
            'framing': {
                'name': 'Framing',
                'description': 'Frame information to influence decisions',
                'strength': 0.4,
                'persistence': 0.5,
                'subtlety': 0.9
            },
            'reciprocity': {
                'name': 'Reciprocity',
                'description': 'Give something to encourage reciprocation',
                'strength': 0.5,
                'persistence': 0.6,
                'subtlety': 0.7
            },
            'commitment': {
                'name': 'Commitment & Consistency',
                'description': 'Get small commitments that lead to larger ones',
                'strength': 0.7,
                'persistence': 0.9,
                'subtlety': 0.6
            },
            'scarcity': {
                'name': 'Scarcity',
                'description': 'Create sense of limited availability',
                'strength': 0.6,
                'persistence': 0.5,
                'subtlety': 0.5
            }
        }
    
    def set_behavior_target(self, user_id: str, target_behavior: str, 
                           nudge_type: str = None, strength: float = 0.5) -> Dict[str, Any]:
        """
        Set a target behavior to nudge user towards
        
        Args:
            user_id: User identifier
            target_behavior: Behavior to encourage (e.g., 'video_generation', 'battle_participation', 'social_interaction')
            nudge_type: Type of nudge to use (default: best for behavior)
            strength: Nudge strength (0.0-1.0)
        """
        if nudge_type is None:
            # Auto-select best nudge type for behavior
            nudge_type = self._select_best_nudge(target_behavior)
        
        if nudge_type not in self.nudge_types:
            nudge_type = 'positive_reinforcement'  # Default
        
        target_id = f"target_{uuid.uuid4().hex[:12]}"
        target = {
            'target_id': target_id,
            'user_id': user_id,
            'target_behavior': target_behavior,
            'nudge_type': nudge_type,
            'strength': min(1.0, max(0.0, strength)),
            'created_at': datetime.utcnow().isoformat(),
            'active': True,
            'effectiveness': 0.0,
            'attempts': 0,
            'successes': 0
        }
        
        if user_id not in self.behavior_targets:
            self.behavior_targets[user_id] = []
        
        self.behavior_targets[user_id].append(target)
        
        return {
            'success': True,
            'target': target,
            'message': f'Behavior target set: {target_behavior}'
        }
    
    def _select_best_nudge(self, target_behavior: str) -> str:
        """Select best nudge type for target behavior"""
        behavior_nudge_map = {
            'video_generation': 'positive_reinforcement',
            'battle_participation': 'social_proof',
            'social_interaction': 'reciprocity',
            'engagement': 'commitment',
            'retention': 'loss_aversion',
            'premium_purchase': 'scarcity',
            'content_creation': 'framing',
            'regular_activity': 'default_effect'
        }
        
        return behavior_nudge_map.get(target_behavior.lower(), 'positive_reinforcement')
    
    def apply_nudge(self, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply a nudge to the user based on their active targets
        
        Args:
            user_id: User identifier
            context: Current context (current_action, page, etc.)
        """
        if user_id not in self.behavior_targets:
            return {'success': False, 'error': 'No behavior targets set'}
        
        active_targets = [t for t in self.behavior_targets[user_id] if t.get('active', True)]
        if not active_targets:
            return {'success': False, 'error': 'No active targets'}
        
        # Select target to nudge (prioritize high-strength, low-effectiveness)
        target = self._select_target_to_nudge(active_targets)
        nudge_type = self.nudge_types[target['nudge_type']]
        
        # Generate nudge content
        nudge_content = self._generate_nudge_content(
            target['target_behavior'],
            target['nudge_type'],
            target['strength'],
            context
        )
        
        # Create nudge event
        nudge_id = f"nudge_{uuid.uuid4().hex[:12]}"
        nudge_event = {
            'nudge_id': nudge_id,
            'user_id': user_id,
            'target_id': target['target_id'],
            'target_behavior': target['target_behavior'],
            'nudge_type': target['nudge_type'],
            'strength': target['strength'],
            'content': nudge_content,
            'applied_at': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self.nudge_history[user_id].append(nudge_event)
        target['attempts'] += 1
        
        # Store active nudge
        if user_id not in self.user_nudges:
            self.user_nudges[user_id] = {}
        self.user_nudges[user_id][nudge_id] = nudge_event
        
        return {
            'success': True,
            'nudge': nudge_event,
            'message': 'Nudge applied'
        }
    
    def _select_target_to_nudge(self, targets: List[Dict]) -> Dict:
        """Select which target to nudge (prioritize high impact, low effectiveness)"""
        if len(targets) == 1:
            return targets[0]
        
        # Score targets: (strength * 0.5) + ((1 - effectiveness) * 0.5)
        scored_targets = []
        for target in targets:
            effectiveness = target.get('effectiveness', 0.0)
            score = (target['strength'] * 0.5) + ((1.0 - effectiveness) * 0.5)
            scored_targets.append((score, target))
        
        # Sort by score (descending) and return top
        scored_targets.sort(key=lambda x: x[0], reverse=True)
        return scored_targets[0][1]
    
    def _generate_nudge_content(self, target_behavior: str, nudge_type: str, 
                               strength: float, context: Dict = None) -> Dict[str, Any]:
        """Generate nudge content based on type and behavior"""
        templates = {
            'positive_reinforcement': {
                'video_generation': [
                    'You\'re doing great! Generate another video to earn bonus points.',
                    'Keep creating! Each video brings you closer to new achievements.',
                    'Your creativity is amazing! Ready to make another masterpiece?'
                ],
                'battle_participation': [
                    'Victory awaits! Join a battle to test your skills.',
                    'You\'re a strong fighter! Ready for the next challenge?',
                    'Battle wins unlock exclusive rewards. Ready to fight?'
                ],
                'social_interaction': [
                    'Connect with others! Share your creations.',
                    'The community would love to see what you\'ve made!',
                    'Join the conversation and grow your network.'
                ]
            },
            'social_proof': {
                'video_generation': [
                    'Join 10,000+ creators making amazing videos!',
                    'Most users generate 5+ videos per week. How many will you make?',
                    'Top creators are generating videos right now. Don\'t miss out!'
                ],
                'battle_participation': [
                    '100 players just won battles. Will you be next?',
                    'Join the weekly battle tournament with 500+ participants!',
                    'Top fighters battle daily. Ready to compete?'
                ]
            },
            'loss_aversion': {
                'video_generation': [
                    'Don\'t miss out on today\'s bonus XP for video creation!',
                    'Your video generation streak will end soon. Keep it going!',
                    'Limited time: Double points for videos created today!'
                ],
                'battle_participation': [
                    'Your battle ranking is about to expire. Defend it!',
                    'Don\'t lose your place on the leaderboard. Battle now!',
                    'Limited rewards available. Claim them before they\'re gone!'
                ]
            },
            'default_effect': {
                'video_generation': [
                    'Video generation is enabled by default. Just click to start!',
                    'Your next video is ready to create. One click away!',
                    'Quick generation mode is active. Create instantly!'
                ]
            },
            'framing': {
                'video_generation': [
                    'Think of it as creative expression, not work!',
                    'Video creation is a fun way to express yourself.',
                    'Turn your ideas into reality with video generation!'
                ]
            },
            'reciprocity': {
                'video_generation': [
                    'We\'ve given you bonus credits. Create a video to show your appreciation!',
                    'As a thank you, here\'s a free video generation!',
                    'You\'ve received a gift. Time to create something amazing!'
                ]
            },
            'commitment': {
                'video_generation': [
                    'You said you wanted to create more videos. Here\'s your chance!',
                    'Remember your goal? Today\'s the day to take action!',
                    'You committed to creating content. Let\'s do it!'
                ]
            },
            'scarcity': {
                'video_generation': [
                    'Only 3 premium video slots left today!',
                    'Limited availability: Generate before others claim the spot!',
                    'Exclusive video generation opportunity - ends soon!'
                ]
            }
        }
        
        # Get template list
        template_list = templates.get(nudge_type, {}).get(target_behavior, [
            f'Try {target_behavior.replace("_", " ")} now!'
        ])
        
        # Select based on strength
        template = random.choice(template_list)
        
        return {
            'text': template,
            'type': nudge_type,
            'strength': strength,
            'visual_cue': self._get_visual_cue(nudge_type, strength),
            'action_suggestion': target_behavior
        }
    
    def _get_visual_cue(self, nudge_type: str, strength: float) -> str:
        """Get visual cue for nudge"""
        cues = {
            'positive_reinforcement': '🎉',
            'social_proof': '👥',
            'loss_aversion': '⏰',
            'default_effect': '✅',
            'framing': '💡',
            'reciprocity': '🎁',
            'commitment': '📌',
            'scarcity': '🔥'
        }
        return cues.get(nudge_type, '✨')
    
    def track_nudge_success(self, user_id: str, nudge_id: str, 
                           behavior_performed: bool) -> Dict[str, Any]:
        """
        Track if nudge was successful (user performed desired behavior)
        
        Args:
            user_id: User identifier
            nudge_id: Nudge identifier
            behavior_performed: Whether user performed the desired behavior
        """
        if user_id not in self.user_nudges or nudge_id not in self.user_nudges[user_id]:
            return {'success': False, 'error': 'Nudge not found'}
        
        nudge = self.user_nudges[user_id][nudge_id]
        target_id = nudge['target_id']
        
        # Find target
        target = None
        if user_id in self.behavior_targets:
            for t in self.behavior_targets[user_id]:
                if t['target_id'] == target_id:
                    target = t
                    break
        
        if target:
            if behavior_performed:
                target['successes'] += 1
                # Update effectiveness
                if target['attempts'] > 0:
                    target['effectiveness'] = target['successes'] / target['attempts']
            
            # Update nudge type effectiveness
            nudge_type = target['nudge_type']
            if user_id not in self.nudge_effectiveness:
                self.nudge_effectiveness[user_id] = {}
            if nudge_type not in self.nudge_effectiveness[user_id]:
                self.nudge_effectiveness[user_id][nudge_type] = {
                    'attempts': 0,
                    'successes': 0,
                    'effectiveness': 0.0
                }
            
            nudge_effect = self.nudge_effectiveness[user_id][nudge_type]
            nudge_effect['attempts'] += 1
            if behavior_performed:
                nudge_effect['successes'] += 1
            nudge_effect['effectiveness'] = nudge_effect['successes'] / nudge_effect['attempts']
        
        return {
            'success': True,
            'behavior_performed': behavior_performed,
            'target_effectiveness': target['effectiveness'] if target else 0.0,
            'nudge_type_effectiveness': nudge_effect.get('effectiveness', 0.0) if target else 0.0
        }
    
    def get_user_nudges(self, user_id: str) -> Dict[str, Any]:
        """Get all nudges and targets for a user"""
        targets = self.behavior_targets.get(user_id, [])
        active_nudges = self.user_nudges.get(user_id, {})
        nudge_history = self.nudge_history.get(user_id, [])
        effectiveness = self.nudge_effectiveness.get(user_id, {})
        
        return {
            'success': True,
            'user_id': user_id,
            'targets': targets,
            'active_nudges': list(active_nudges.values()),
            'nudge_history': nudge_history[-50:],  # Last 50
            'effectiveness': effectiveness
        }
    
    def update_behavior_pattern(self, user_id: str, behavior_type: str, 
                               performed: bool) -> Dict[str, Any]:
        """
        Update behavior pattern tracking and trigger nudges if needed
        """
        # Check if this behavior matches any targets
        if user_id in self.behavior_targets:
            for target in self.behavior_targets[user_id]:
                if target['target_behavior'] == behavior_type and target.get('active', True):
                    # Mark as successful if performed
                    if performed:
                        # Find recent nudge for this target
                        recent_nudges = [
                            n for n in self.nudge_history.get(user_id, [])
                            if n['target_id'] == target['target_id']
                            and (datetime.fromisoformat(n['applied_at'].replace('Z', '+00:00')) - 
                                 datetime.utcnow().replace(tzinfo=None)) < timedelta(hours=1)
                        ]
                        if recent_nudges:
                            self.track_nudge_success(user_id, recent_nudges[-1]['nudge_id'], True)
        
        return {'success': True, 'behavior_tracked': behavior_type}


# Global instance
nudging_behavior_system = NudgingBehaviorSystem()

