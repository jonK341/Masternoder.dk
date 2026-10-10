"""
System History & Psychology Routes
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

system_history_bp = Blueprint('system_history', __name__, url_prefix='/api/history')

@system_history_bp.route('/user/<user_id>/timeline', methods=['GET'])
def get_user_timeline(user_id: str):
    """Get user progression timeline"""
    try:
        from backend.services.system_history import system_history
        
        limit = request.args.get('limit', 100, type=int)
        timeline = system_history.get_user_timeline(user_id, limit)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'timeline': timeline,
            'total_events': len(timeline)
        })
    except Exception as e:
        logger.error(f"Error getting user timeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/user/<user_id>/milestones', methods=['GET'])
def get_user_milestones(user_id: str):
    """Get user achievement milestones"""
    try:
        from backend.services.system_history import system_history
        
        milestones = system_history.get_user_milestones(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'milestones': milestones,
            'total_milestones': len(milestones)
        })
    except Exception as e:
        logger.error(f"Error getting milestones: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/system', methods=['GET'])
def get_system_history():
    """Get system-wide history"""
    try:
        from backend.services.system_history import system_history
        
        limit = request.args.get('limit', 100, type=int)
        history = system_history.get_system_history(limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'total_entries': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting system history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/user/<user_id>/psychology', methods=['GET'])
def get_psychological_profile(user_id: str):
    """Get user psychological profile"""
    try:
        from backend.services.system_history import psychology_system
        
        profile = psychology_system.get_psychological_profile(user_id)
        
        return jsonify({
            'success': True,
            'profile': profile
        })
    except Exception as e:
        logger.error(f"Error getting psychological profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/user/<user_id>/behavior', methods=['POST'])
def analyze_behavior(user_id: str):
    """Analyze user behavior"""
    try:
        from backend.services.system_history import psychology_system
        
        data = request.get_json() or {}
        activity_data = data.get('activity_data', {})
        
        analysis = psychology_system.analyze_behavior(user_id, activity_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error analyzing behavior: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/user/<user_id>/motivation', methods=['POST'])
def track_motivation(user_id: str):
    """Track user motivation"""
    try:
        from backend.services.system_history import psychology_system
        
        data = request.get_json() or {}
        point_gain = data.get('point_gain', 0)
        activity_type = data.get('activity_type', 'unknown')
        
        motivation = psychology_system.track_motivation(user_id, point_gain, activity_type)
        
        return jsonify({
            'success': True,
            'motivation': motivation
        })
    except Exception as e:
        logger.error(f"Error tracking motivation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/search/<user_id>/perform', methods=['POST'])
def perform_intelligent_search(user_id: str):
    """Perform intelligent search with 7 tech upgrades"""
    try:
        from backend.services.search_intelligence import search_intelligence
        from backend.services.unified_points_database import unified_points_db
        
        data = request.get_json() or {}
        query = data.get('query', '')
        search_type = data.get('search_type', 'standard')
        metadata = data.get('metadata', {})
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query required'
            }), 400
        
        # Perform search
        search_result = search_intelligence.perform_search(user_id, query, search_type, metadata)
        
        # Award points
        unified_points_db.add_points(
            user_id,
            'search',
            search_result['total_points'],
            source='intelligent_search'
        )
        
        return jsonify({
            'success': True,
            'search_result': search_result
        })
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/search/<user_id>/stats', methods=['GET'])
def get_search_stats(user_id: str):
    """Get user search statistics"""
    try:
        from backend.services.search_intelligence import search_intelligence
        
        stats = search_intelligence.get_search_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_history_bp.route('/search/tech-upgrades', methods=['GET'])
def get_tech_upgrades():
    """Get status of all tech upgrades"""
    try:
        from backend.services.search_intelligence import search_intelligence
        
        upgrades = search_intelligence.get_tech_upgrades_status()
        
        return jsonify({
            'success': True,
            'tech_upgrades': upgrades,
            'total_upgrades': len(upgrades)
        })
    except Exception as e:
        logger.error(f"Error getting tech upgrades: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
