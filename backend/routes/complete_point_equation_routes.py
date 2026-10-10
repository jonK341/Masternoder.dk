"""
Complete Point Equation Routes
API endpoints for complete point counter equation
"""
from flask import Blueprint, request, jsonify
from backend.services.complete_point_equation import complete_point_equation

complete_equation_bp = Blueprint('complete_equation', __name__, url_prefix='/api/points/equation')

@complete_equation_bp.route('/test', methods=['GET'])
def test_equation():
    """Test endpoint for complete point equation"""
    return jsonify({'message': 'Complete Point Equation API is working!'}), 200

@complete_equation_bp.route('/calculate/<string:user_id>', methods=['GET'])
def calculate_total_points(user_id):
    """Calculate total points using complete equation"""
    points = complete_point_equation.calculate_total_points(user_id)
    return jsonify({'success': True, 'points': points}), 200

@complete_equation_bp.route('/breakdown/<string:user_id>', methods=['GET'])
def get_point_breakdown(user_id):
    """Get detailed point breakdown with equation"""
    breakdown = complete_point_equation.get_point_breakdown(user_id)
    return jsonify({'success': True, 'breakdown': breakdown}), 200

