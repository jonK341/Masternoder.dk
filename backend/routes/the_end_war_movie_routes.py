"""
The End War Movie Clip Routes
Generate a 30-second "The End War" movie clip
"""
from flask import Blueprint, request, jsonify
from typing import Dict
from datetime import datetime
import uuid
import os

the_end_war_bp = Blueprint('the_end_war', __name__)


@the_end_war_bp.route('/api/movie/the-end-war/generate', methods=['POST'])
def generate_the_end_war_movie():
    """Generate "The End War" 30-second movie clip"""
    try:
        data = request.get_json() or {}
        job_id = str(uuid.uuid4())
        
        # Movie clip configuration
        movie_config = {
            'title': 'The End War',
            'duration': 30,  # 30 seconds
            'theme': 'epic_battle',
            'style': 'cinematic',
            'quality': 'high',
            'scenes': [
                {
                    'scene': 1,
                    'duration': 5,
                    'description': 'Opening: Dark skies, war-torn landscape',
                    'visual': 'apocalyptic_landscape',
                    'audio': 'ominous_drums'
                },
                {
                    'scene': 2,
                    'duration': 8,
                    'description': 'Rising action: Armies gathering, tension building',
                    'visual': 'army_formation',
                    'audio': 'building_tension'
                },
                {
                    'scene': 3,
                    'duration': 10,
                    'description': 'Climax: Epic battle, explosions, conflict',
                    'visual': 'battle_sequence',
                    'audio': 'intense_battle_music'
                },
                {
                    'scene': 4,
                    'duration': 5,
                    'description': 'Resolution: Aftermath, peace restored',
                    'visual': 'peaceful_ending',
                    'audio': 'triumphant_ending'
                },
                {
                    'scene': 5,
                    'duration': 2,
                    'description': 'Title card: "The End War"',
                    'visual': 'title_card',
                    'audio': 'dramatic_finale'
                }
            ],
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'job_id': job_id,
                'type': 'movie_clip',
                'resolution': '1920x1080',
                'fps': 30
            }
        }
        
        # Save job to database or file
        try:
            from backend.utils.agent_task_database import save_agent_task
            save_agent_task({
                'task_id': job_id,
                'agent_id': 'content_generator_agent',
                'task_type': 'movie_generation',
                'description': 'Generate "The End War" 30-second movie clip',
                'status': 'processing',
                'priority': 'high',
                'points_reward': {'xp': 100, 'activity_points': 50, 'generation_points': 75},
                'result_data': movie_config
            })
        except:
            pass
        
        # Award points for starting generation
        try:
            from backend.services.agent_point_creator import AgentPointCreator
            point_creator = AgentPointCreator()
            if point_creator:
                point_creator.award_points_for_agent_action(
                    agent_id='content_generator_agent',
                    action='start_movie_generation',
                    user_id='system',
                    points={'xp': 50, 'activity_points': 25, 'generation_points': 30}
                )
        except:
            pass
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'processing',
            'message': 'The End War movie clip generation started',
            'config': movie_config,
            'estimated_time': '30-60 seconds',
            'points_awarded': {'xp': 50, 'activity_points': 25, 'generation_points': 30}
        }), 202
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@the_end_war_bp.route('/api/movie/the-end-war/status/<job_id>', methods=['GET'])
def get_movie_status(job_id):
    """Get movie generation status"""
    try:
        from backend.utils.agent_task_database import get_agent_task
        task = get_agent_task(job_id)
        
        if task:
            return jsonify({
                'success': True,
                'job_id': job_id,
                'status': task.get('status', 'processing'),
                'progress': 75 if task.get('status') == 'processing' else 100,
                'video_url': f'/vidgenerator/videos/the-end-war-{job_id}.mp4' if task.get('status') == 'completed' else None
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
