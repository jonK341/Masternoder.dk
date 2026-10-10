"""
System Aggregator Routes
API endpoints for aggregated system data
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
system_aggregator_bp = Blueprint('system_aggregator', __name__)

try:
    from backend.services.system_aggregator import system_aggregator
except ImportError:
    system_aggregator = None
    logger.warning("System aggregator not available")


@system_aggregator_bp.route('/api/aggregator/all', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/all', methods=['GET'])
def get_all_systems_data():
    """Get aggregated data from all systems"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_all_systems_data(user_id)
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        logger.error(f"Error getting aggregated data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200


@system_aggregator_bp.route('/api/aggregator/dashboard', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get data formatted for unified dashboard"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_unified_dashboard_data(user_id)
        
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200


@system_aggregator_bp.route('/api/aggregator/frontend', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/frontend', methods=['GET'])
def get_all_frontend_data():
    """Get all data needed for frontend pages"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_all_frontend_data(user_id)
        
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error getting frontend data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200


@system_aggregator_bp.route('/api/aggregator/battle', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/battle', methods=['GET'])
def get_battle_data():
    """Get aggregated battle data"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_battle_data(user_id)
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        logger.error(f"Error getting battle data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200


@system_aggregator_bp.route('/api/aggregator/shop', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/shop', methods=['GET'])
def get_shop_data():
    """Get aggregated shop data"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_shop_data(user_id)
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        logger.error(f"Error getting shop data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200


@system_aggregator_bp.route('/api/aggregator/quest', methods=['GET'])
@system_aggregator_bp.route('/vidgenerator/api/aggregator/quest', methods=['GET'])
def get_quest_data():
    """Get aggregated quest data"""
    try:
        if not system_aggregator:
            return jsonify({
                'success': False,
                'error': 'System aggregator not available',
                'data': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        data = system_aggregator.get_quest_data(user_id)
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
    except Exception as e:
        logger.error(f"Error getting quest data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 200
