"""
Shop v2.0 Routes
API endpoints for enhanced shop with intelligence
"""
from flask import Blueprint, request, jsonify
from backend.services.shop_v2_system import shop_v2

shop_v2_bp = Blueprint('shop_v2', __name__, url_prefix='/api/shop-v2')

@shop_v2_bp.route('/test', methods=['GET'])
def test_shop_v2():
    """Test endpoint for shop v2"""
    return jsonify({'message': 'Shop v2.0 API is working!'}), 200

@shop_v2_bp.route('/items', methods=['GET'])
def get_all_items():
    """Get all shop items"""
    items = shop_v2.get_all_items()
    return jsonify({'success': True, 'items': items}), 200

@shop_v2_bp.route('/intelligence/<string:user_id>', methods=['GET'])
def get_shop_intelligence(user_id):
    """Get shop intelligence recommendations"""
    intelligence = shop_v2.get_shop_intelligence(user_id)
    return jsonify({'success': True, 'intelligence': intelligence}), 200

@shop_v2_bp.route('/purchase', methods=['POST'])
def purchase_item():
    """Purchase item from shop"""
    data = request.get_json()
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    
    if not user_id or not item_id:
        return jsonify({'success': False, 'error': 'user_id and item_id are required'}), 400
    
    result = shop_v2.purchase_item(user_id, item_id, quantity)
    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 400

@shop_v2_bp.route('/inventory/<string:user_id>', methods=['GET'])
def get_user_inventory(user_id):
    """Get user inventory"""
    inventory = shop_v2.user_inventory.get(user_id, {})
    return jsonify({'success': True, 'inventory': inventory}), 200

@shop_v2_bp.route('/purchase-history/<string:user_id>', methods=['GET'])
def get_purchase_history(user_id):
    """Get user purchase history"""
    history = shop_v2.purchase_history.get(user_id, [])
    return jsonify({'success': True, 'history': history}), 200

