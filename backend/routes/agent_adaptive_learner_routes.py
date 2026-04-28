"""
Adaptive Learner Routes
API endpoints for Adaptive Learner agent technology
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_techs.agent_adaptive_learner import agent_adaptive_learner

agent_adaptive_learner_bp = Blueprint('agent_adaptive_learner', __name__)

# ========== STATUS & METRICS ==========

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/status', methods=['GET'])
def get_agent_adaptive_learner_status():
    """Get Adaptive Learner status"""
    try:
        status = agent_adaptive_learner.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/metrics', methods=['GET'])
def get_agent_adaptive_learner_metrics():
    """Get Adaptive Learner metrics"""
    try:
        metrics = agent_adaptive_learner.get_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== IMPROVEMENT FUNCTIONS ==========

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/optimize_performance', methods=['POST'])
def agent_adaptive_learner_optimize_performance():
    """Execute Optimize Performance improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.optimize_performance(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/enhance_security', methods=['POST'])
def agent_adaptive_learner_enhance_security():
    """Execute Enhance Security improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.enhance_security(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/improve_reliability', methods=['POST'])
def agent_adaptive_learner_improve_reliability():
    """Execute Improve Reliability improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.improve_reliability(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/scale_capacity', methods=['POST'])
def agent_adaptive_learner_scale_capacity():
    """Execute Scale Capacity improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.scale_capacity(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/reduce_latency', methods=['POST'])
def agent_adaptive_learner_reduce_latency():
    """Execute Reduce Latency improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.reduce_latency(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/increase_throughput', methods=['POST'])
def agent_adaptive_learner_increase_throughput():
    """Execute Increase Throughput improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.increase_throughput(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/add_monitoring', methods=['POST'])
def agent_adaptive_learner_add_monitoring():
    """Execute Add Monitoring improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.add_monitoring(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/enable_auto_recovery', methods=['POST'])
def agent_adaptive_learner_enable_auto_recovery():
    """Execute Enable Auto Recovery improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.enable_auto_recovery(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/improve_caching', methods=['POST'])
def agent_adaptive_learner_improve_caching():
    """Execute Improve Caching improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.improve_caching(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/enhance_logging', methods=['POST'])
def agent_adaptive_learner_enhance_logging():
    """Execute Enhance Logging improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.enhance_logging(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/add_analytics', methods=['POST'])
def agent_adaptive_learner_add_analytics():
    """Execute Add Analytics improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.add_analytics(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/upgrade_algorithm', methods=['POST'])
def agent_adaptive_learner_upgrade_algorithm():
    """Execute Upgrade Algorithm improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_adaptive_learner.upgrade_algorithm(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== EXECUTE ACTION ==========

@agent_adaptive_learner_bp.route('/api/agent-tech/agent_adaptive_learner/execute', methods=['POST'])
def execute_agent_adaptive_learner():
    """Execute Adaptive Learner action"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'default')
        params = data.get('params', {})
        result = agent_adaptive_learner.execute(action, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
