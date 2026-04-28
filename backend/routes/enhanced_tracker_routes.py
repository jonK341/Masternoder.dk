"""
Enhanced Tracker Routes
API endpoints for enhanced point tracking
"""
from flask import Blueprint, jsonify, request
from backend.services.enhanced_point_tracker import enhanced_point_tracker

enhanced_tracker_bp = Blueprint('enhanced_tracker', __name__)

@enhanced_tracker_bp.route('/api/tracker/start-session', methods=['POST'])
def start_session():
    """Start a generator session with extended time"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        extended_time = data.get('extended_time', True)
        
        result = enhanced_point_tracker.start_generator_session(user_id, extended_time)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_tracker_bp.route('/api/tracker/track-points', methods=['POST'])
def track_points():
    """Track point creation during session"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        point_type = data.get('point_type', 'generation_points')
        amount = data.get('amount', 0)
        source = data.get('source', 'generator')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'session_id required'}), 400
        
        result = enhanced_point_tracker.track_point_creation(session_id, point_type, amount, source)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_tracker_bp.route('/api/tracker/session/<session_id>', methods=['GET'])
def get_session_stats(session_id):
    """Get session statistics"""
    try:
        result = enhanced_point_tracker.get_session_stats(session_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_tracker_bp.route('/api/tracker/extend-session', methods=['POST'])
def extend_session():
    """Extend session time"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        additional_minutes = data.get('additional_minutes', 30)
        
        if not session_id:
            return jsonify({'success': False, 'error': 'session_id required'}), 400
        
        result = enhanced_point_tracker.extend_session_time(session_id, additional_minutes)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_tracker_bp.route('/api/tracker/stats', methods=['GET'])
def get_all_stats():
    """Get all tracking statistics"""
    try:
        result = enhanced_point_tracker.get_all_tracking_stats()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
