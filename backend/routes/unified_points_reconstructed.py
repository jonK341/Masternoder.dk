"""
Unified Points API Routes - RECONSTRUCTED
Clean, logical API for the reconstructed unified point system
"""
from flask import Blueprint, request, jsonify
from backend.services.unified_point_system_reconstructed import unified_point_system
import logging

logger = logging.getLogger(__name__)

unified_points_reconstructed_bp = Blueprint('unified_points_reconstructed', __name__, url_prefix='/api/points')


@unified_points_reconstructed_bp.route('/all', methods=['GET'])
def get_all_points():
    """Get all points for a user"""
    try:
        user_id = request.args.get('user_id', 'default')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        points = unified_point_system.get_user_points(user_id, force_refresh=force_refresh)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'points': points
        }), 200
    except Exception as e:
        logger.error(f"Error getting all points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_points_reconstructed_bp.route('/add', methods=['POST'])
def add_points():
    """Add points to a user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        category = data.get('category')
        point_type = data.get('point_type')
        amount = data.get('amount', 0)
        source = data.get('source', 'api')
        
        if not category or not point_type:
            return jsonify({
                'success': False,
                'error': 'category and point_type are required'
            }), 400
        
        result = unified_point_system.add_points(user_id, category, point_type, amount, source)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error adding points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_points_reconstructed_bp.route('/set', methods=['POST'])
def set_points():
    """Set points to a specific value"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        category = data.get('category')
        point_type = data.get('point_type')
        value = data.get('value', 0)
        
        if not category or not point_type:
            return jsonify({
                'success': False,
                'error': 'category, point_type, and value are required'
            }), 400
        
        result = unified_point_system.set_points(user_id, category, point_type, value)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error setting points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_points_reconstructed_bp.route('/category/<category>', methods=['GET'])
def get_category_points(category):
    """Get all points for a specific category"""
    try:
        user_id = request.args.get('user_id', 'default')
        
        result = unified_point_system.get_category_points(user_id, category)
        
        if result.get('success') is False:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting category points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_points_reconstructed_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get summary of all points organized by category"""
    try:
        user_id = request.args.get('user_id', 'default')
        
        summary = unified_point_system.get_summary(user_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
    except Exception as e:
        logger.error(f"Error getting summary: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_points_reconstructed_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    try:
        categories = {}
        for key, info in unified_point_system.CATEGORIES.items():
            categories[key] = {
                'name': info['name'],
                'description': info['description'],
                'point_types': info['points']
            }
        
        return jsonify({
            'success': True,
            'categories': categories
        }), 200
    except Exception as e:
        logger.error(f"Error getting categories: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

