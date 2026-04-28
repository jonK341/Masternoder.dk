"""
Agent Judge Routes
API endpoints for agent judge
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_judge import agent_judge

agent_judge_bp = Blueprint('agent_judge', __name__)

@agent_judge_bp.route('/api/agents/judge/status', methods=['GET'])
def judge_status():
    """Get judge agent status"""
    try:
        result = agent_judge.get_status()
        return jsonify({'success': True, 'agent': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_judge_bp.route('/api/agents/judge/judge-content', methods=['POST'])
def judge_content():
    """Judge content quality"""
    try:
        data = request.get_json() or {}
        content_id = data.get('content_id')
        content_type = data.get('content_type', 'video')
        criteria = data.get('criteria', {})
        
        if not content_id:
            return jsonify({'success': False, 'error': 'content_id required'}), 400
        
        result = agent_judge.judge_content_quality(content_id, content_type, criteria)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_judge_bp.route('/api/agents/judge/evaluate-agent', methods=['POST'])
def evaluate_agent():
    """Evaluate agent performance"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id required'}), 400
        
        result = agent_judge.evaluate_agent_performance(agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_judge_bp.route('/api/agents/judge/rate-system', methods=['POST'])
def rate_system():
    """Rate system health"""
    try:
        result = agent_judge.rate_system_health()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
