"""
Model Operator Routes
API endpoints for model operator
"""
from flask import Blueprint, request, jsonify
from backend.services.model_operator import model_operator
from src.utils.rate_limiter import rate_limit
import sys

model_operator_bp = Blueprint('model_operator', __name__)


@model_operator_bp.route('/api/model-operator/models', methods=['GET'])
@model_operator_bp.route('/vidgenerator/api/model-operator/models', methods=['GET'])
@rate_limit()
def get_all_models():
    """Get all models"""
    try:
        result = model_operator.get_all_models()
        return jsonify(result), 200
    except Exception as e:
        print(f"[ModelOperator] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@model_operator_bp.route('/api/model-operator/operate', methods=['POST'])
@model_operator_bp.route('/vidgenerator/api/model-operator/operate', methods=['POST'])
@rate_limit()
def operate_model():
    """Operate a model"""
    try:
        data = request.get_json() or {}
        model_id = data.get('model_id')
        operation = data.get('operation')
        params = data.get('params', {})
        
        if not model_id or not operation:
            return jsonify({
                'success': False,
                'error': 'model_id and operation required'
            }), 400
        
        result = model_operator.operate_model(model_id, operation, params)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ModelOperator] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@model_operator_bp.route('/api/model-operator/stats', methods=['GET'])
@model_operator_bp.route('/vidgenerator/api/model-operator/stats', methods=['GET'])
@rate_limit()
def get_model_stats():
    """Get model statistics"""
    try:
        model_id = request.args.get('model_id')
        result = model_operator.get_model_stats(model_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ModelOperator] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
