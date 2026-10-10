"""
Video Editor Routes
API endpoints for video editing: trim, enhance, subtitles
"""
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
import uuid
from typing import Dict, Any, Optional
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

try:
    from src.services.video_generation.advanced_video_compiler import AdvancedVideoCompiler, TransitionType
    from src.db.models import db, Documentary
except ImportError as e:
    print(f"[VideoEditor] Import error: {e}")
    AdvancedVideoCompiler = None
    TransitionType = None
    db = None
    Documentary = None

video_editor_bp = Blueprint('video_editor', __name__)

@video_editor_bp.route('/api/video-editor/trim', methods=['POST'])
@video_editor_bp.route('/vidgenerator/api/video-editor/trim', methods=['POST'])
@rate_limit()
def trim_video():
    """Trim video - cut start and/or end"""
    try:
        data = InputValidator.get_json_safe(default={})
        video_id = InputValidator.sanitize_string(data.get('video_id', ''), max_length=50).strip()
        start_time = float(data.get('start_time', 0))
        end_time = float(data.get('end_time', 0))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        
        if end_time <= start_time:
            return jsonify({'success': False, 'error': 'end_time must be greater than start_time'}), 400
        
        # Get video from database
        if not Documentary:
            return jsonify({'success': False, 'error': 'Database models not available'}), 500
        
        doc = Documentary.query.get(video_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        if doc.status != 'completed':
            return jsonify({'success': False, 'error': 'Video is not ready for editing'}), 400
        
        video_path = doc.video_path
        if not video_path or not os.path.exists(video_path):
            return jsonify({'success': False, 'error': 'Video file not found'}), 404
        
        # Create output path for trimmed video
        base_path = Path(video_path).parent
        output_filename = f"trimmed_{video_id}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = base_path / output_filename
        
        # Trim video using FFmpeg
        if not AdvancedVideoCompiler:
            return jsonify({'success': False, 'error': 'Video compiler not available'}), 500
        
        compiler = AdvancedVideoCompiler()
        if not compiler.ffmpeg_path:
            return jsonify({'success': False, 'error': 'FFmpeg not found'}), 500
        
        # Build FFmpeg command for trimming
        import subprocess
        duration = end_time - start_time
        
        cmd = [
            compiler.ffmpeg_path,
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c', 'copy',  # Stream copy (fast, no re-encoding)
            '-avoid_negative_ts', 'make_zero',
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': f'FFmpeg error: {result.stderr[:200]}'
            }), 500
        
        if not output_path.exists():
            return jsonify({'success': False, 'error': 'Trimmed video not created'}), 500
        
        # Create new documentary entry for trimmed video
        trimmed_doc = Documentary(
            title=f"{doc.title or 'Video'} (Trimmed)",
            description=doc.description or '',
            prompt=doc.prompt or '',
            status='completed',
            progress=100,
            video_path=str(output_path),
            thumbnail_path=doc.thumbnail_path,
            duration=duration,
            category_name=doc.category_name,
            user_id=user_id
        )
        db.session.add(trimmed_doc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'video_id': trimmed_doc.id,
            'original_id': video_id,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'output_path': str(output_path),
            'message': 'Video trimmed successfully'
        }), 200
        
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@video_editor_bp.route('/api/video-editor/enhance', methods=['POST'])
@video_editor_bp.route('/vidgenerator/api/video-editor/enhance', methods=['POST'])
@rate_limit()
def enhance_video():
    """Enhance video quality: upscale, color correction, etc."""
    try:
        data = InputValidator.get_json_safe(default={})
        video_id = InputValidator.sanitize_string(data.get('video_id', ''), max_length=50).strip()
        enhancement_type = InputValidator.sanitize_string(data.get('type', 'upscale'), max_length=20).strip()
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        
        # Get video from database
        if not Documentary:
            return jsonify({'success': False, 'error': 'Database models not available'}), 500
        
        doc = Documentary.query.get(video_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        if doc.status != 'completed':
            return jsonify({'success': False, 'error': 'Video is not ready for editing'}), 400
        
        video_path = doc.video_path
        if not video_path or not os.path.exists(video_path):
            return jsonify({'success': False, 'error': 'Video file not found'}), 404
        
        # Create output path
        base_path = Path(video_path).parent
        output_filename = f"enhanced_{video_id}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = base_path / output_filename
        
        # Enhance video
        if not AdvancedVideoCompiler:
            return jsonify({'success': False, 'error': 'Video compiler not available'}), 500
        
        compiler = AdvancedVideoCompiler()
        if not compiler.ffmpeg_path:
            return jsonify({'success': False, 'error': 'FFmpeg not found'}), 500
        
        import subprocess
        
        # Build enhancement filter based on type
        if enhancement_type == 'upscale':
            # Upscale to 1080p or 4K
            target_resolution = data.get('target_resolution', '1920x1080')
            filter_complex = f"scale={target_resolution}:flags=lanczos"
        elif enhancement_type == 'color_correction':
            # Color correction: brightness, contrast, saturation
            brightness = data.get('brightness', 0)  # -1.0 to 1.0
            contrast = data.get('contrast', 1.0)  # 0.0 to 3.0
            saturation = data.get('saturation', 1.0)  # 0.0 to 3.0
            filter_complex = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
        elif enhancement_type == 'sharpen':
            filter_complex = "unsharp=5:5:1.0:5:5:0.0"
        elif enhancement_type == 'denoise':
            filter_complex = "hqdn3d=4:3:6:4.5"
        else:
            return jsonify({'success': False, 'error': f'Unknown enhancement type: {enhancement_type}'}), 400
        
        # Build FFmpeg command
        cmd = [
            compiler.ffmpeg_path,
            '-i', video_path,
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-crf', '18',  # High quality
            '-preset', 'slow',
            '-c:a', 'copy',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for enhancement
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': f'FFmpeg error: {result.stderr[:200]}'
            }), 500
        
        if not output_path.exists():
            return jsonify({'success': False, 'error': 'Enhanced video not created'}), 500
        
        # Create new documentary entry
        enhanced_doc = Documentary(
            title=f"{doc.title or 'Video'} (Enhanced)",
            description=doc.description or '',
            prompt=doc.prompt or '',
            status='completed',
            progress=100,
            video_path=str(output_path),
            thumbnail_path=doc.thumbnail_path,
            duration=doc.duration,
            category_name=doc.category_name,
            user_id=user_id
        )
        db.session.add(enhanced_doc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'video_id': enhanced_doc.id,
            'original_id': video_id,
            'enhancement_type': enhancement_type,
            'output_path': str(output_path),
            'message': f'Video enhanced with {enhancement_type}'
        }), 200
        
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@video_editor_bp.route('/api/video-editor/subtitle', methods=['POST'])
@video_editor_bp.route('/vidgenerator/api/video-editor/subtitle', methods=['POST'])
@rate_limit()
def add_subtitle():
    """Add subtitles/text overlays to video"""
    try:
        data = InputValidator.get_json_safe(default={})
        video_id = InputValidator.sanitize_string(data.get('video_id', ''), max_length=50).strip()
        subtitles = data.get('subtitles', [])  # List of {text, start_time, end_time, x, y, font_size, color}
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        
        if not subtitles or len(subtitles) == 0:
            return jsonify({'success': False, 'error': 'At least one subtitle is required'}), 400
        
        # Get video from database
        if not Documentary:
            return jsonify({'success': False, 'error': 'Database models not available'}), 500
        
        doc = Documentary.query.get(video_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        if doc.status != 'completed':
            return jsonify({'success': False, 'error': 'Video is not ready for editing'}), 400
        
        video_path = doc.video_path
        if not video_path or not os.path.exists(video_path):
            return jsonify({'success': False, 'error': 'Video file not found'}), 404
        
        # Create output path
        base_path = Path(video_path).parent
        output_filename = f"subtitled_{video_id}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = base_path / output_filename
        
        # Add subtitles using FFmpeg
        if not AdvancedVideoCompiler:
            return jsonify({'success': False, 'error': 'Video compiler not available'}), 500
        
        compiler = AdvancedVideoCompiler()
        if not compiler.ffmpeg_path:
            return jsonify({'success': False, 'error': 'FFmpeg not found'}), 500
        
        import subprocess
        
        # Build subtitle filter complex
        drawtext_filters = []
        for i, subtitle in enumerate(subtitles):
            text = subtitle.get('text', '').replace("'", "\\'").replace(":", "\\:")
            start = subtitle.get('start_time', 0)
            end = subtitle.get('end_time', start + 5)
            x = subtitle.get('x', '(w-text_w)/2')
            y = subtitle.get('y', 'h-th-10')
            font_size = subtitle.get('font_size', 24)
            color = subtitle.get('color', 'white')
            
            # Build drawtext filter
            drawtext = (
                f"drawtext=text='{text}':"
                f"fontsize={font_size}:"
                f"fontcolor={color}:"
                f"x={x}:"
                f"y={y}:"
                f"enable='between(t,{start},{end})'"
            )
            drawtext_filters.append(drawtext)
        
        filter_complex = ','.join(drawtext_filters)
        
        # Build FFmpeg command
        cmd = [
            compiler.ffmpeg_path,
            '-i', video_path,
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'medium',
            '-c:a', 'copy',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': f'FFmpeg error: {result.stderr[:200]}'
            }), 500
        
        if not output_path.exists():
            return jsonify({'success': False, 'error': 'Subtitled video not created'}), 500
        
        # Create new documentary entry
        subtitled_doc = Documentary(
            title=f"{doc.title or 'Video'} (Subtitled)",
            description=doc.description or '',
            prompt=doc.prompt or '',
            status='completed',
            progress=100,
            video_path=str(output_path),
            thumbnail_path=doc.thumbnail_path,
            duration=doc.duration,
            category_name=doc.category_name,
            user_id=user_id
        )
        db.session.add(subtitled_doc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'video_id': subtitled_doc.id,
            'original_id': video_id,
            'subtitles_count': len(subtitles),
            'output_path': str(output_path),
            'message': f'Added {len(subtitles)} subtitles to video'
        }), 200
        
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@video_editor_bp.route('/api/video-editor/preview/<video_id>', methods=['GET'])
@video_editor_bp.route('/vidgenerator/api/video-editor/preview/<video_id>', methods=['GET'])
@rate_limit()
def preview_video(video_id: str):
    """Get video for preview in editor"""
    try:
        if not Documentary:
            return jsonify({'success': False, 'error': 'Database models not available'}), 500
        
        doc = Documentary.query.get(video_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
        
        return jsonify({
            'success': True,
            'video': {
                'id': doc.id,
                'title': doc.title or 'Untitled',
                'video_path': doc.video_path,
                'duration': doc.duration or 0,
                'status': doc.status
            }
        }), 200
        
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

