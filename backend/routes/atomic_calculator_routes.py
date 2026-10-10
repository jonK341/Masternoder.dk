"""
Atomic Calculator Routes - Hell & Money Satan Edition
Advanced atomic calculations for financial/monetary systems
"""
from flask import Blueprint, jsonify, request
from backend.services.atomic_calculator_hell_money import atomic_calculator_hell_money
from decimal import Decimal

atomic_calculator_bp = Blueprint('atomic_calculator', __name__)


@atomic_calculator_bp.route('/api/atomic-calculator/calculate', methods=['POST'])
@atomic_calculator_bp.route('/vidgenerator/api/atomic-calculator/calculate', methods=['POST'])
def atomic_calculate():
    """Perform atomic calculation"""
    try:
        data = request.get_json() or {}
        base_value = Decimal(str(data.get('base_value', 0)))
        calculation_type = data.get('calculation_type', 'hell_money')
        params = data.get('params', {})
        
        result = atomic_calculator_hell_money.atomic_calculate(base_value, calculation_type, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@atomic_calculator_bp.route('/api/atomic-calculator/financial-metrics', methods=['POST'])
@atomic_calculator_bp.route('/vidgenerator/api/atomic-calculator/financial-metrics', methods=['POST'])
def calculate_financial_metrics():
    """Calculate comprehensive financial metrics"""
    try:
        data = request.get_json() or {}
        base_value = Decimal(str(data.get('base_value', 0)))
        metrics = data.get('metrics', ['hell_money', 'satan_compound', 'atomic_interest'])
        
        result = atomic_calculator_hell_money.calculate_financial_metrics(base_value, metrics)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@atomic_calculator_bp.route('/api/atomic-calculator/money-satan-returns', methods=['POST'])
@atomic_calculator_bp.route('/vidgenerator/api/atomic-calculator/money-satan-returns', methods=['POST'])
def calculate_money_satan_returns():
    """Calculate Money Satan returns on investment"""
    try:
        data = request.get_json() or {}
        investment = Decimal(str(data.get('investment', 0)))
        time_periods = data.get('time_periods', 1)
        
        result = atomic_calculator_hell_money.calculate_money_satan_returns(investment, time_periods)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

