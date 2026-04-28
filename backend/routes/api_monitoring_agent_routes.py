"""
API Monitoring Agent Routes
API endpoints for the API monitoring agent skill
"""
from flask import Blueprint, jsonify, request
from backend.services.api_monitoring_agent import api_monitoring_agent

api_monitoring_agent_bp = Blueprint('api_monitoring_agent', __name__)

@api_monitoring_agent_bp.route('/api/agent/monitoring/status', methods=['GET'])
def get_status():
    """Get monitoring agent status"""
    try:
        status = api_monitoring_agent.get_status()
        return jsonify({
            'success': True,
            'status': status
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/scan', methods=['POST'])
def trigger_scan():
    """Trigger a monitoring scan"""
    try:
        result = api_monitoring_agent.perform_scan()
        return jsonify({
            'success': result.get('success', False),
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/cycle', methods=['POST'])
def run_cycle():
    """Run a complete monitoring cycle"""
    try:
        result = api_monitoring_agent.run_monitoring_cycle()
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/alerts', methods=['GET'])
def get_alerts():
    """Get monitoring alerts"""
    try:
        limit = int(request.args.get('limit', 50))
        alerts = api_monitoring_agent.get_alerts(limit)
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/alerts/clear', methods=['POST'])
def clear_alerts():
    """Clear all alerts"""
    try:
        api_monitoring_agent.clear_alerts()
        return jsonify({
            'success': True,
            'message': 'Alerts cleared'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/config', methods=['GET', 'POST'])
def config():
    """Get or update monitoring configuration"""
    try:
        if request.method == 'GET':
            status = api_monitoring_agent.get_status()
            return jsonify({
                'success': True,
                'config': {
                    'monitoring_enabled': status['enabled'],
                    'auto_generate_enabled': status['auto_generate_enabled'],
                    'scan_interval_hours': status['scan_interval_hours'],
                    'thresholds': status['thresholds']
                }
            }), 200
        else:
            # POST - Update config
            data = request.get_json() or {}
            updated_status = api_monitoring_agent.update_config(data)
            return jsonify({
                'success': True,
                'message': 'Configuration updated',
                'status': updated_status
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_monitoring_agent_bp.route('/api/agent/monitoring/auto-generate', methods=['POST'])
def auto_generate():
    """Trigger auto-generation of missing methods"""
    try:
        data = request.get_json() or {}
        dry_run = data.get('dry_run', True)
        
        result = api_monitoring_agent.auto_generate_missing(dry_run=dry_run)
        return jsonify({
            'success': result.get('success', False),
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
