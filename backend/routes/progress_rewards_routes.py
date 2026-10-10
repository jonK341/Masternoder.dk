"""
Enhanced Progress Data & Video Generation Rewards Routes
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

progress_rewards_bp = Blueprint('progress_rewards', __name__, url_prefix='/api/progress-rewards')

# Enhanced Progress Data Routes
@progress_rewards_bp.route('/progress/track', methods=['POST'])
def track_progress():
    """Track detailed progress"""
    try:
        from backend.services.enhanced_progress_data import enhanced_progress_data
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        progress_type = data.get('progress_type', 'general')
        value = data.get('value', 0)
        metadata = data.get('metadata', {})
        
        result = enhanced_progress_data.track_progress(user_id, progress_type, value, metadata)
        
        # Also add to point accumulation
        if 'point_type' in metadata:
            enhanced_progress_data.add_point_entry(user_id, metadata['point_type'], value)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error tracking progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/progress/<user_id>/leveling', methods=['GET'])
def get_leveling_analytics(user_id: str):
    """Get leveling analytics"""
    try:
        from backend.services.enhanced_progress_data import enhanced_progress_data
        
        analytics = enhanced_progress_data.calculate_leveling_analytics(user_id)
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        logger.error(f"Error getting leveling analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/progress/<user_id>/graph', methods=['GET'])
def get_point_graph(user_id: str):
    """Get point accumulation graph"""
    try:
        from backend.services.enhanced_progress_data import enhanced_progress_data
        
        days = request.args.get('days', 30, type=int)
        graph_data = enhanced_progress_data.generate_point_accumulation_graph(user_id, days)
        
        return jsonify({
            'success': True,
            'graph_data': graph_data
        })
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/progress/<user_id>/predictions', methods=['GET'])
def get_achievement_predictions(user_id: str):
    """Get achievement predictions"""
    try:
        from backend.services.enhanced_progress_data import enhanced_progress_data
        
        predictions = enhanced_progress_data.predict_achievements(user_id)
        return jsonify({
            'success': True,
            'predictions': predictions
        })
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/progress/<user_id>/benchmarks', methods=['GET'])
def get_performance_benchmarks(user_id: str):
    """Get performance benchmarks"""
    try:
        from backend.services.enhanced_progress_data import enhanced_progress_data
        
        benchmarks = enhanced_progress_data.calculate_performance_benchmarks(user_id)
        return jsonify({
            'success': True,
            'benchmarks': benchmarks
        })
    except Exception as e:
        logger.error(f"Error getting benchmarks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Video Generation Rewards Routes
@progress_rewards_bp.route('/video/generate', methods=['POST'])
def award_video_generation():
    """Award points for video generation"""
    try:
        from backend.services.video_generation_rewards import video_generation_rewards
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        video_data = data.get('video_data', {})
        
        result = video_generation_rewards.award_video_generation(user_id, video_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error awarding video generation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/clip/generate', methods=['POST'])
def award_clip_generation():
    """Award points for clip generation"""
    try:
        from backend.services.video_generation_rewards import video_generation_rewards
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        clip_data = data.get('clip_data', {})
        
        result = video_generation_rewards.award_clip_generation(user_id, clip_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error awarding clip generation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_rewards_bp.route('/generation/<user_id>/stats', methods=['GET'])
def get_generation_stats(user_id: str):
    """Get video/clip generation statistics"""
    try:
        from backend.services.video_generation_rewards import video_generation_rewards
        
        stats = video_generation_rewards.get_generation_stats(user_id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting generation stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
