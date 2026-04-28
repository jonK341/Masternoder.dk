"""
Point Calculator Routes
Simple API routes for the point calculator
"""
from flask import Blueprint, request, jsonify

try:
    from vidgenerator.src.services.point_calculator import PointCalculator
except ImportError:
    from src.services.point_calculator import PointCalculator

point_calculator_bp = Blueprint('point_calculator', __name__)


@point_calculator_bp.route('/api/point-calculator/calculate', methods=['POST'])
def calculate_points():
    """Calculate total points from point data"""
    try:
        data = request.get_json() or {}
        point_data = data.get('point_data', {})
        
        calculator = PointCalculator()
        result = calculator.calculate_total_points(point_data)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@point_calculator_bp.route('/api/point-calculator/system/<system_name>', methods=['POST'])
def calculate_system_points(system_name):
    """Calculate points for a single system"""
    try:
        data = request.get_json() or {}
        point_count = float(data.get('point_count', 0))
        
        calculator = PointCalculator()
        calculated = calculator.calculate_system_points(system_name, point_count)
        
        return jsonify({
            'success': True,
            'system_name': system_name,
            'point_count': point_count,
            'point_value': calculator.get_point_value(system_name),
            'calculated_points': calculated
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@point_calculator_bp.route('/api/point-calculator/systems', methods=['GET'])
def get_all_systems():
    """Get list of all systems"""
    try:
        calculator = PointCalculator()
        systems = calculator.get_all_systems()
        
        return jsonify({
            'success': True,
            'systems': systems,
            'count': len(systems)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@point_calculator_bp.route('/api/point-calculator/system/<system_name>/value', methods=['GET'])
def get_system_value(system_name):
    """Get point value for a system"""
    try:
        calculator = PointCalculator()
        point_value = calculator.get_point_value(system_name)
        
        if point_value == 0 and system_name not in calculator.get_all_systems():
            return jsonify({
                'success': False,
                'error': f'System "{system_name}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'system_name': system_name,
            'point_value': point_value
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
