"""Emotion, Trigger, and Relation System for Documentary Generation

This module implements a comprehensive system for:
- Emotional analysis and triggers during video generation
- Dynamic relations between content elements
- Special effects based on emotional context
- Safe, robust implementation with best practices
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


class EmotionType(Enum):
    """Emotion types that can be detected and triggered"""
    EXCITEMENT = "excitement"
    WONDER = "wonder"
    NOSTALGIA = "nostalgia"
    DRAMA = "drama"
    INSPIRATION = "inspiration"
    MYSTERY = "mystery"
    JOY = "joy"
    SERIOUSNESS = "seriousness"
    ADVENTURE = "adventure"
    PEACEFUL = "peaceful"


class TriggerType(Enum):
    """Trigger types that activate special effects"""
    VISUAL_ENHANCEMENT = "visual_enhancement"
    AUDIO_MODULATION = "audio_modulation"
    TRANSITION_EFFECT = "transition_effect"
    COLOR_GRADING = "color_grading"
    TEXT_OVERLAY = "text_overlay"
    MUSIC_SYNC = "music_sync"
    PACE_ADJUSTMENT = "pace_adjustment"
    FOCUS_SHIFT = "focus_shift"


class RelationType(Enum):
    """Relation types between content elements"""
    SEQUENTIAL = "sequential"  # Elements follow in sequence
    CONTRAST = "contrast"  # Elements contrast each other
    COMPLEMENT = "complement"  # Elements complement each other
    CAUSAL = "causal"  # One element causes another
    THEMATIC = "thematic"  # Elements share theme
    TEMPORAL = "temporal"  # Elements related by time


@dataclass
class EmotionProfile:
    """Profile of emotions detected in content"""
    primary_emotion: EmotionType
    secondary_emotions: List[EmotionType]
    intensity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    detected_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'primary_emotion': self.primary_emotion.value,
            'secondary_emotions': [e.value for e in self.secondary_emotions],
            'intensity': self.intensity,
            'confidence': self.confidence,
            'detected_at': self.detected_at.isoformat()
        }


@dataclass
class Trigger:
    """Trigger that activates special effects"""
    trigger_type: TriggerType
    emotion_context: EmotionType
    activation_condition: str  # Condition for activation
    effect_parameters: Dict[str, Any]
    priority: int  # Higher priority triggers first
    safe_mode: bool  # Whether to use safe/fallback effects
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trigger_type': self.trigger_type.value,
            'emotion_context': self.emotion_context.value,
            'activation_condition': self.activation_condition,
            'effect_parameters': self.effect_parameters,
            'priority': self.priority,
            'safe_mode': self.safe_mode
        }


@dataclass
class Relation:
    """Relation between content elements"""
    relation_type: RelationType
    source_element: str  # ID or identifier
    target_element: str  # ID or identifier
    strength: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'relation_type': self.relation_type.value,
            'source_element': self.source_element,
            'target_element': self.target_element,
            'strength': self.strength,
            'metadata': self.metadata
        }


class EmotionTriggerSystem:
    """Main system for emotion detection, trigger activation, and relation management"""
    
    # Emotion keywords mapping - IMPROVED with more keywords and better matching
    EMOTION_KEYWORDS = {
        EmotionType.EXCITEMENT: ['exciting', 'exciting', 'thrilling', 'thrilling', 'amazing', 'incredible', 'spectacular', 'breathtaking', 'adrenaline', 'pulse', 'heart-pounding'],
        EmotionType.WONDER: ['wonder', 'wonderful', 'mystery', 'mysterious', 'fascinating', 'curious', 'discover', 'marvel', 'awe', 'astonishing'],
        EmotionType.NOSTALGIA: ['remember', 'remembering', 'past', 'history', 'historical', 'ancient', 'old', 'tradition', 'heritage', 'memories', 'nostalgic'],
        EmotionType.DRAMA: ['dramatic', 'drama', 'intense', 'intensity', 'conflict', 'struggle', 'challenge', 'crisis', 'tension', 'climactic'],
        EmotionType.INSPIRATION: ['inspire', 'inspiring', 'inspiration', 'motivate', 'motivation', 'achieve', 'success', 'triumph', 'overcome', 'empower'],
        EmotionType.MYSTERY: ['mystery', 'mysterious', 'unknown', 'secret', 'secrets', 'hidden', 'enigma', 'puzzle', 'unexplained', 'cryptic'],
        EmotionType.JOY: ['happy', 'happiness', 'joy', 'joyful', 'celebration', 'festival', 'cheerful', 'delight', 'delightful', 'bliss'],
        EmotionType.SERIOUSNESS: ['serious', 'important', 'critical', 'significant', 'crucial', 'vital', 'essential', 'paramount', 'grave'],
        EmotionType.ADVENTURE: ['adventure', 'adventurous', 'explore', 'exploration', 'journey', 'expedition', 'quest', 'voyage', 'trek', 'odyssey'],
        EmotionType.PEACEFUL: ['peaceful', 'peace', 'calm', 'serene', 'tranquil', 'gentle', 'quiet', 'relaxing', 'soothing', 'zen']
    }
    
    # Safe effect parameters (fallback when unsafe effects fail)
    SAFE_EFFECT_PARAMETERS = {
        TriggerType.VISUAL_ENHANCEMENT: {
            'brightness': 1.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'sharpness': 1.0
        },
        TriggerType.AUDIO_MODULATION: {
            'volume': 0.8,
            'fade_in': 0.5,
            'fade_out': 0.5
        },
        TriggerType.TRANSITION_EFFECT: {
            'type': 'fade',
            'duration': 0.5
        },
        TriggerType.COLOR_GRADING: {
            'temperature': 0.0,
            'tint': 0.0,
            'exposure': 0.0
        }
    }
    
    def __init__(self):
        """Initialize the emotion trigger system"""
        self.emotion_profiles: Dict[str, EmotionProfile] = {}
        self.active_triggers: List[Trigger] = []
        self.relations: List[Relation] = []
        self.generation_context: Dict[str, Any] = {}
        
    def analyze_emotion(self, text: str, context: Optional[Dict[str, Any]] = None) -> EmotionProfile:
        """Analyze text to detect emotions
        
        Args:
            text: Text to analyze (prompt, description, script)
            context: Additional context (title, metadata, etc.)
            
        Returns:
            EmotionProfile with detected emotions
        """
        text_lower = text.lower()
        emotion_scores: Dict[EmotionType, float] = {}
        
        # IMPROVED: Score each emotion based on keyword matches with better weighting
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = 0.0
            matches = 0
            unique_matches = set()
            
            for keyword in keywords:
                # Use word boundary matching for better accuracy
                import re
                pattern = r'\b' + re.escape(keyword) + r'\b'
                count = len(re.findall(pattern, text_lower))
                if count > 0:
                    matches += count
                    unique_matches.add(keyword)
                    # Weight by keyword uniqueness (first occurrence is more important)
                    score += count * (1.0 / max(len(keywords), 1))  # Normalize by keyword count
            
            # Boost score if multiple unique keywords match
            if len(unique_matches) > 1:
                score *= (1.0 + len(unique_matches) * 0.1)  # 10% boost per unique match
            
            # Boost score if multiple total matches
            if matches > 2:
                score *= 1.3
            
            emotion_scores[emotion] = min(score, 1.0)  # Cap at 1.0
        
        # If no emotions detected, use default
        if not emotion_scores or max(emotion_scores.values()) == 0:
            primary_emotion = EmotionType.WONDER  # Default to wonder
            intensity = 0.5
            confidence = 0.3
        else:
            # Find primary emotion (highest score)
            primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            intensity = emotion_scores[primary_emotion]
            confidence = min(intensity * 1.5, 1.0)  # Confidence based on intensity
        
        # Find secondary emotions (top 2-3 after primary)
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        secondary_emotions = [
            emotion for emotion, score in sorted_emotions[1:4]
            if score > 0.2 and emotion != primary_emotion
        ]
        
        profile = EmotionProfile(
            primary_emotion=primary_emotion,
            secondary_emotions=secondary_emotions,
            intensity=intensity,
            confidence=confidence,
            detected_at=datetime.now(timezone.utc)
        )
        
        return profile
    
    def create_triggers_for_emotion(self, emotion_profile: EmotionProfile, 
                                    safe_mode: bool = True) -> List[Trigger]:
        """Create triggers based on emotion profile
        
        Args:
            emotion_profile: Detected emotion profile
            safe_mode: Whether to use safe effect parameters
            
        Returns:
            List of triggers to activate
        """
        triggers = []
        primary = emotion_profile.primary_emotion
        
        # Map emotions to appropriate triggers
        emotion_trigger_map = {
            EmotionType.EXCITEMENT: [
                (TriggerType.VISUAL_ENHANCEMENT, {'brightness': 1.1, 'saturation': 1.15, 'contrast': 1.1}),
                (TriggerType.AUDIO_MODULATION, {'volume': 1.0, 'fade_in': 0.3}),
                (TriggerType.PACE_ADJUSTMENT, {'speed_multiplier': 1.05})
            ],
            EmotionType.WONDER: [
                (TriggerType.COLOR_GRADING, {'temperature': 0.1, 'exposure': 0.1}),
                (TriggerType.TRANSITION_EFFECT, {'type': 'fade', 'duration': 0.8}),
                (TriggerType.FOCUS_SHIFT, {'blur_radius': 0.0, 'focus_strength': 1.0})
            ],
            EmotionType.DRAMA: [
                (TriggerType.COLOR_GRADING, {'temperature': -0.1, 'contrast': 1.2}),
                (TriggerType.AUDIO_MODULATION, {'volume': 0.9, 'fade_in': 0.7}),
                (TriggerType.TRANSITION_EFFECT, {'type': 'cut', 'duration': 0.2})
            ],
            EmotionType.INSPIRATION: [
                (TriggerType.VISUAL_ENHANCEMENT, {'brightness': 1.05, 'saturation': 1.1}),
                (TriggerType.TEXT_OVERLAY, {'style': 'motivational', 'opacity': 0.8}),
                (TriggerType.MUSIC_SYNC, {'tempo': 1.0, 'beat_match': True})
            ],
            EmotionType.MYSTERY: [
                (TriggerType.COLOR_GRADING, {'temperature': -0.2, 'exposure': -0.1}),
                (TriggerType.AUDIO_MODULATION, {'volume': 0.7, 'fade_in': 1.0}),
                (TriggerType.FOCUS_SHIFT, {'blur_radius': 0.1, 'focus_strength': 0.8})
            ],
            EmotionType.ADVENTURE: [
                (TriggerType.VISUAL_ENHANCEMENT, {'saturation': 1.2, 'contrast': 1.15}),
                (TriggerType.PACE_ADJUSTMENT, {'speed_multiplier': 1.1}),
                (TriggerType.TRANSITION_EFFECT, {'type': 'slide', 'duration': 0.6})
            ],
            EmotionType.PEACEFUL: [
                (TriggerType.COLOR_GRADING, {'temperature': 0.2, 'exposure': 0.05}),
                (TriggerType.AUDIO_MODULATION, {'volume': 0.6, 'fade_in': 1.5}),
                (TriggerType.PACE_ADJUSTMENT, {'speed_multiplier': 0.95})
            ]
        }
        
        # Get triggers for primary emotion
        trigger_configs = emotion_trigger_map.get(primary, [
            (TriggerType.VISUAL_ENHANCEMENT, self.SAFE_EFFECT_PARAMETERS[TriggerType.VISUAL_ENHANCEMENT])
        ])
        
        # Create triggers
        for i, (trigger_type, effect_params) in enumerate(trigger_configs):
            # Use safe parameters if safe_mode is enabled
            if safe_mode:
                safe_params = self.SAFE_EFFECT_PARAMETERS.get(trigger_type, {})
                # Merge safe params with effect params, prioritizing safe
                final_params = {**effect_params, **safe_params}
                # Ensure values are within safe ranges
                final_params = self._sanitize_parameters(trigger_type, final_params)
            else:
                final_params = self._sanitize_parameters(trigger_type, effect_params)
            
            trigger = Trigger(
                trigger_type=trigger_type,
                emotion_context=primary,
                activation_condition=f"emotion_{primary.value}_intensity_{emotion_profile.intensity:.2f}",
                effect_parameters=final_params,
                priority=100 - i * 10,  # Higher priority for first triggers
                safe_mode=safe_mode
            )
            triggers.append(trigger)
        
        return triggers
    
    def _sanitize_parameters(self, trigger_type: TriggerType, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to ensure safe values
        
        Args:
            trigger_type: Type of trigger
            params: Parameters to sanitize
            
        Returns:
            Sanitized parameters
        """
        sanitized = params.copy()
        
        # Define safe ranges for each parameter type
        safe_ranges = {
            'brightness': (0.5, 1.5),
            'contrast': (0.5, 1.5),
            'saturation': (0.5, 1.5),
            'sharpness': (0.5, 1.5),
            'volume': (0.0, 1.0),
            'fade_in': (0.0, 3.0),
            'fade_out': (0.0, 3.0),
            'temperature': (-0.5, 0.5),
            'tint': (-0.5, 0.5),
            'exposure': (-0.5, 0.5),
            'speed_multiplier': (0.5, 1.5),
            'blur_radius': (0.0, 0.5),
            'focus_strength': (0.5, 1.0),
            'opacity': (0.0, 1.0)
        }
        
        # Clamp values to safe ranges
        for key, value in sanitized.items():
            if key in safe_ranges:
                min_val, max_val = safe_ranges[key]
                sanitized[key] = max(min_val, min(max_val, value))
        
        return sanitized
    
    def detect_relations(self, elements: List[Dict[str, Any]]) -> List[Relation]:
        """Detect relations between content elements
        
        Args:
            elements: List of content elements (clips, images, scripts)
            
        Returns:
            List of detected relations
        """
        relations = []
        
        # Detect sequential relations (adjacent elements)
        for i in range(len(elements) - 1):
            relation = Relation(
                relation_type=RelationType.SEQUENTIAL,
                source_element=elements[i].get('id', f'element_{i}'),
                target_element=elements[i+1].get('id', f'element_{i+1}'),
                strength=0.8,
                metadata={'position': i, 'next_position': i+1}
            )
            relations.append(relation)
        
        # Detect thematic relations (similar content)
        for i, elem1 in enumerate(elements):
            for j, elem2 in enumerate(elements[i+1:], start=i+1):
                # Check for thematic similarity (simple keyword matching)
                text1 = (elem1.get('prompt', '') + ' ' + elem1.get('title', '')).lower()
                text2 = (elem2.get('prompt', '') + ' ' + elem2.get('title', '')).lower()
                
                # Count common words
                words1 = set(re.findall(r'\w+', text1))
                words2 = set(re.findall(r'\w+', text2))
                common_words = words1.intersection(words2)
                
                # IMPROVED: Better thematic relation detection
                # Remove common stop words for better matching
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
                meaningful_words1 = words1 - stop_words
                meaningful_words2 = words2 - stop_words
                meaningful_common = meaningful_words1.intersection(meaningful_words2)
                
                # Check for meaningful common words (at least 2, or 1 if it's a significant word)
                has_significant_word = any(len(w) > 4 for w in meaningful_common) if meaningful_common else False
                if len(meaningful_common) >= 2 or (len(meaningful_common) >= 1 and has_significant_word):
                    strength = min(len(meaningful_common) / 8.0, 1.0)
                    # Boost strength if words are longer (more significant)
                    avg_word_length = sum(len(w) for w in meaningful_common) / max(len(meaningful_common), 1)
                    if avg_word_length > 5:
                        strength = min(strength * 1.2, 1.0)
                    
                    relation = Relation(
                        relation_type=RelationType.THEMATIC,
                        source_element=elem1.get('id', f'element_{i}'),
                        target_element=elem2.get('id', f'element_{j}'),
                        strength=strength,
                        metadata={'common_words': list(meaningful_common), 'total_common': len(common_words)}
                    )
                    relations.append(relation)
        
        return relations
    
    def apply_triggers_to_generation(self, triggers: List[Trigger], 
                                     generation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply triggers to video generation process
        
        Args:
            triggers: List of active triggers
            generation_context: Current generation context
            
        Returns:
            Updated generation context with trigger effects applied
        """
        # Sort triggers by priority (higher first)
        sorted_triggers = sorted(triggers, key=lambda t: t.priority, reverse=True)
        
        applied_effects = {}
        
        for trigger in sorted_triggers:
            try:
                if trigger.trigger_type == TriggerType.VISUAL_ENHANCEMENT:
                    applied_effects['visual'] = trigger.effect_parameters
                elif trigger.trigger_type == TriggerType.AUDIO_MODULATION:
                    applied_effects['audio'] = trigger.effect_parameters
                elif trigger.trigger_type == TriggerType.COLOR_GRADING:
                    applied_effects['color'] = trigger.effect_parameters
                elif trigger.trigger_type == TriggerType.TRANSITION_EFFECT:
                    applied_effects['transition'] = trigger.effect_parameters
                elif trigger.trigger_type == TriggerType.PACE_ADJUSTMENT:
                    applied_effects['pace'] = trigger.effect_parameters
                elif trigger.trigger_type == TriggerType.FOCUS_SHIFT:
                    applied_effects['focus'] = trigger.effect_parameters
                
                # Log applied trigger
                print(f"[EmotionTrigger] Applied {trigger.trigger_type.value} for {trigger.emotion_context.value}")
                
            except Exception as e:
                print(f"[EmotionTrigger] Error applying trigger {trigger.trigger_type.value}: {e}")
                # Continue with other triggers even if one fails
        
        # Merge with existing context
        updated_context = {**generation_context, 'applied_effects': applied_effects}
        
        return updated_context
    
    def get_progress_message_with_emotion(self, emotion_profile: EmotionProfile, 
                                         base_message: str) -> str:
        """Enhance progress message with emotional context
        
        Args:
            emotion_profile: Current emotion profile
            base_message: Base progress message
            
        Returns:
            Enhanced message with emotional context
        """
        emotion_emojis = {
            EmotionType.EXCITEMENT: '⚡',
            EmotionType.WONDER: '✨',
            EmotionType.DRAMA: '🎭',
            EmotionType.INSPIRATION: '💫',
            EmotionType.ADVENTURE: '🗺️',
            EmotionType.PEACEFUL: '🌊',
            EmotionType.MYSTERY: '🔮',
            EmotionType.JOY: '🎉',
            EmotionType.NOSTALGIA: '📜',
            EmotionType.SERIOUSNESS: '📊'
        }
        
        emoji = emotion_emojis.get(emotion_profile.primary_emotion, '🎬')
        intensity_str = "high" if emotion_profile.intensity > 0.7 else "moderate" if emotion_profile.intensity > 0.4 else "subtle"
        
        return f"{emoji} {base_message} ({emotion_profile.primary_emotion.value.replace('_', ' ').title()} - {intensity_str} intensity)"
    
    def save_state(self, doc_id: str) -> Dict[str, Any]:
        """Save current system state
        
        Args:
            doc_id: Documentary ID
            
        Returns:
            State dictionary
        """
        return {
            'doc_id': doc_id,
            'emotion_profiles': {k: v.to_dict() for k, v in self.emotion_profiles.items()},
            'active_triggers': [t.to_dict() for t in self.active_triggers],
            'relations': [r.to_dict() for r in self.relations],
            'generation_context': self.generation_context,
            'saved_at': datetime.now(timezone.utc).isoformat()
        }
    
    def load_state(self, state: Dict[str, Any]) -> bool:
        """Load system state
        
        Args:
            state: State dictionary
            
        Returns:
            True if loaded successfully
        """
        try:
            # Reconstruct emotion profiles
            self.emotion_profiles = {}
            for k, v in state.get('emotion_profiles', {}).items():
                self.emotion_profiles[k] = EmotionProfile(
                    primary_emotion=EmotionType(v['primary_emotion']),
                    secondary_emotions=[EmotionType(e) for e in v['secondary_emotions']],
                    intensity=v['intensity'],
                    confidence=v['confidence'],
                    detected_at=datetime.fromisoformat(v['detected_at'])
                )
            
            # Reconstruct triggers
            self.active_triggers = [
                Trigger(
                    trigger_type=TriggerType(t['trigger_type']),
                    emotion_context=EmotionType(t['emotion_context']),
                    activation_condition=t['activation_condition'],
                    effect_parameters=t['effect_parameters'],
                    priority=t['priority'],
                    safe_mode=t['safe_mode']
                )
                for t in state.get('active_triggers', [])
            ]
            
            # Reconstruct relations
            self.relations = [
                Relation(
                    relation_type=RelationType(r['relation_type']),
                    source_element=r['source_element'],
                    target_element=r['target_element'],
                    strength=r['strength'],
                    metadata=r['metadata']
                )
                for r in state.get('relations', [])
            ]
            
            self.generation_context = state.get('generation_context', {})
            return True
            
        except Exception as e:
            print(f"[EmotionTrigger] Error loading state: {e}")
            return False

