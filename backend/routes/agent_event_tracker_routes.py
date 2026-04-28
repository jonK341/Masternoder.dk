"""
Event Tracker Routes
API endpoints for Event Tracker agent technology
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_techs.agent_event_tracker import agent_event_tracker

agent_event_tracker_bp = Blueprint('agent_event_tracker', __name__)

# ========== STATUS & METRICS ==========

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/status', methods=['GET'])
def get_agent_event_tracker_status():
    """Get Event Tracker status"""
    try:
        status = agent_event_tracker.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/metrics', methods=['GET'])
def get_agent_event_tracker_metrics():
    """Get Event Tracker metrics"""
    try:
        metrics = agent_event_tracker.get_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== IMPROVEMENT FUNCTIONS ==========

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/optimize_performance', methods=['POST'])
def agent_event_tracker_optimize_performance():
    """Execute Optimize Performance improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.optimize_performance(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/enhance_security', methods=['POST'])
def agent_event_tracker_enhance_security():
    """Execute Enhance Security improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.enhance_security(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/improve_reliability', methods=['POST'])
def agent_event_tracker_improve_reliability():
    """Execute Improve Reliability improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.improve_reliability(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/scale_capacity', methods=['POST'])
def agent_event_tracker_scale_capacity():
    """Execute Scale Capacity improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.scale_capacity(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/reduce_latency', methods=['POST'])
def agent_event_tracker_reduce_latency():
    """Execute Reduce Latency improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.reduce_latency(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/increase_throughput', methods=['POST'])
def agent_event_tracker_increase_throughput():
    """Execute Increase Throughput improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.increase_throughput(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/add_monitoring', methods=['POST'])
def agent_event_tracker_add_monitoring():
    """Execute Add Monitoring improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.add_monitoring(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/enable_auto_recovery', methods=['POST'])
def agent_event_tracker_enable_auto_recovery():
    """Execute Enable Auto Recovery improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.enable_auto_recovery(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/improve_caching', methods=['POST'])
def agent_event_tracker_improve_caching():
    """Execute Improve Caching improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.improve_caching(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/enhance_logging', methods=['POST'])
def agent_event_tracker_enhance_logging():
    """Execute Enhance Logging improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.enhance_logging(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/add_analytics', methods=['POST'])
def agent_event_tracker_add_analytics():
    """Execute Add Analytics improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.add_analytics(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/upgrade_algorithm', methods=['POST'])
def agent_event_tracker_upgrade_algorithm():
    """Execute Upgrade Algorithm improvement"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        params = data.get('params', {})
        result = agent_event_tracker.upgrade_algorithm(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== NEW TASK (INTELLIGENCE) ==========

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/track_new_task', methods=['POST'])
def agent_event_tracker_track_new_task():
    """Track new agent task; fires event_tracker_new_task trigger."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        task_name = data.get('task_name', '')
        params = data.get('params', {})
        result = agent_event_tracker.track_new_task(user_id, task_name, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/new_tasks', methods=['GET'])
def agent_event_tracker_new_tasks_list():
    """List recent new tasks."""
    try:
        tasks = agent_event_tracker.data.get('new_tasks', [])[-50:]
        return jsonify({'success': True, 'new_tasks': tasks, 'count': len(tasks)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== EXECUTE ACTION ==========

@agent_event_tracker_bp.route('/api/agent-tech/agent_event_tracker/execute', methods=['POST'])
def execute_agent_event_tracker():
    """Execute Event Tracker action"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'default')
        params = data.get('params', {})
        result = agent_event_tracker.execute(action, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
