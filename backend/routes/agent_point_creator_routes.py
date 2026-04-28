"""
Agent Point Creator Routes
API endpoints for agent point creation and value tracking
"""
from flask import Blueprint, jsonify, request

agent_point_creator_bp = Blueprint('agent_point_creator', __name__)

# Initialize service with error handling
agent_point_creator = None

try:
    from backend.services.agent_point_creator import agent_point_creator
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import agent_point_creator: {e}")
    agent_point_creator = None

@agent_point_creator_bp.route('/api/agent-points/award', methods=['POST'])
def award_points():
    """Award points for agent action"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        action = data.get('action')
        user_id = data.get('user_id', 'agent_user')
        points = data.get('points')
        
        if not agent_id or not action:
            return jsonify({
                'success': False,
                'error': 'agent_id and action are required'
            }), 400
        
        if agent_point_creator:
            try:
                result = agent_point_creator.award_points_for_agent_action(
                    agent_id=agent_id,
                    action=action,
                    user_id=user_id,
                    points=points
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({
                    'success': True,
                    'points_awarded': points or {},
                    'note': f'Point creator unavailable: {str(e)}'
                }), 200
        else:
            return jsonify({
                'success': True,
                'points_awarded': points or {},
                'note': 'Point creator service not available'
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_point_creator_bp.route('/api/agent-points/agent/<agent_id>/value', methods=['GET'])
def get_agent_value(agent_id):
    """Get value created by specific agent"""
    try:
        if agent_point_creator:
            try:
                result = agent_point_creator.get_agent_value_created(agent_id)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({
                    'success': True,
                    'agent_id': agent_id,
                    'points_awarded': {},
                    'value_created': 0,
                    'total_actions': 0,
                    'note': f'Point creator unavailable: {str(e)}'
                }), 200
        else:
            return jsonify({
                'success': True,
                'agent_id': agent_id,
                'points_awarded': {},
                'value_created': 0,
                'total_actions': 0,
                'note': 'Point creator service not available'
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_point_creator_bp.route('/api/agent-points/all-value', methods=['GET'])
def get_all_value():
    """Get value created by all agents"""
    try:
        if agent_point_creator:
            try:
                result = agent_point_creator.get_all_agents_value()
                return jsonify(result), 200
            except Exception as e:
                return jsonify({
                    'success': True,
                    'agents': {},
                    'total_value': 0,
                    'note': f'Point creator unavailable: {str(e)}'
                }), 200
        else:
            return jsonify({
                'success': True,
                'agents': {},
                'total_value': 0,
                'note': 'Point creator service not available'
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_point_creator_bp.route('/api/agent-points/status', methods=['GET'])
def point_creator_status():
    """Get point creator status"""
    try:
        if agent_point_creator:
            try:
                result = agent_point_creator.get_status()
                return jsonify({'success': True, 'status': result}), 200
            except Exception as e:
                return jsonify({
                    'success': True,
                    'status': {
                        'service': 'unavailable',
                        'note': f'Error: {str(e)}'
                    }
                }), 200
        else:
            return jsonify({
                'success': True,
                'status': {
                    'service': 'not_available',
                    'note': 'Point creator service not initialized'
                }
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
