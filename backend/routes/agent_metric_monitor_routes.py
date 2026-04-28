"""
Metric Monitor Routes
API endpoints for Metric Monitor agent technology
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_techs.agent_metric_monitor import agent_metric_monitor

agent_metric_monitor_bp = Blueprint('agent_metric_monitor', __name__)

# ========== STATUS & METRICS ==========

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/status', methods=['GET'])
def get_agent_metric_monitor_status():
    """Get Metric Monitor status"""
    try:
        status = agent_metric_monitor.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/metrics', methods=['GET'])
def get_agent_metric_monitor_metrics():
    """Get Metric Monitor metrics"""
    try:
        metrics = agent_metric_monitor.get_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== IMPROVEMENT FUNCTIONS ==========

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/optimize_performance', methods=['POST'])
def agent_metric_monitor_optimize_performance():
    """Execute Optimize Performance improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.optimize_performance(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/enhance_security', methods=['POST'])
def agent_metric_monitor_enhance_security():
    """Execute Enhance Security improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.enhance_security(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/improve_reliability', methods=['POST'])
def agent_metric_monitor_improve_reliability():
    """Execute Improve Reliability improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.improve_reliability(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/scale_capacity', methods=['POST'])
def agent_metric_monitor_scale_capacity():
    """Execute Scale Capacity improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.scale_capacity(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/reduce_latency', methods=['POST'])
def agent_metric_monitor_reduce_latency():
    """Execute Reduce Latency improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.reduce_latency(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/increase_throughput', methods=['POST'])
def agent_metric_monitor_increase_throughput():
    """Execute Increase Throughput improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.increase_throughput(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/add_monitoring', methods=['POST'])
def agent_metric_monitor_add_monitoring():
    """Execute Add Monitoring improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.add_monitoring(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/enable_auto_recovery', methods=['POST'])
def agent_metric_monitor_enable_auto_recovery():
    """Execute Enable Auto Recovery improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.enable_auto_recovery(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/improve_caching', methods=['POST'])
def agent_metric_monitor_improve_caching():
    """Execute Improve Caching improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.improve_caching(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/enhance_logging', methods=['POST'])
def agent_metric_monitor_enhance_logging():
    """Execute Enhance Logging improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.enhance_logging(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/add_analytics', methods=['POST'])
def agent_metric_monitor_add_analytics():
    """Execute Add Analytics improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.add_analytics(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/upgrade_algorithm', methods=['POST'])
def agent_metric_monitor_upgrade_algorithm():
    """Execute Upgrade Algorithm improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_metric_monitor.upgrade_algorithm(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== EXECUTE ACTION ==========

@agent_metric_monitor_bp.route('/api/agent-tech/agent_metric_monitor/execute', methods=['POST'])
def execute_agent_metric_monitor():
    """Execute Metric Monitor action"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'default')
        params = data.get('params', {})
        result = agent_metric_monitor.execute(action, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
