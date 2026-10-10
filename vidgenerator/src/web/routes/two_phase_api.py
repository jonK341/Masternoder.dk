"""
API Routes for Two-Phase Generator
Phase 1: Intelligence Gathering
Phase 2: AI Generation from Intelligence
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import uuid
import os
from datetime import datetime
from pathlib import Path

from src.db.models import db, Documentary

# Import GenerationStats with fallback
try:
    from src.db.models import GenerationStats
except ImportError:
    # GenerationStats might not exist, create dummy class
    class GenerationStats:
        def __init__(self, **kwargs):
            pass
    print("[TwoPhaseAPI] Warning: GenerationStats not available, using dummy class")

# Import with error handling to prevent service crash
try:
    from src.services.documentary_pipeline.two_phase_generator import TwoPhaseGenerator
except ImportError as e:
    print(f"[TwoPhaseAPI] Warning: TwoPhaseGenerator not available: {e}")
    import traceback
    traceback.print_exc()
    TwoPhaseGenerator = None

try:
    from src.services.ai_generation.worker_intelligence_ai import WorkerIntelligenceAI
except ImportError as e:
    print(f"[TwoPhaseAPI] Warning: WorkerIntelligenceAI not available: {e}")
    import traceback
    traceback.print_exc()
    WorkerIntelligenceAI = None

two_phase_bp = Blueprint('two_phase', __name__)

# Import theme selector
try:
    from src.services.theme_manager.theme_selector import select_theme_for_generation, IntelligentThemeSelector
    from src.services.theme_manager.theme_config import ThemeConfig
except ImportError as e:
    print(f"[TwoPhaseAPI] Warning: Theme selector not available: {e}")
    IntelligentThemeSelector = None
    ThemeConfig = None


@two_phase_bp.route('/api/documentary/gather-intelligence', methods=['POST'])
def gather_intelligence():
    """
    Phase 1: Gather comprehensive intelligence
    This endpoint can be called by the service worker or frontend
    """
    try:
        data = request.get_json() or {}
        
        # Support both old format (documentary_data) and new format (direct fields)
        if 'documentary_data' in data:
            documentary_data = data.get('documentary_data', {})
            user_context = data.get('user_context', {})
        else:
            # New simplified format - direct fields
            documentary_data = {
                'doc_id': data.get('doc_id'),
                'prompt': data.get('prompt'),
                'title': data.get('title'),
                'description': data.get('description'),
                'theme': data.get('theme'),
                'clip_duration': data.get('clip_duration', 10)
            }
            user_context = data.get('user_context', {})
        
        doc_id = documentary_data.get('doc_id') or data.get('doc_id') or str(uuid.uuid4())
        
        # Get clip duration from request (default: 10 seconds)
        clip_duration = documentary_data.get('clip_duration', 10)
        user_context['preferred_clip_duration'] = clip_duration
        
        # Get theme from request or auto-detect
        theme = documentary_data.get('theme') or user_context.get('theme')
        if not theme or theme == 'auto':
            # Auto-detect theme from prompt
            if IntelligentThemeSelector:
                selector = IntelligentThemeSelector()
                theme = selector.detect_theme_from_content(
                    documentary_data.get('prompt', ''),
                    documentary_data.get('title', '')
                )
            else:
                theme = 'matrix'  # Default
        
        user_context['theme'] = theme
        documentary_data['theme'] = theme
        
        # Enhanced logic: Calculate XP bonus based on prompt complexity
        prompt = documentary_data.get('prompt', '')
        prompt_length = len(prompt.split())
        complexity_bonus = min(prompt_length / 50, 2.0)  # Max 2x bonus for long prompts
        user_context['complexity_bonus'] = complexity_bonus
        user_context['prompt_length'] = prompt_length
        
        # Create or get documentary record
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            documentary = Documentary(
                id=doc_id,
                title=documentary_data.get('title', 'Untitled'),
                prompt=documentary_data.get('prompt', ''),
                description=documentary_data.get('description', ''),
                status='gathering_intelligence',
                progress=5
            )
            db.session.add(documentary)
        else:
            documentary.status = 'gathering_intelligence'
            documentary.progress = 5
        
        db.session.commit()
        
        # Note: Actual intelligence gathering happens client-side via service worker
        # This endpoint just prepares the documentary record
        
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'message': 'Intelligence gathering initiated. Service worker will gather all data.',
            'note': 'Intelligence gathering happens client-side. Use service worker for actual gathering.'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@two_phase_bp.route('/api/documentary/generate-from-intelligence', methods=['POST'])
def generate_from_intelligence():
    """
    Phase 2: Generate clips and movie from intelligence
    """
    try:
        data = request.get_json()
        doc_id = data.get('doc_id')
        intelligence = data.get('intelligence', {})
        strategy = data.get('strategy', 'balanced')
        target_duration = data.get('target_duration', 180)
        clip_duration = data.get('clip_duration', 10)  # Get clip duration (default: 10)
        
        # Update intelligence with clip duration preference
        if 'user_stats' not in intelligence:
            intelligence['user_stats'] = {}
        intelligence['user_stats']['preferred_clip_duration'] = clip_duration
        
        if not doc_id:
            return jsonify({
                'success': False,
                'error': 'doc_id required'
            }), 400
        
        if not intelligence:
            return jsonify({
                'success': False,
                'error': 'intelligence data required'
            }), 400
        
        # Get documentary
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            return jsonify({
                'success': False,
                'error': 'Documentary not found'
            }), 404
        
        # Update status
        documentary.status = 'generating'
        documentary.progress = 55
        db.session.commit()
        
        # Initialize AI generation system with doc_id
        if not WorkerIntelligenceAI:
            return jsonify({
                'success': False,
                'error': 'WorkerIntelligenceAI not available'
            }), 500
        
        worker_ai = WorkerIntelligenceAI(doc_id=doc_id)
        
        # Get clip count from request or intelligence (emphasized)
        request_data = data  # Fix: use data directly
        clip_count = data.get('clip_count') or intelligence.get('metadata', {}).get('preferred_clip_count', 10)
        
        # Get active unlocks that may add extra clips
        unlocks = intelligence.get('unlocks', {}) or {}
        extra_clips = unlocks.get('extra_clips', 0)
        clip_count = int(clip_count) + int(extra_clips)
        
        print(f"[TwoPhaseAPI] Generating with clip count: {clip_count} (base: {request_data.get('clip_count', 10)}, extra: {extra_clips})")
        
        # Generate from intelligence with service worker content
        generation_result = worker_ai.generate_from_intelligence(
            intelligence=intelligence,
            target_duration=target_duration,
            strategy=strategy,
            doc_id=doc_id,
            clip_count=clip_count  # Pass emphasized clip count
        )
        
        if generation_result.get('success'):
            # Get video path and clips from result
            movie_path = generation_result.get('movie_path')
            generated_clips = generation_result.get('clips', [])
            
            # Save clips metadata for slideshow (clips themselves saved to browser storage by frontend)
            if generated_clips:
                print(f"[TwoPhaseAPI] Generated {len(generated_clips)} clips for slideshow")
                # Clips will be saved to browser storage (IndexedDB/Cache) by frontend JavaScript
                # Return clip metadata in response for frontend to save
            
            # Ensure video path is valid and file exists AND is valid size (> 10KB)
            if movie_path and os.path.exists(movie_path):
                file_size = os.path.getsize(movie_path)
                
                # CRITICAL: Only save if file is valid (> 10KB)
                if file_size <= 10240:
                    print(f"[TwoPhaseAPI] ERROR: Video file too small ({file_size} bytes), recreating...")
                    # Try to recreate using worker AI
                    if WorkerIntelligenceAI:
                        try:
                            worker_ai = WorkerIntelligenceAI(doc_id=doc_id)
                            recreated_path = worker_ai._recreate_movie_with_context(
                                generation_result.get('clips', []),
                                intelligence,
                                target_duration
                            )
                            if recreated_path and os.path.exists(recreated_path):
                                recreated_size = os.path.getsize(recreated_path)
                                if recreated_size > 10240:
                                    movie_path = recreated_path
                                    file_size = recreated_size
                                    print(f"[TwoPhaseAPI] ✓ Video recreated: {movie_path} ({file_size} bytes)")
                                else:
                                    print(f"[TwoPhaseAPI] ✗ Recreated video still too small ({recreated_size} bytes)")
                                    movie_path = None
                            else:
                                print(f"[TwoPhaseAPI] ✗ Failed to recreate video")
                                movie_path = None
                        except Exception as e:
                            print(f"[TwoPhaseAPI] Error recreating video: {e}")
                            movie_path = None
                    else:
                        movie_path = None
                
                if movie_path and os.path.exists(movie_path) and os.path.getsize(movie_path) > 10240:
                    # Convert to relative path if needed for database storage
                    from pathlib import Path
                    movie_path_obj = Path(movie_path)
                    
                    # If absolute path, try to make it relative to output directory
                    if movie_path_obj.is_absolute():
                        try:
                            from src.services.file_management.file_manager import FileManager
                            file_manager = FileManager()
                            output_dir = file_manager.get_output_dir()
                            try:
                                movie_path = str(movie_path_obj.relative_to(output_dir))
                            except ValueError:
                                # Path not relative to output dir, use absolute
                                movie_path = str(movie_path_obj)
                        except Exception:
                            # File manager not available, use absolute path
                            movie_path = str(movie_path_obj)
                    else:
                        movie_path = str(movie_path_obj)
                    
                    # Update documentary with results
                    documentary.video_path = movie_path
                    documentary.duration = generation_result.get('total_duration', 0)
                    documentary.status = 'completed'
                    documentary.progress = 100
                    documentary.completed_at = datetime.utcnow()
                    
                    print(f"[TwoPhaseAPI] ✓ Video saved: {movie_path}, Duration: {documentary.duration}s, Size: {file_size} bytes")
                else:
                    # Video file doesn't exist or is invalid - mark as failed
                    print(f"[TwoPhaseAPI] ERROR: Video file invalid or not found: {movie_path}")
                    documentary.status = 'failed'
                    documentary.progress = 0
                    db.session.commit()
                    
                    return jsonify({
                        'success': False,
                        'error': f'Video file invalid or too small: {movie_path}'
                    }), 500
            else:
                # Video file doesn't exist - mark as failed
                print(f"[TwoPhaseAPI] ERROR: Video file not found: {movie_path}")
                documentary.status = 'failed'
                documentary.progress = 0
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': f'Video file not found: {movie_path}'
                }), 500
            
            # Update generation stats
            try:
                from src.web.routes.booster_packs import stats_counter
                stats_counter.update_generation_stats({
                    'status': 'completed',
                    'duration': generation_result.get('total_duration', 0),
                    'quality_score': generation_result.get('quality_score', 0.8),
                    'clips': generation_result.get('clips', []),
                    'theme': request_data.get('theme', 'matrix'),
                    'provider': generation_result.get('provider', 'unknown')
                })
            except Exception as e:
                print(f"[TwoPhaseAPI] Stats update error: {e}")
            
            # Save generation stats (if GenerationStats is available)
            try:
                if GenerationStats and hasattr(GenerationStats, '__init__'):
                    stats = GenerationStats(
                        id=str(uuid.uuid4()),
                        user_id=request.headers.get('X-User-ID', doc_id),
                        documentary_id=doc_id,
                        generation_time=generation_result.get('generation_time'),
                        quality_score=generation_result.get('quality_score', 0),
                        duration_achieved=generation_result.get('total_duration', 0),
                        target_duration=target_duration,
                        clips_generated=len(generation_result.get('clips', [])),
                        video_quality=generation_result.get('quality_score', 0)
                    )
                    db.session.add(stats)
            except Exception as stats_error:
                print(f"[TwoPhaseAPI] Warning: Could not save generation stats: {stats_error}")
                # Continue without stats
            
            # Track XP and trophies for successful generation
            try:
                from src.services.behavioral_tracking.generation_tracker import (
                    get_user_id_from_request,
                    track_generation_complete
                )
                user_id = get_user_id_from_request(request)
                
                tracking_result = track_generation_complete(
                    user_id=user_id,
                    doc_id=doc_id,
                    success=True,
                    video_path=movie_path,
                    duration=generation_result.get('total_duration', 0),
                    quality_score=generation_result.get('quality_score', 0),
                    metadata={
                        'strategy': strategy,
                        'target_duration': target_duration,
                        'clips_count': len(generation_result.get('clips', []))
                    }
                )
                
                if tracking_result.get('level_up'):
                    print(f"[TwoPhaseAPI] 🎉 User {user_id} leveled up to {tracking_result.get('new_level')}!")
                if tracking_result.get('trophies_awarded'):
                    print(f"[TwoPhaseAPI] 🏆 User {user_id} earned {len(tracking_result['trophies_awarded'])} trophies!")
            except Exception as track_error:
                print(f"[TwoPhaseAPI] Warning: Could not track generation: {track_error}")
                import traceback
                traceback.print_exc()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'doc_id': doc_id,
                'video_path': generation_result.get('movie_path'),
                'duration': generation_result.get('total_duration', 0),
                'quality_score': generation_result.get('quality_score', 0),
                'clips_count': len(generation_result.get('clips', [])),
                'xp_awarded': tracking_result.get('xp_awarded', 0) if 'tracking_result' in locals() else 0,
                'trophies_awarded': len(tracking_result.get('trophies_awarded', [])) if 'tracking_result' in locals() else 0
            }), 200
        else:
            documentary.status = 'failed'
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': generation_result.get('error', 'Generation failed')
            }), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@two_phase_bp.route('/api/documentary/<doc_id>/intelligence', methods=['GET'])
def get_intelligence(doc_id: str):
    """Get stored intelligence for a documentary"""
    try:
        # Intelligence is typically stored client-side
        # This endpoint can retrieve from cache or database if stored
        
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'message': 'Intelligence stored client-side. Use service worker to retrieve.'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@two_phase_bp.route('/api/documentary/<doc_id>/intelligence', methods=['POST'])
def store_intelligence(doc_id: str):
    """Store intelligence for a documentary"""
    try:
        data = request.get_json()
        intelligence = data.get('intelligence', {})
        
        # Store intelligence (could be in cache, database, or service worker)
        # For now, just acknowledge
        
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'message': 'Intelligence stored'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@two_phase_bp.route('/api/documentary/<doc_id>/progress', methods=['GET'])
def get_progress(doc_id: str):
    """
    Get generation progress for a documentary
    """
    try:
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            return jsonify({
                'success': False,
                'error': 'Documentary not found',
                'status': 'not_found',
                'progress': 0
            }), 404
        
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'status': documentary.status,
            'progress': documentary.progress or 0,
            'message': _get_status_message(documentary.status, documentary.progress or 0),
            'video_path': documentary.video_path if documentary.video_path else None,
            'duration': documentary.duration if documentary.duration else None,
            'created_at': documentary.created_at.isoformat() if documentary.created_at else None,
            'completed_at': documentary.completed_at.isoformat() if documentary.completed_at else None
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error',
            'progress': 0
        }), 500


def _get_status_message(status: str, progress: int) -> str:
    """Get user-friendly status message"""
    status_messages = {
        'gathering_intelligence': 'Gathering intelligence...',
        'intelligence_ready': 'Intelligence ready, starting generation...',
        'generating': f'Generating video... {progress}%',
        'processing': f'Processing clips... {progress}%',
        'composing': f'Composing video... {progress}%',
        'completed': 'Generation complete!',
        'failed': 'Generation failed',
        'pending': 'Waiting to start...'
    }
    
    return status_messages.get(status, f'Status: {status} ({progress}%)')

