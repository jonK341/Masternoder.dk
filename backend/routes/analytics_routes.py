"""
Analytics Routes
API endpoints for analytics dashboard
"""
from flask import Blueprint, request, jsonify
from backend.services.analytics_service import analytics_service
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import uuid

analytics_bp = Blueprint('analytics', __name__, url_prefix='')


@analytics_bp.route('/api/analytics/overview', methods=['GET'])
@analytics_bp.route('/vidgenerator/api/analytics/overview', methods=['GET'])
@rate_limit(endpoint='/api/analytics/overview')
def get_analytics_overview():
    """Get system analytics overview"""
    try:
        overview = analytics_service.get_system_overview()
        return jsonify({
            'success': True,
            'overview': overview
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@analytics_bp.route('/api/analytics/user-behavior', methods=['GET'])
@analytics_bp.route('/vidgenerator/api/analytics/user-behavior', methods=['GET'])
@rate_limit(endpoint='/api/analytics/user-behavior')
def get_user_behavior():
    """Get user behavior analytics"""
    try:
        timeframe = request.args.get('timeframe', 'week')
        behavior = analytics_service.get_user_behavior_analytics(timeframe)
        
        return jsonify({
            'success': True,
            'behavior': behavior
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@analytics_bp.route('/api/analytics/revenue', methods=['GET'])
@analytics_bp.route('/vidgenerator/api/analytics/revenue', methods=['GET'])
@rate_limit(endpoint='/api/analytics/revenue')
def get_revenue_analytics():
    """Get revenue analytics"""
    try:
        revenue = analytics_service.get_revenue_analytics()
        return jsonify({
            'success': True,
            'revenue': revenue
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@analytics_bp.route('/api/analytics/leaderboard', methods=['GET'])
@analytics_bp.route('/vidgenerator/api/analytics/leaderboard', methods=['GET'])
@rate_limit(endpoint='/api/analytics/leaderboard')
def get_leaderboard_analytics():
    """Get leaderboard analytics"""
    try:
        analytics = analytics_service.get_leaderboard_analytics()
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@analytics_bp.route('/api/analytics/export', methods=['GET'])
@analytics_bp.route('/vidgenerator/api/analytics/export', methods=['GET'])
@rate_limit(endpoint='/api/analytics/export')
def export_analytics():
    """Export analytics data"""
    try:
        format_type = request.args.get('format', 'json')
        result = analytics_service.export_analytics(format_type)
        
        if format_type == 'csv':
            from flask import Response
            return Response(
                result['data'],
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=analytics-{datetime.utcnow().strftime("%Y%m%d")}.csv'}
            )
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
