"""
Agent Task Force Routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.services.agent_task_force import agent_task_force

agent_task_force_bp = Blueprint('agent_task_force', __name__, url_prefix='/api/agent-task-force')


@agent_task_force_bp.route('/objective/create', methods=['POST'])
def create_objective():
    """Create a new objective"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        title = data.get('title', '')
        description = data.get('description', '')
        objective_type = data.get('type', 'mission')
        priority = int(data.get('priority', 5))
        deadline_str = data.get('deadline')
        
        deadline = None
        if deadline_str:
            deadline = datetime.fromisoformat(deadline_str)
        
        result = agent_task_force.create_objective(
            user_id, title, description, objective_type, priority, deadline
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/objective/<objective_id>/assign', methods=['POST'])
def assign_objective(objective_id: str):
    """Assign objective to user"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        result = agent_task_force.assign_objective(user_id, objective_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/objective/<objective_id>/progress', methods=['POST'])
def update_progress(objective_id: str):
    """Update objective progress"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        progress = int(data.get('progress', 0))
        
        result = agent_task_force.update_objective_progress(user_id, objective_id, progress)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/mission/create', methods=['POST'])
def create_mission():
    """Create a mission"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        mission_name = data.get('mission_name', '')
        mission_type = data.get('mission_type', 'general')
        objectives = data.get('objectives', [])
        reward_points = int(data.get('reward_points', 100))
        
        result = agent_task_force.create_mission(
            user_id, mission_name, mission_type, objectives, reward_points
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/user/<user_id>/objectives', methods=['GET'])
def get_user_objectives(user_id: str):
    """Get user objectives"""
    try:
        result = agent_task_force.get_user_objectives(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/user/<user_id>/missions', methods=['GET'])
def get_user_missions(user_id: str):
    """Get user missions"""
    try:
        result = agent_task_force.get_user_missions(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/calendar/<user_id>', methods=['GET'])
def get_calendar_events(user_id: str):
    """Get calendar events"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
        
        result = agent_task_force.get_calendar_events(user_id, start_date, end_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/opinion/record', methods=['POST'])
def record_opinion():
    """Record agent opinion"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        opinion_type = data.get('type', 'general')
        content = data.get('content', '')
        confidence = float(data.get('confidence', 0.5))
        
        result = agent_task_force.record_agent_opinion(user_id, opinion_type, content, confidence)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/observation/record', methods=['POST'])
def record_observation():
    """Record observation"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        observation_type = data.get('type', 'general')
        observation_data = data.get('data', {})
        
        result = agent_task_force.record_observation(user_id, observation_type, observation_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/emotion/update', methods=['POST'])
def update_emotion():
    """Update emotion"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        emotion_type = data.get('emotion_type', 'neutral')
        intensity = float(data.get('intensity', 0.5))
        
        result = agent_task_force.update_emotion(user_id, emotion_type, intensity)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/emotion/<user_id>', methods=['GET'])
def get_emotions(user_id: str):
    """Get user emotions"""
    try:
        result = agent_task_force.get_emotions(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_task_force_bp.route('/behavior-patterns/<user_id>', methods=['GET'])
def get_behavior_patterns(user_id: str):
    """Get behavior patterns"""
    try:
        result = agent_task_force.get_behavior_patterns(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
