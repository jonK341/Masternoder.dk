"""
Clip Generation API Routes
Handles individual clip generation requests from service worker
"""
from flask import Blueprint, request, jsonify
from src.db.models import db, MovieClip, Documentary
from src.services.video_generation.multi_generator_system import (
    MultiGeneratorSystem, ClipRequest, ClipDuration
)
from datetime import datetime
import uuid
import os

clips_bp = Blueprint('clips', __name__)

# Initialize multi-generator system
multi_generator = MultiGeneratorSystem()


@clips_bp.route('/api/clip/generate', methods=['POST'])
@clips_bp.route('/vidgenerator/api/clip/generate', methods=['POST'])
def generate_clip():
    """Generate a single clip"""
    try:
        data = request.get_json() or {}
        
        prompt = data.get('prompt', '').strip()
        duration_type = data.get('duration', 'short')  # 'short', 'medium', 'long'
        duration_seconds = data.get('duration_seconds', 10)
        style = data.get('style', 'default')
        metadata = data.get('metadata', {})
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Determine clip duration category
        if duration_seconds <= 12:
            clip_duration = ClipDuration.SHORT
        elif duration_seconds <= 180:
            clip_duration = ClipDuration.MEDIUM
        else:
            clip_duration = ClipDuration.LONG
        
        # Create clip request
        clip_request = ClipRequest(
            prompt=prompt,
            duration=clip_duration,
            duration_seconds=duration_seconds,
            style=style,
            metadata=metadata
        )
        
        # Generate clip
        result = multi_generator.generate_clip(clip_request)
        
        if result.success:
            # Save clip to database if documentary_id provided
            clip_record = None
            if metadata.get('documentary_id'):
                clip_record = MovieClip(
                    id=str(uuid.uuid4()),
                    documentary_id=metadata['documentary_id'],
                    prompt=prompt,
                    clip_path=result.clip_path,
                    duration=result.duration or duration_seconds,
                    order_index=metadata.get('clipIndex', 0),
                    quality_score=0.8,  # Default quality
                    clip_metadata={
                        'generator_used': result.generator_used,
                        'style': style,
                        'generation_timestamp': datetime.utcnow().isoformat()
                    }
                )
                db.session.add(clip_record)
                db.session.commit()
            
            return jsonify({
                'success': True,
                'clip_path': result.clip_path,
                'clip_id': clip_record.id if clip_record else None,
                'duration': result.duration,
                'generator_used': result.generator_used,
                'metadata': result.metadata or {}
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error or 'Clip generation failed'
            }), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@clips_bp.route('/api/documentary/compile', methods=['POST'])
@clips_bp.route('/vidgenerator/api/documentary/compile', methods=['POST'])
def compile_documentary():
    """Compile multiple clips into final documentary"""
    try:
        data = request.get_json() or {}
        clips = data.get('clips', [])
        generation_id = data.get('generationId')
        documentary_id = data.get('documentary_id')
        
        if not clips:
            return jsonify({'error': 'No clips provided'}), 400
        
        # Filter successful clips
        successful_clips = [c for c in clips if c.get('path') and os.path.exists(c.get('path'))]
        
        if not successful_clips:
            return jsonify({'error': 'No valid clips to compile'}), 400
        
        # Compile clips using FFmpeg
        from src.utils.file_manager import FileManager
        file_manager = FileManager()
        
        # Create compilation list file
        compilation_id = generation_id or f"comp_{int(datetime.utcnow().timestamp())}"
        list_file = file_manager.get_output_path(f"{compilation_id}_clips.txt")
        
        with open(list_file, 'w') as f:
            for clip in successful_clips:
                clip_path = clip['path']
                if os.path.exists(clip_path):
                    # Escape single quotes and special characters
                    escaped_path = clip_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
        
        # Output file
        output_path = file_manager.get_output_path(f"{compilation_id}_final.mp4")
        
        # Use FFmpeg to concatenate clips
        import subprocess
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Clean up list file
        if os.path.exists(list_file):
            os.remove(list_file)
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Update documentary if ID provided
            if documentary_id:
                documentary = Documentary.query.get(documentary_id)
                if documentary:
                    documentary.video_path = str(output_path)
                    documentary.status = 'completed'
                    documentary.progress = 100
                    db.session.commit()
            
            # Calculate total duration
            total_duration = sum(c.get('duration', 0) for c in successful_clips)
            
            return jsonify({
                'success': True,
                'final_path': str(output_path),
                'total_duration': total_duration,
                'clips_used': len(successful_clips),
                'documentary_id': documentary_id
            })
        else:
            return jsonify({
                'success': False,
                'error': f'FFmpeg compilation failed: {result.stderr}'
            }), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

