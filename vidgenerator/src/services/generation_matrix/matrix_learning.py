"""
Matrix Learning System
Continuously improves the generation matrix based on successful patterns
"""
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path


class MatrixLearningSystem:
    """Learns from generation patterns and improves matrix decisions"""
    
    def __init__(self, knowledge_file: str = None):
        self.knowledge_file = knowledge_file or 'matrix_knowledge.json'
        self.knowledge = self._load_knowledge()
        self.learning_rate = 0.15  # How fast to adapt
        
    def _load_knowledge(self) -> Dict[str, Any]:
        """Load accumulated knowledge from file"""
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[MatrixLearning] Error loading knowledge: {e}")
        
        return {
            'successful_patterns': [],
            'failed_patterns': [],
            'quality_scores': {},
            'performance_metrics': {},
            'user_preferences': {},
            'generation_count': 0,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _save_knowledge(self):
        """Save accumulated knowledge to file"""
        try:
            self.knowledge['last_updated'] = datetime.utcnow().isoformat()
            with open(self.knowledge_file, 'w') as f:
                json.dump(self.knowledge, f, indent=2)
        except Exception as e:
            print(f"[MatrixLearning] Error saving knowledge: {e}")
    
    def record_successful_generation(self, pattern: Dict[str, Any], result: Dict[str, Any]):
        """Record a successful generation pattern"""
        self.knowledge['generation_count'] = self.knowledge.get('generation_count', 0) + 1
        
        pattern_entry = {
            'pattern': pattern,
            'result': result,
            'timestamp': datetime.utcnow().isoformat(),
            'generation_id': self.knowledge['generation_count']
        }
        
        self.knowledge['successful_patterns'].append(pattern_entry)
        
        # Keep only last 1000 successful patterns
        if len(self.knowledge['successful_patterns']) > 1000:
            self.knowledge['successful_patterns'] = self.knowledge['successful_patterns'][-1000:]
        
        # Update quality scores
        if 'clips' in result:
            for clip in result.get('clips', []):
                clip_id = clip.get('id', 'unknown')
                quality = clip.get('quality_score', 0.5)
                
                if clip_id not in self.knowledge['quality_scores']:
                    self.knowledge['quality_scores'][clip_id] = []
                
                self.knowledge['quality_scores'][clip_id].append(quality)
                
                # Keep only last 100 scores per clip
                if len(self.knowledge['quality_scores'][clip_id]) > 100:
                    self.knowledge['quality_scores'][clip_id] = self.knowledge['quality_scores'][clip_id][-100:]
        
        self._save_knowledge()
    
    def record_failed_generation(self, pattern: Dict[str, Any], error: str):
        """Record a failed generation pattern"""
        pattern_entry = {
            'pattern': pattern,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.knowledge['failed_patterns'].append(pattern_entry)
        
        # Keep only last 500 failed patterns
        if len(self.knowledge['failed_patterns']) > 500:
            self.knowledge['failed_patterns'] = self.knowledge['failed_patterns'][-500:]
        
        self._save_knowledge()
    
    def get_optimal_pattern(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimal pattern based on learned knowledge"""
        # Find similar successful patterns
        similar_patterns = []
        
        for pattern_entry in self.knowledge['successful_patterns']:
            pattern = pattern_entry['pattern']
            similarity = self._calculate_similarity(pattern, context)
            if similarity > 0.5:  # Threshold for similarity
                similar_patterns.append({
                    'pattern': pattern,
                    'similarity': similarity,
                    'result': pattern_entry['result']
                })
        
        # Sort by similarity
        similar_patterns.sort(key=lambda x: x['similarity'], reverse=True)
        
        if similar_patterns:
            # Use most similar successful pattern
            best_pattern = similar_patterns[0]['pattern']
            # Adapt it to current context
            return self._adapt_pattern(best_pattern, context)
        
        # No similar patterns found, return default
        return self._get_default_pattern(context)
    
    def _calculate_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between two patterns"""
        similarity = 0.0
        matches = 0
        
        # Compare key fields
        for key in ['prompt_type', 'duration', 'style', 'theme']:
            if key in pattern1 and key in pattern2:
                if pattern1[key] == pattern2[key]:
                    similarity += 0.25
                matches += 1
        
        if matches > 0:
            similarity = similarity / matches
        
        return similarity
    
    def _adapt_pattern(self, base_pattern: Dict, context: Dict) -> Dict:
        """Adapt a pattern to current context"""
        adapted = base_pattern.copy()
        
        # Update with context-specific values
        for key in context:
            if key in adapted:
                # Blend old and new values
                if isinstance(adapted[key], (int, float)) and isinstance(context[key], (int, float)):
                    adapted[key] = adapted[key] * (1 - self.learning_rate) + context[key] * self.learning_rate
                else:
                    adapted[key] = context[key]
            else:
                adapted[key] = context[key]
        
        return adapted
    
    def _get_default_pattern(self, context: Dict) -> Dict:
        """Get default pattern when no similar patterns found"""
        return {
            'prompt_type': context.get('prompt_type', 'general'),
            'duration': context.get('duration', 10),
            'style': context.get('style', 'documentary'),
            'theme': context.get('theme', 'default'),
            'quality_priority': 0.5,
            'speed_priority': 0.3,
            'creativity_priority': 0.2
        }
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Update learned user preferences"""
        if user_id not in self.knowledge['user_preferences']:
            self.knowledge['user_preferences'][user_id] = {}
        
        # Merge preferences with learning rate
        for key, value in preferences.items():
            if key in self.knowledge['user_preferences'][user_id]:
                # Blend old and new
                if isinstance(value, (int, float)):
                    old_value = self.knowledge['user_preferences'][user_id][key]
                    self.knowledge['user_preferences'][user_id][key] = (
                        old_value * (1 - self.learning_rate) + value * self.learning_rate
                    )
                else:
                    self.knowledge['user_preferences'][user_id][key] = value
            else:
                self.knowledge['user_preferences'][user_id][key] = value
        
        self._save_knowledge()
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get learned preferences for a user"""
        return self.knowledge['user_preferences'].get(user_id, {})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            'total_generations': self.knowledge.get('generation_count', 0),
            'successful_patterns': len(self.knowledge.get('successful_patterns', [])),
            'failed_patterns': len(self.knowledge.get('failed_patterns', [])),
            'success_rate': (
                len(self.knowledge.get('successful_patterns', [])) /
                max(1, len(self.knowledge.get('successful_patterns', [])) + len(self.knowledge.get('failed_patterns', [])))
            ),
            'tracked_clips': len(self.knowledge.get('quality_scores', {})),
            'users_tracked': len(self.knowledge.get('user_preferences', {}))
        }

