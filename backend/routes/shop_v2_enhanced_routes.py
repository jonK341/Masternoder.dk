"""
Shop V2 Enhanced Routes
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

shop_v2_enhanced_bp = Blueprint('shop_v2_enhanced', __name__, url_prefix='/api/shop-v2')

@shop_v2_enhanced_bp.route('/items', methods=['GET'])
def get_items():
    """Get all shop items with filtering"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        category = request.args.get('category', 'all')
        search = request.args.get('search', '')
        filters = {}
        
        if request.args.get('rarity'):
            filters['rarity'] = request.args.get('rarity')
        if request.args.get('max_price'):
            filters['max_price'] = float(request.args.get('max_price'))
        if request.args.get('min_price'):
            filters['min_price'] = float(request.args.get('min_price'))
        
        result = shop_v2_enhanced.get_all_items(category, search, filters)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shop_v2_enhanced_bp.route('/wishlist/add', methods=['POST'])
def add_to_wishlist():
    """Add item to wishlist"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        item_id = data.get('item_id')
        
        if not item_id:
            return jsonify({
                'success': False,
                'error': 'Item ID required'
            }), 400
        
        result = shop_v2_enhanced.add_to_wishlist(user_id, item_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error adding to wishlist: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shop_v2_enhanced_bp.route('/wishlist/<user_id>', methods=['GET'])
def get_wishlist(user_id: str):
    """Get user wishlist"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        result = shop_v2_enhanced.get_wishlist(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting wishlist: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shop_v2_enhanced_bp.route('/purchase', methods=['POST'])
def purchase_item():
    """Purchase an item"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        item_id = data.get('item_id')
        
        if not item_id:
            return jsonify({
                'success': False,
                'error': 'Item ID required'
            }), 400
        
        result = shop_v2_enhanced.purchase_item(user_id, item_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error purchasing item: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shop_v2_enhanced_bp.route('/history/<user_id>', methods=['GET'])
def get_purchase_history(user_id: str):
    """Get purchase history"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        result = shop_v2_enhanced.get_purchase_history(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shop_v2_enhanced_bp.route('/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id: str):
    """Get personalized recommendations"""
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        
        result = shop_v2_enhanced.get_recommendations(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
