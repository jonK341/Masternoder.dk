"""
Generation Script with Documentary Details
Main script that integrates all systems for optimal generation
"""
from typing import Dict, Any, Optional
from src.services.documentary_pipeline.documentary_details_processor import documentary_processor
from src.services.behavioral_tracking.xp_system import xp_system
from src.services.ai_defense.defense_system import ai_defense
from src.services.generation_matrix.matrix_system import generation_matrix
from src.services.documentary_pipeline.matrix_integration import integrate_matrix_with_generation


def generate_documentary_with_full_system(
    pipeline_orchestrator,
    doc_id: str,
    prompt: str,
    title: str = None,
    description: str = None,
    user_id: str = None
) -> Dict[str, Any]:
    """
    Generate documentary with full system integration:
    - AI Defense (prioritized)
    - Data Gathering
    - XP Tracking
    - Matrix Optimization
    
    Args:
        pipeline_orchestrator: PipelineOrchestrator instance
        doc_id: Documentary ID
        prompt: User prompt
        title: Optional title
        description: Optional description
        user_id: User identifier
    
    Returns:
        Generation result with all system data
    """
    result = {
        'doc_id': doc_id,
        'success': False,
        'systems': {
            'ai_defense': None,
            'data_gathering': None,
            'xp_tracking': None,
            'matrix_optimization': None
        },
        'enhanced_data': {}
    }
    
    # Step 1: AI Defense (PRIORITIZED)
    print(f"[FullSystem] Step 1: AI Defense check for user {user_id}")
    if user_id:
        is_safe, defense_result = ai_defense.is_safe_to_process(user_id, prompt, 'prompt')
        result['systems']['ai_defense'] = defense_result
        
        if not is_safe:
            result['error'] = f"Input blocked by AI defense: {defense_result['analysis']['threat_level_name']}"
            return result
        
        # Use sanitized input
        prompt = defense_result['sanitized_input']
        print(f"[FullSystem] ✓ AI Defense passed, using sanitized prompt")
    else:
        # Still sanitize even without user_id
        prompt = ai_defense.sanitize_input(prompt)
        print(f"[FullSystem] ✓ Input sanitized")
    
    # Step 2: Track XP (if user_id provided)
    if user_id:
        print(f"[FullSystem] Step 2: Tracking XP for user {user_id}")
        xp_awarded = xp_system.track_action(user_id, 'generate_video', {
            'prompt_length': len(prompt),
            'doc_id': doc_id,
            'title': title
        })
        result['systems']['xp_tracking'] = {
            'xp_awarded': xp_awarded,
            'total_xp': xp_system.behavioral_data.get(user_id, {}).get('total_xp', 0),
            'level': xp_system.behavioral_data.get(user_id, {}).get('level', 1)
        }
        print(f"[FullSystem] ✓ XP tracked: +{xp_awarded} XP")
    
    # Step 3: Data Gathering
    print(f"[FullSystem] Step 3: Gathering documentary data")
    try:
        doc_details = documentary_processor.process_documentary_request(
            prompt=prompt,
            title=title,
            user_id=user_id
        )
        result['systems']['data_gathering'] = {
            'success': True,
            'data_quality': doc_details['metadata']['data_quality'],
            'sources': doc_details['metadata']['sources'],
            'images_count': len(doc_details.get('images', [])),
            'text_sections': len(doc_details.get('text_content', []))
        }
        result['enhanced_data'] = doc_details
        print(f"[FullSystem] ✓ Data gathered: {len(doc_details.get('images', []))} images, "
              f"{len(doc_details.get('text_content', []))} text sections")
    except Exception as e:
        print(f"[FullSystem] ⚠ Data gathering error (continuing): {e}")
        result['systems']['data_gathering'] = {'success': False, 'error': str(e)}
    
    # Step 4: Get User Profile for Optimization
    user_profile = None
    if user_id:
        user_profile = xp_system.get_user_profile(user_id)
        recommendations = xp_system.get_generation_recommendations(user_id)
        result['enhanced_data']['user_recommendations'] = recommendations
        print(f"[FullSystem] ✓ User profile loaded: Level {user_profile['level']}, "
              f"Priority: {recommendations.get('optimization_priority', 'balanced')}")
    
    # Step 5: Matrix Integration
    print(f"[FullSystem] Step 4: Matrix system integration")
    try:
        matrix_result = integrate_matrix_with_generation(
            pipeline_orchestrator,
            doc_id,
            prompt,
            user_id,
            user_profile
        )
        result['systems']['matrix_optimization'] = {
            'success': True,
            'recommendations': matrix_result.get('recommendations', {}),
            'matrix_ready': matrix_result.get('matrix_ready', False)
        }
        print(f"[FullSystem] ✓ Matrix system ready")
    except Exception as e:
        print(f"[FullSystem] ⚠ Matrix integration error (continuing): {e}")
        result['systems']['matrix_optimization'] = {'success': False, 'error': str(e)}
    
    # Step 6: Enhanced prompt for generation
    enhanced_prompt = result['enhanced_data'].get('enhanced_prompt', prompt)
    enhanced_images = result['enhanced_data'].get('images', [])
    
    result['generation_input'] = {
        'original_prompt': prompt,
        'enhanced_prompt': enhanced_prompt,
        'title': title or result['enhanced_data'].get('title', ''),
        'images': enhanced_images,
        'user_recommendations': result['enhanced_data'].get('user_recommendations', {})
    }
    
    result['success'] = True
    print(f"[FullSystem] ✓ All systems integrated, ready for generation")
    
    return result


def apply_matrix_to_clips(clips: list, target_duration: float, user_profile: Dict = None) -> Dict[str, Any]:
    """Apply matrix optimization to generated clips"""
    return generation_matrix.create_generation_plan(
        clips=clips,
        target_duration=target_duration,
        user_profile=user_profile
    )

