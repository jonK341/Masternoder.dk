"""
Test route for generator debugger - simple test to verify routing works
"""
from flask import Blueprint, jsonify

generator_debugger_test_bp = Blueprint('generator_debugger_test', __name__)

@generator_debugger_test_bp.route('/test-generator-debugger')
@generator_debugger_test_bp.route('/vidgenerator/test-generator-debugger')
def test_route():
    """Simple test route to verify blueprint is working"""
    return jsonify({
        'success': True,
        'message': 'Generator debugger blueprint is working!',
        'routes': [
            '/generator-debugger',
            '/vidgenerator/generator-debugger',
            '/api/generator/debug',
            '/vidgenerator/api/generator/debug'
        ]
    })

