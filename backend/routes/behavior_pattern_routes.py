"""
Behavior Pattern Tracking API Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.behavior_pattern_tracker import behavior_tracker
import sys

behavior_pattern_bp = Blueprint('behavior_pattern', __name__)


@behavior_pattern_bp.route('/api/behavior-pattern/track/mouse', methods=['POST'], strict_slashes=False)
def track_mouse_movement():
    """Track mouse movement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        x = data.get('x', 0)
        y = data.get('y', 0)
        timestamp = data.get('timestamp')
        
        behavior_tracker.track_mouse_movement(user_id, x, y, timestamp)
        
        return jsonify({
            'success': True,
            'message': 'Mouse movement tracked'
        }), 200
    except Exception as e:
        print(f"[BehaviorPattern] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@behavior_pattern_bp.route('/api/behavior-pattern/track/click', methods=['POST'], strict_slashes=False)
def track_click():
    """Track click"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        x = data.get('x', 0)
        y = data.get('y', 0)
        element_type = data.get('element_type', 'unknown')
        timestamp = data.get('timestamp')
        
        behavior_tracker.track_click(user_id, x, y, element_type, timestamp)
        
        return jsonify({
            'success': True,
            'message': 'Click tracked'
        }), 200
    except Exception as e:
        print(f"[BehaviorPattern] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@behavior_pattern_bp.route('/api/behavior-pattern/track/scroll', methods=['POST'], strict_slashes=False)
def track_scroll():
    """Track scroll"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        scroll_depth = data.get('scroll_depth', 0)
        scroll_direction = data.get('scroll_direction', 'down')
        timestamp = data.get('timestamp')
        
        behavior_tracker.track_scroll(user_id, scroll_depth, scroll_direction, timestamp)
        
        return jsonify({
            'success': True,
            'message': 'Scroll tracked'
        }), 200
    except Exception as e:
        print(f"[BehaviorPattern] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@behavior_pattern_bp.route('/api/behavior-pattern/analysis', methods=['GET'], strict_slashes=False)
def get_analysis():
    """Get comprehensive behavior pattern analysis"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        analysis_type = request.args.get('type', 'comprehensive')
        
        if analysis_type == 'clicks':
            analysis = behavior_tracker.analyze_click_patterns(user_id)
        elif analysis_type == 'scrolls':
            analysis = behavior_tracker.analyze_scroll_patterns(user_id)
        elif analysis_type == 'mouse':
            analysis = behavior_tracker.analyze_mouse_movement(user_id)
        elif analysis_type == 'attention':
            analysis = behavior_tracker.get_attention_hotspots(user_id)
        elif analysis_type == 'timing':
            analysis = behavior_tracker.get_interaction_timing_analysis(user_id)
        else:
            analysis = behavior_tracker.get_comprehensive_analysis(user_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
    except Exception as e:
        print(f"[BehaviorPattern] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@behavior_pattern_bp.route('/api/behavior-pattern/test', methods=['GET'], strict_slashes=False)
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Behavior Pattern Tracking API is working',
        'endpoints': {
            'track_mouse': '/api/behavior-pattern/track/mouse (POST)',
            'track_click': '/api/behavior-pattern/track/click (POST)',
            'track_scroll': '/api/behavior-pattern/track/scroll (POST)',
            'analysis': '/api/behavior-pattern/analysis?user_id=USER_ID&type=TYPE'
        }
    }), 200

