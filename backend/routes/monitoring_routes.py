"""
Monitoring Routes
System monitoring and alerting endpoints
"""
from flask import Blueprint, jsonify, request
from backend.utils.monitoring import system_monitor

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/api/monitoring/summary', methods=['GET'])
def monitoring_summary():
    """Get monitoring summary"""
    try:
        summary = system_monitor.get_summary()
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/metrics', methods=['GET'])
def monitoring_metrics():
    """Get metrics"""
    try:
        metric_name = request.args.get('metric')
        hours = request.args.get('hours', 24, type=int)
        metrics = system_monitor.get_metrics(metric_name=metric_name, hours=hours)
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/alerts', methods=['GET'])
def monitoring_alerts():
    """Get alerts"""
    try:
        level = request.args.get('level')
        hours = request.args.get('hours', 24, type=int)
        alerts = system_monitor.get_alerts(level=level, hours=hours)
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
