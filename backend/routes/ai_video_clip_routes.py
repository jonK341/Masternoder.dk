"""
AI Video and Clip Generation Routes - All AI Providers
"""
from flask import Blueprint, request, jsonify, send_file, abort, redirect
from backend.services.ai_video_clip_generator import ai_video_clip_generator
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from backend.utils.url_validator import URLValidator
import os
from pathlib import Path

ai_video_clip_bp = Blueprint('ai_video_clip', __name__)


@ai_video_clip_bp.route('/api/ai-video/providers', methods=['GET'])
def get_providers():
    """Get all available AI providers"""
    try:
        providers = ai_video_clip_generator.get_available_providers()
        return jsonify(providers), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Adding both variants to ensure route matching
@ai_video_clip_bp.route('/api/ai-video/generate', methods=['POST', 'GET', 'OPTIONS'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-video/generate', methods=['POST', 'GET', 'OPTIONS'])
@rate_limit()
def generate_video():
    """Generate video with all AI"""
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    # Handle GET requests
    if request.method == 'GET':
        return jsonify({
            'success': False,
            'error': 'POST request required. Send JSON with: prompt (required), user_id (optional), duration (optional), resolution (optional), provider (optional), theme (optional)',
            'endpoint': '/api/ai-video/generate',
            'method': 'POST',
            'required_fields': ['prompt'],
            'optional_fields': ['user_id', 'duration', 'resolution', 'provider', 'theme']
        }), 200
    
    try:
        data = InputValidator.get_json_safe(request) or {}
        prompt = InputValidator.sanitize_string(data.get('prompt', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        duration = int(data.get('duration', 5)) if data.get('duration') else 5
        resolution = data.get('resolution', '1280x768')
        provider = data.get('provider')
        theme = data.get('theme')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'}), 400
        
        result = ai_video_clip_generator.generate_video_with_all_ai(
            prompt=prompt,
            user_id=user_id,
            duration=duration,
            resolution=resolution,
            provider_preference=provider,
            theme=theme
        )
        
        # Award comprehensive points for video generation
        if result.get('success'):
            try:
                from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
                from backend.services.unified_point_system_reconstructed import unified_point_system
                enhanced_game_mechanics.set_unified_points(unified_point_system)
                
                # Calculate quality multiplier (if quality_score exists in result)
                quality_score = result.get('quality_score', 0.8)
                difficulty = 'normal'
                if quality_score >= 0.9:
                    difficulty = 'extreme'
                elif quality_score >= 0.7:
                    difficulty = 'hard'
                
                # Award comprehensive points for video generation
                points_result = enhanced_game_mechanics.award_comprehensive_points(
                    user_id=user_id,
                    action='video_create',
                    difficulty=difficulty,
                    multiplier=1.0 + (quality_score * 0.5)  # Quality bonus
                )
                
                # Also award generation_complete points
                generation_points = enhanced_game_mechanics.award_comprehensive_points(
                    user_id=user_id,
                    action='generation_complete',
                    difficulty=difficulty,
                    multiplier=1.0
                )
                
                # Combine points
                if points_result.get('success') and generation_points.get('success'):
                    combined_points = {}
                    for key, value in points_result.get('points_awarded', {}).items():
                        combined_points[key] = combined_points.get(key, 0) + value
                    for key, value in generation_points.get('points_awarded', {}).items():
                        combined_points[key] = combined_points.get(key, 0) + value
                    
                    result['points_awarded'] = combined_points
                    result['gaming_experience'] = True
                    
                    print(f"[AI Video] Points awarded for video: {combined_points}", file=sys.stderr, flush=True)
            except Exception as point_err:
                print(f"[AI Video] Error awarding points: {point_err}", file=sys.stderr, flush=True)
        
        return jsonify(result), 200
    except Exception as e:
        import sys
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Video Generate] Error: {e}\n{error_trace}", file=sys.stderr, flush=True)
        # Return 200 to avoid breaking frontend
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': 'Video generation failed. Please try again or check your prompt.'
        }), 200


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Adding both variants to ensure route matching
@ai_video_clip_bp.route('/api/ai-clips/generate', methods=['POST', 'GET', 'OPTIONS'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-clips/generate', methods=['POST', 'GET', 'OPTIONS'])
@rate_limit()
def generate_clips():
    """Generate multiple clips with all AI"""
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    # Handle GET requests
    if request.method == 'GET':
        return jsonify({
            'success': False,
            'error': 'POST request required. Send JSON with: prompt (required), user_id (optional), clip_count (optional), duration (optional), theme (optional)',
            'endpoint': '/api/ai-clips/generate',
            'method': 'POST',
            'required_fields': ['prompt'],
            'optional_fields': ['user_id', 'clip_count', 'duration', 'theme']
        }), 200
    
    try:
        data = InputValidator.get_json_safe(request) or {}
        prompt = InputValidator.sanitize_string(data.get('prompt', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        clip_count = int(data.get('clip_count', 5)) if data.get('clip_count') else 5
        duration = int(data.get('duration', 5)) if data.get('duration') else 5
        theme = data.get('theme')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'}), 400
        
        result = ai_video_clip_generator.generate_clips_with_all_ai(
            prompt=prompt,
            user_id=user_id,
            clip_count=clip_count,
            duration=duration,
            theme=theme
        )
        
        # Award comprehensive points for clip generation
        if result.get('success'):
            try:
                from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
                from backend.services.unified_point_system_reconstructed import unified_point_system
                enhanced_game_mechanics.set_unified_points(unified_point_system)
                
                # Award points for clip generation
                points_result = enhanced_game_mechanics.award_comprehensive_points(
                    user_id=user_id,
                    action='generation_complete',
                    difficulty='normal',
                    multiplier=1.0 + (clip_count * 0.1)  # Bonus for multiple clips
                )
                
                # Add points info to result
                if points_result.get('success'):
                    result['points_awarded'] = points_result.get('points_awarded', {})
                    result['gaming_experience'] = True
                    
                    # Also award video_create points for each clip
                    for i in range(clip_count):
                        enhanced_game_mechanics.award_comprehensive_points(
                            user_id=user_id,
                            action='video_create',
                            difficulty='normal',
                            multiplier=1.0
                        )
                    
                    print(f"[AI Clips] Points awarded for {clip_count} clips: {points_result.get('points_awarded', {})}", file=sys.stderr, flush=True)
            except Exception as point_err:
                print(f"[AI Clips] Error awarding points: {point_err}", file=sys.stderr, flush=True)
        
        return jsonify(result), 200
    except Exception as e:
        import sys
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Clips Generate] Error: {e}\n{error_trace}", file=sys.stderr, flush=True)
        # Return 200 to avoid breaking frontend
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': 'Clip generation failed. Please try again or check your prompt.'
        }), 200


@ai_video_clip_bp.route('/api/ai-video/status/<video_id>', methods=['GET'])
def get_video_status(video_id):
    """Get video generation status"""
    try:
        result = ai_video_clip_generator.get_video_status(video_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@ai_video_clip_bp.route('/api/ai-video/user/<user_id>', methods=['GET'])
def get_user_videos(user_id):
    """Get user's videos and clips"""
    try:
        result = ai_video_clip_generator.get_user_videos(user_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@ai_video_clip_bp.route('/api/ai-video/video/<video_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-video/video/<video_id>', methods=['GET'])
def serve_video(video_id):
    """Serve AI-generated video file - Immortalized link"""
    try:
        result = ai_video_clip_generator.get_video_status(video_id)
        
        if not result.get('success'):
            abort(404)
        
        video_data = result.get('video') or result.get('clip')
        if not video_data:
            abort(404)
        
        # Get video URL or path
        video_url = video_data.get('video_url')
        video_path = video_data.get('video_path')
        
        # Check if it's a URL (external storage) - SECURITY: Validate before redirect
        if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
            is_safe, error = URLValidator.is_safe_redirect(video_url, allow_external=True)
            if is_safe:
                return redirect(video_url, code=302)
            else:
                # Log security issue and abort
                import sys
                print(f"[SECURITY] Blocked unsafe redirect: {video_url} - {error}", file=sys.stderr, flush=True)
                abort(403)  # Forbidden - unsafe redirect attempt
        
        # Check if we have a local file path
        if video_path and os.path.exists(video_path):
            download = request.args.get('download', '0') == '1'
            return send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=download,
                download_name=f"video_{video_id}.mp4" if download else None
            )
        
        # Try to find video in output directory
        output_dirs = [
            Path('/var/www/html/vidgenerator/output/videos'),
            Path('output/videos'),
            Path('output')
        ]
        
        for output_dir in output_dirs:
            if output_dir.exists():
                potential_path = output_dir / f"{video_id}.mp4"
                if potential_path.exists():
                    download = request.args.get('download', '0') == '1'
                    return send_file(
                        str(potential_path),
                        mimetype='video/mp4',
                        as_attachment=download,
                        download_name=f"video_{video_id}.mp4" if download else None
                    )
        
        abort(404)
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving video {video_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


@ai_video_clip_bp.route('/api/ai-clip/video/<clip_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-clip/video/<clip_id>', methods=['GET'])
def serve_clip(clip_id):
    """Serve AI-generated clip file - Immortalized link"""
    try:
        result = ai_video_clip_generator.get_video_status(clip_id)
        
        if not result.get('success'):
            abort(404)
        
        clip_data = result.get('clip') or result.get('video')
        if not clip_data:
            abort(404)
        
        # Get clip URL or path
        video_url = clip_data.get('video_url')
        video_path = clip_data.get('video_path')
        
        # Check if it's a URL (external storage) - SECURITY: Validate before redirect
        if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
            is_safe, error = URLValidator.is_safe_redirect(video_url, allow_external=True)
            if is_safe:
                return redirect(video_url, code=302)
            else:
                # Log security issue and abort
                import sys
                print(f"[SECURITY] Blocked unsafe redirect: {video_url} - {error}", file=sys.stderr, flush=True)
                abort(403)  # Forbidden - unsafe redirect attempt
        
        # Check if we have a local file path
        if video_path and os.path.exists(video_path):
            download = request.args.get('download', '0') == '1'
            return send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=download,
                download_name=f"clip_{clip_id}.mp4" if download else None
            )
        
        # Try to find clip in output directory
        output_dirs = [
            Path('/var/www/html/vidgenerator/output/videos'),
            Path('output/videos'),
            Path('output/clips'),
            Path('output')
        ]
        
        for output_dir in output_dirs:
            if output_dir.exists():
                potential_path = output_dir / f"{clip_id}.mp4"
                if potential_path.exists():
                    download = request.args.get('download', '0') == '1'
                    return send_file(
                        str(potential_path),
                        mimetype='video/mp4',
                        as_attachment=download,
                        download_name=f"clip_{clip_id}.mp4" if download else None
                    )
        
        abort(404)
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving clip {clip_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


# Short permanent links for videos and clips
@ai_video_clip_bp.route('/v/<video_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/v/<video_id>', methods=['GET'])
def serve_video_short(video_id):
    """Short permanent link for video - Immortalized"""
    return serve_video(video_id)


@ai_video_clip_bp.route('/c/<clip_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/c/<clip_id>', methods=['GET'])
def serve_clip_short(clip_id):
    """Short permanent link for clip - Immortalized"""
    return serve_clip(clip_id)


@ai_video_clip_bp.route('/api/ai-video/thumbnail/<video_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-video/thumbnail/<video_id>', methods=['GET'])
def serve_thumbnail(video_id):
    """Serve video thumbnail"""
    try:
        result = ai_video_clip_generator.get_video_status(video_id)
        
        if not result.get('success'):
            abort(404)
        
        video_data = result.get('video') or result.get('clip')
        if not video_data:
            abort(404)
        
        thumbnail_path = video_data.get('thumbnail_path')
        if not thumbnail_path:
            abort(404)
        
        thumb_path = Path(thumbnail_path)
        if thumb_path.exists():
            return send_file(
                str(thumb_path),
                mimetype='image/jpeg',
                download_name=f"thumb_{video_id}.jpg"
            )
        
        abort(404)
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving thumbnail {video_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


@ai_video_clip_bp.route('/api/ai-video/metadata/<video_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-video/metadata/<video_id>', methods=['GET'])
def serve_metadata(video_id):
    """Serve video metadata"""
    try:
        result = ai_video_clip_generator.get_video_status(video_id)
        
        if not result.get('success'):
            abort(404)
        
        video_data = result.get('video') or result.get('clip')
        if not video_data:
            abort(404)
        
        metadata_path = video_data.get('metadata_path')
        if metadata_path:
            meta_path = Path(metadata_path)
            if meta_path.exists():
                import json
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                return jsonify(metadata), 200
        
        # Return video data as metadata if no separate metadata file
        return jsonify(video_data), 200
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving metadata {video_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


@ai_video_clip_bp.route('/api/ai-clip/thumbnail/<clip_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-clip/thumbnail/<clip_id>', methods=['GET'])
def serve_clip_thumbnail(clip_id):
    """Serve clip thumbnail"""
    try:
        result = ai_video_clip_generator.get_video_status(clip_id)
        
        if not result.get('success'):
            abort(404)
        
        clip_data = result.get('clip') or result.get('video')
        if not clip_data:
            abort(404)
        
        thumbnail_path = clip_data.get('thumbnail_path')
        if not thumbnail_path:
            abort(404)
        
        thumb_path = Path(thumbnail_path)
        if thumb_path.exists():
            return send_file(
                str(thumb_path),
                mimetype='image/jpeg',
                download_name=f"thumb_{clip_id}.jpg"
            )
        
        abort(404)
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving clip thumbnail {clip_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


@ai_video_clip_bp.route('/api/ai-clip/metadata/<clip_id>', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-clip/metadata/<clip_id>', methods=['GET'])
def serve_clip_metadata(clip_id):
    """Serve clip metadata"""
    try:
        result = ai_video_clip_generator.get_video_status(clip_id)
        
        if not result.get('success'):
            abort(404)
        
        clip_data = result.get('clip') or result.get('video')
        if not clip_data:
            abort(404)
        
        metadata_path = clip_data.get('metadata_path')
        if metadata_path:
            meta_path = Path(metadata_path)
            if meta_path.exists():
                import json
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                return jsonify(metadata), 200
        
        # Return clip data as metadata if no separate metadata file
        return jsonify(clip_data), 200
    except Exception as e:
        import sys
        print(f"[AI Video Routes] Error serving clip metadata {clip_id}: {e}", file=sys.stderr, flush=True)
        abort(404)


@ai_video_clip_bp.route('/api/ai-video/batch-status', methods=['GET'])
@ai_video_clip_bp.route('/vidgenerator/api/ai-video/batch-status', methods=['GET'])
@rate_limit()
def batch_status():
    """Get status of multiple videos/clips"""
    try:
        video_ids = request.args.getlist('video_id')
        clip_ids = request.args.getlist('clip_id')
        user_id = request.args.get('user_id')
        
        results = {
            'videos': [],
            'clips': [],
            'total': 0,
            'completed': 0,
            'processing': 0,
            'failed': 0
        }
        
        # Get video statuses
        for vid_id in video_ids:
            status = ai_video_clip_generator.get_video_status(vid_id)
            if status.get('success'):
                video_data = status.get('video') or status.get('clip')
                if video_data:
                    results['videos'].append(video_data)
                    status_val = video_data.get('status', 'unknown')
                    if status_val == 'completed':
                        results['completed'] += 1
                    elif status_val == 'processing':
                        results['processing'] += 1
                    elif status_val in ['failed', 'error']:
                        results['failed'] += 1
        
        # Get clip statuses
        for clip_id in clip_ids:
            status = ai_video_clip_generator.get_video_status(clip_id)
            if status.get('success'):
                clip_data = status.get('clip') or status.get('video')
                if clip_data:
                    results['clips'].append(clip_data)
                    status_val = clip_data.get('status', 'unknown')
                    if status_val == 'completed':
                        results['completed'] += 1
                    elif status_val == 'processing':
                        results['processing'] += 1
                    elif status_val in ['failed', 'error']:
                        results['failed'] += 1
        
        # Get user videos if user_id provided
        if user_id:
            user_data = ai_video_clip_generator.get_user_videos(user_id)
            if user_data.get('success'):
                results['user_videos'] = user_data.get('videos', [])
                results['user_clips'] = user_data.get('clips', [])
        
        results['total'] = len(results['videos']) + len(results['clips'])
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

