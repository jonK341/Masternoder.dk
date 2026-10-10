"""
Matrix Integration for Pipeline Orchestrator
Integrates matrix system with generation process
"""
from typing import Dict, List, Optional, Any
from src.services.generation_matrix.matrix_system import generation_matrix
from src.services.behavioral_tracking.xp_system import xp_system
from src.services.ai_defense.defense_system import ai_defense


def integrate_matrix_with_generation(pipeline_orchestrator, doc_id: str, prompt: str, 
                                    user_id: str = None, user_profile: Optional[Dict] = None):
    """
    Integrate matrix system with generation process
    
    Args:
        pipeline_orchestrator: PipelineOrchestrator instance
        doc_id: Documentary ID
        prompt: Generation prompt
        user_id: User identifier (for XP/behavioral tracking)
        user_profile: User behavioral/psychological profile
    
    Returns:
        Generation plan with matrix optimization
    """
    # Get user profile if not provided
    if user_id and not user_profile:
        user_profile = xp_system.get_user_profile(user_id)
    
    # Get generation recommendations from XP system
    if user_id:
        recommendations = xp_system.get_generation_recommendations(user_id)
    else:
        recommendations = {
            'clip_duration_range': (5, 15),
            'target_duration_range': (180, 600),
            'complexity_level': 0.5,
            'optimization_priority': 'balanced'
        }
    
    # AI Defense: Check input safety
    if user_id:
        is_safe, defense_result = ai_defense.is_safe_to_process(user_id, prompt)
        if not is_safe:
            raise ValueError(f"Input blocked by AI defense system: {defense_result['analysis']['threat_level_name']}")
        
        # Use sanitized input
        prompt = defense_result['sanitized_input']
    
    # Create generation plan using matrix system
    # This will be called during clip generation to optimize sequence
    return {
        'recommendations': recommendations,
        'user_profile': user_profile,
        'defense_passed': True if user_id else None,
        'matrix_ready': True
    }


def apply_matrix_optimization(clips: List[Dict], target_duration: float, 
                              user_profile: Optional[Dict] = None) -> Dict:
    """
    Apply matrix optimization to clip sequence
    
    Args:
        clips: List of generated clips
        target_duration: Target duration
        user_profile: User profile for optimization
    
    Returns:
        Optimized generation plan
    """
    plan = generation_matrix.create_generation_plan(
        clips=clips,
        target_duration=target_duration,
        user_profile=user_profile
    )
    
    return plan

