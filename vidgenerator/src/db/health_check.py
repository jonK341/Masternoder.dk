"""
Database health check endpoint and utilities
"""
from flask import Blueprint, jsonify
from datetime import datetime
from src.db.models import db
from src.db.init_db import DatabaseManager
from src.utils.system_metrics import get_system_metrics

health_check_bp = Blueprint('db_health', __name__)


@health_check_bp.route('/api/health/database', methods=['GET'])
def database_health_check():
    """
    Database health check endpoint
    
    Returns:
        JSON response with database health status
    """
    from flask import current_app
    
    try:
        manager = DatabaseManager(db, current_app)
        health = manager.check_database_health()
        info = manager.get_database_info()
        
        status_code = 200
        if health['status'] != 'healthy':
            status_code = 503  # Service Unavailable
        
        return jsonify({
            'success': True,
            'health': health,
            'info': info
        }), status_code
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {'status': 'error'}
        }), 500


@health_check_bp.route('/api/health/database/info', methods=['GET'])
def database_info():
    """
    Get database information endpoint
    
    Returns:
        JSON response with database information
    """
    from flask import current_app
    
    try:
        manager = DatabaseManager(db, current_app)
        info = manager.get_database_info()
        
        return jsonify({
            'success': True,
            'info': info
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@health_check_bp.route('/api/health/system', methods=['GET'])
def system_health():
    """
    Get system health status (database, metrics, system resources)
    
    Returns:
        JSON response with comprehensive system health
    """
    from flask import current_app
    
    try:
        metrics = get_system_metrics()
        health_status = metrics.get_health_status()
        system_info = metrics.get_system_info()
        request_stats = metrics.get_request_stats()
        endpoint_stats = metrics.get_endpoint_stats()
        
        # Get database health
        db_manager = DatabaseManager(db, current_app)
        db_health = db_manager.check_database_health()
        
        return jsonify({
            'success': True,
            'status': health_status['status'],
            'uptime': health_status['uptime_formatted'],
            'timestamp': health_status['timestamp'],
            'database': {
                'status': db_health['status'],
                'tables': db_health['table_count'],
                'issues': db_health.get('issues', [])
            },
            'system': system_info,
            'requests': request_stats,
            'endpoints': endpoint_stats,
            'issues': health_status.get('issues', [])
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 500


@health_check_bp.route('/api/metrics', methods=['GET'])
def get_metrics():
    """
    Get application metrics endpoint
    
    Returns:
        JSON response with performance metrics
    """
    try:
        metrics = get_system_metrics()
        
        return jsonify({
            'success': True,
            'metrics': {
                'requests': metrics.get_request_stats(),
                'endpoints': metrics.get_endpoint_stats(),
                'system': metrics.get_system_info(),
                'health': metrics.get_health_status()
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

