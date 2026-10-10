"""
Matrix Learning Integration
Integrates the matrix learning system into the pipeline
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Try to import matrix learning system
try:
    from src.services.generation_matrix.matrix_learning import MatrixLearningSystem
    MATRIX_LEARNING_AVAILABLE = True
except ImportError:
    MATRIX_LEARNING_AVAILABLE = False
    print("[MatrixLearning] Matrix learning system not available")


def get_matrix_learning_system(knowledge_file: Optional[str] = None) -> Optional[Any]:
    """Get matrix learning system instance"""
    if not MATRIX_LEARNING_AVAILABLE:
        return None
    
    try:
        if knowledge_file is None:
            # Default knowledge file location
            base_dir = Path(__file__).parent.parent.parent.parent
            knowledge_file = str(base_dir / 'matrix_knowledge.json')
        
        return MatrixLearningSystem(knowledge_file=knowledge_file)
    except Exception as e:
        print(f"[MatrixLearning] Error initializing: {e}")
        return None


def record_generation_pattern(
    learning_system: Any,
    prompt: str,
    title: str,
    result: Dict[str, Any],
    doc_id: str
):
    """Record a generation pattern for learning"""
    if not learning_system:
        return
    
    try:
        # Extract pattern from generation context
        pattern = {
            'prompt_type': _classify_prompt_type(prompt),
            'duration': result.get('duration', 180),
            'style': 'documentary',
            'theme': result.get('theme', 'default'),
            'clips_count': result.get('video_clips_count', 0),
            'success': result.get('success', False)
        }
        
        if result.get('success'):
            learning_system.record_successful_generation(pattern, result)
            print(f"[MatrixLearning] Recorded successful generation pattern for {doc_id}")
        else:
            error = result.get('error', 'Unknown error')
            learning_system.record_failed_generation(pattern, error)
            print(f"[MatrixLearning] Recorded failed generation pattern for {doc_id}")
            
    except Exception as e:
        print(f"[MatrixLearning] Error recording pattern: {e}")


def get_optimal_generation_pattern(
    learning_system: Any,
    prompt: str,
    title: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Get optimal generation pattern based on learned knowledge"""
    if not learning_system:
        return _get_default_pattern(context)
    
    try:
        generation_context = {
            'prompt_type': _classify_prompt_type(prompt),
            'duration': context.get('target_duration', 180),
            'style': context.get('style', 'documentary'),
            'theme': context.get('theme', 'default')
        }
        
        optimal_pattern = learning_system.get_optimal_pattern(generation_context)
        print(f"[MatrixLearning] Retrieved optimal pattern for generation")
        return optimal_pattern
        
    except Exception as e:
        print(f"[MatrixLearning] Error getting optimal pattern: {e}")
        return _get_default_pattern(context)


def update_user_preferences(
    learning_system: Any,
    user_id: str,
    preferences: Dict[str, Any]
):
    """Update learned user preferences"""
    if not learning_system:
        return
    
    try:
        learning_system.update_user_preferences(user_id, preferences)
        print(f"[MatrixLearning] Updated preferences for user {user_id}")
    except Exception as e:
        print(f"[MatrixLearning] Error updating preferences: {e}")


def get_user_preferences(learning_system: Any, user_id: str) -> Dict[str, Any]:
    """Get learned preferences for a user"""
    if not learning_system:
        return {}
    
    try:
        return learning_system.get_user_preferences(user_id)
    except Exception as e:
        print(f"[MatrixLearning] Error getting preferences: {e}")
        return {}


def _classify_prompt_type(prompt: str) -> str:
    """Classify prompt type for pattern matching"""
    prompt_lower = prompt.lower()
    
    if any(kw in prompt_lower for kw in ['history', 'historical', 'past', 'ancient']):
        return 'historical'
    elif any(kw in prompt_lower for kw in ['science', 'scientific', 'research', 'study']):
        return 'scientific'
    elif any(kw in prompt_lower for kw in ['nature', 'wildlife', 'animal', 'environment']):
        return 'nature'
    elif any(kw in prompt_lower for kw in ['technology', 'tech', 'digital', 'computer']):
        return 'technology'
    elif any(kw in prompt_lower for kw in ['art', 'artistic', 'creative', 'design']):
        return 'artistic'
    else:
        return 'general'


def _get_default_pattern(context: Dict[str, Any]) -> Dict[str, Any]:
    """Get default pattern when learning system unavailable"""
    return {
        'prompt_type': context.get('prompt_type', 'general'),
        'duration': context.get('target_duration', 180),
        'style': context.get('style', 'documentary'),
        'theme': context.get('theme', 'default'),
        'quality_priority': 0.5,
        'speed_priority': 0.3,
        'creativity_priority': 0.2
    }

