"""
Agent Tracker Routes
API endpoints for agent tracking data (live and history)
"""
from flask import Blueprint, jsonify, request
from backend.services.master_fix_agent_skills import master_fix_agent_skills
from backend.services.api_monitoring_agent import api_monitoring_agent
from backend.services.agent_activity_generator import agent_activity_generator

agent_tracker_bp = Blueprint('agent_tracker', __name__)

@agent_tracker_bp.route('/api/agent/tracker/live', methods=['GET'])
def get_live_tracker():
    """Get live agent activity (recording)"""
    try:
        # Get current status
        monitoring_status = api_monitoring_agent.get_status()
        
        # Get current personality
        personality = master_fix_agent_skills.skill_get_personality()
        
        # Get active missions
        active_missions = master_fix_agent_skills.skill_get_missions('active')
        
        # Get in-progress quests
        in_progress_quests = master_fix_agent_skills.skill_get_quests('in_progress')
        
        # Get recent activity (last 10)
        recent_history = master_fix_agent_skills.skill_get_history(limit=10)
        
        # Generate current activity
        current_activity = None
        if personality.get('success'):
            personality_type = personality.get('personality', {}).get('personality_type', 'analytical')
            current_activity = agent_activity_generator.generate_activity(personality_type)
        
        return jsonify({
            'success': True,
            'live': {
                'monitoring': {
                    'enabled': monitoring_status.get('enabled', False),
                    'last_scan': monitoring_status.get('last_scan'),
                    'should_scan': monitoring_status.get('should_scan', False),
                    'alerts_count': monitoring_status.get('alerts_count', 0)
                },
                'personality': personality.get('personality', {}),
                'current_activity': current_activity,
                'active_missions': active_missions.get('missions', []),
                'in_progress_quests': in_progress_quests.get('quests', []),
                'recent_activity': recent_history.get('history', [])[:5]
            },
            'timestamp': monitoring_status.get('last_scan') or 'never'
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@agent_tracker_bp.route('/api/agent/tracker/history', methods=['GET'])
def get_history_tracker():
    """Get agent history (playback)"""
    try:
        # Get full history
        limit = int(request.args.get('limit', 50))
        skill_filter = request.args.get('skill')
        history = master_fix_agent_skills.skill_get_history(limit=limit, skill_filter=skill_filter)
        
        # Get statistics
        stats = master_fix_agent_skills.skill_get_statistics()
        
        # Get completed missions
        completed_missions = master_fix_agent_skills.skill_get_missions('completed')
        
        # Get completed quests
        completed_quests = master_fix_agent_skills.skill_get_quests('completed')
        
        return jsonify({
            'success': True,
            'history': {
                'skill_history': history.get('history', []),
                'statistics': stats,
                'completed_missions': completed_missions.get('missions', []),
                'completed_quests': completed_quests.get('quests', []),
                'total_entries': history.get('count', 0)
            }
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@agent_tracker_bp.route('/api/agent/tracker/combined', methods=['GET'])
def get_combined_tracker():
    """Get both live and history data"""
    try:
        # Get live data
        live_response = get_live_tracker()
        live_data = live_response[0].get_json() if hasattr(live_response[0], 'get_json') else {}
        
        # Get history data
        history_response = get_history_tracker()
        history_data = history_response[0].get_json() if hasattr(history_response[0], 'get_json') else {}
        
        return jsonify({
            'success': True,
            'live': live_data.get('live', {}),
            'history': history_data.get('history', {}),
            'timestamp': live_data.get('timestamp', 'never')
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@agent_tracker_bp.route('/api/agent/tracker/activity-stream', methods=['GET'])
def get_activity_stream():
    """Get streaming activity data (for real-time updates)"""
    try:
        # Get recent history for stream
        history = master_fix_agent_skills.skill_get_history(limit=20)
        
        # Get current monitoring status
        monitoring_status = api_monitoring_agent.get_status()
        
        # Format as stream
        stream_data = {
            'activities': [
                {
                    'id': entry.get('skill', 'unknown'),
                    'timestamp': entry.get('timestamp', ''),
                    'type': 'skill_execution',
                    'data': entry.get('data', {})
                }
                for entry in history.get('history', [])
            ],
            'monitoring': {
                'status': 'active' if monitoring_status.get('enabled') else 'inactive',
                'last_scan': monitoring_status.get('last_scan'),
                'next_scan_due': monitoring_status.get('should_scan', False)
            }
        }
        
        return jsonify({
            'success': True,
            'stream': stream_data
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
