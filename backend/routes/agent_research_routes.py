"""
Agent Research Routes
API endpoints for research and monitoring
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_research_tracker import agent_research_tracker
from backend.services.agent_trigger_system import agent_trigger_system
from backend.services.agent_activation_system import agent_activation_system

agent_research_bp = Blueprint('agent_research', __name__)

# ========== RESEARCH ENDPOINTS ==========

@agent_research_bp.route('/api/agent/research/start', methods=['POST'])
def start_research():
    """Start a research project"""
    try:
        data = request.get_json() or {}
        topic_id = data.get('topic_id')
        agent_id = data.get('agent_id', 'master_fix_agent')
        
        if not topic_id:
            return jsonify({
                'success': False,
                'error': 'topic_id required'
            }), 400
        
        result = agent_research_tracker.start_research(topic_id, agent_id)
        
        # Award points via trigger
        if result.get('success'):
            agent_trigger_system.award_points('research_completed', agent_id, {
                'topic_id': topic_id
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/research/finding', methods=['POST'])
def add_finding():
    """Add a research finding"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        finding = data.get('finding', {})
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'project_id required'
            }), 400
        
        result = agent_research_tracker.add_research_finding(project_id, finding)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/research/summary', methods=['GET'])
def get_research_summary():
    """Get research summary"""
    try:
        result = agent_research_tracker.get_research_summary()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== MONITORING ENDPOINTS ==========

@agent_research_bp.route('/api/agent/monitoring/collect', methods=['POST'])
def collect_monitoring_data():
    """Collect monitoring data"""
    try:
        data = request.get_json() or {}
        target_id = data.get('target_id')
        metrics = data.get('metrics', {})
        
        if not target_id:
            return jsonify({
                'success': False,
                'error': 'target_id required'
            }), 400
        
        result = agent_research_tracker.collect_monitoring_data(target_id, metrics)
        
        # Award points via trigger
        if result.get('success'):
            agent_trigger_system.award_points('health_check', 'agent_user', {
                'target_id': target_id
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/monitoring/alert', methods=['POST'])
def create_alert():
    """Create a monitoring alert"""
    try:
        data = request.get_json() or {}
        target_id = data.get('target_id')
        alert_type = data.get('type', 'warning')
        message = data.get('message', '')
        severity = data.get('severity', 'medium')
        
        if not target_id or not message:
            return jsonify({
                'success': False,
                'error': 'target_id and message required'
            }), 400
        
        result = agent_research_tracker.create_alert(target_id, alert_type, message, severity)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/monitoring/summary', methods=['GET'])
def get_monitoring_summary():
    """Get monitoring summary"""
    try:
        result = agent_research_tracker.get_monitoring_summary()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== TRIGGER ENDPOINTS ==========

@agent_research_bp.route('/api/agent/triggers/award', methods=['POST'])
def award_points():
    """Award points via trigger"""
    try:
        data = request.get_json() or {}
        trigger_id = data.get('trigger_id')
        user_id = data.get('user_id', 'agent_user')
        metadata = data.get('metadata', {})
        
        if not trigger_id:
            return jsonify({
                'success': False,
                'error': 'trigger_id required'
            }), 400
        
        result = agent_trigger_system.award_points(trigger_id, user_id, metadata)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/triggers/stats', methods=['GET'])
def get_trigger_stats():
    """Get trigger statistics"""
    try:
        result = agent_trigger_system.get_trigger_stats()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== ACTIVATION ENDPOINTS ==========

@agent_research_bp.route('/api/agent/activation/status', methods=['GET'])
def get_activation_status():
    """Get activation system status"""
    try:
        result = agent_activation_system.get_status()
        return jsonify({
            'success': True,
            'status': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/activation/start', methods=['POST'])
def start_activation():
    """Start activation system"""
    try:
        agent_activation_system.start()
        return jsonify({
            'success': True,
            'message': 'Activation system started'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_research_bp.route('/api/agent/activation/add', methods=['POST'])
def add_activation():
    """Add a new activation"""
    try:
        data = request.get_json() or {}
        result = agent_activation_system.add_activation(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
