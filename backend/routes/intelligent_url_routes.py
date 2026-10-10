"""
Intelligent URL Routes
Adds intelligence and logic functions to URLs
"""
from flask import Blueprint, jsonify, request, redirect
from backend.services.intelligent_url_router import intelligent_url_router

intelligent_url_bp = Blueprint('intelligent_url', __name__)


@intelligent_url_bp.route('/api/url/process', methods=['POST'])
@intelligent_url_bp.route('/vidgenerator/api/url/process', methods=['POST'])
def process_url():
    """Process URL with intelligence and logic"""
    try:
        data = request.get_json() or {}
        url = data.get('url')
        user_id = data.get('user_id', 'default_user')
        context = data.get('context', {})
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'url required'
            }), 400
        
        result = intelligent_url_router.process_url(url, user_id, context)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@intelligent_url_bp.route('/api/url/register', methods=['POST'])
@intelligent_url_bp.route('/vidgenerator/api/url/register', methods=['POST'])
def register_intelligent_route():
    """Register intelligent route"""
    try:
        data = request.get_json() or {}
        url_pattern = data.get('url_pattern')
        logic_chain = data.get('logic_chain', [])
        
        if not url_pattern:
            return jsonify({
                'success': False,
                'error': 'url_pattern required'
            }), 400
        
        intelligent_url_router.register_intelligent_route(url_pattern, logic_chain)
        
        return jsonify({
            'success': True,
            'url_pattern': url_pattern,
            'logic_chain': logic_chain
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

