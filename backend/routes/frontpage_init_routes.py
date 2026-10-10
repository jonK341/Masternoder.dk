"""
Frontpage Initialization Routes
Initialize and start all systems: Points, Game, Battles
"""
from flask import Blueprint, jsonify, request
from backend.services.frontpage_initializer import frontpage_initializer
import sys

frontpage_init_bp = Blueprint('frontpage_init', __name__)

@frontpage_init_bp.route('/api/frontpage/init', methods=['GET', 'POST'])
@frontpage_init_bp.route('/vidgenerator/api/frontpage/init', methods=['GET', 'POST'])
def initialize_all_systems():
    """Initialize all systems: Points, Game, Battles"""
    try:
        if not frontpage_initializer.initialized:
            result = frontpage_initializer.initialize_all()
            if result:
                return jsonify({
                    'success': True,
                    'message': 'All systems initialized successfully',
                    'status': frontpage_initializer.get_status()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Initialization completed with some errors',
                    'status': frontpage_initializer.get_status()
                }), 200
        else:
            return jsonify({
                'success': True,
                'message': 'Systems already initialized',
                'status': frontpage_initializer.get_status()
            }), 200
    except Exception as e:
        print(f"[FrontpageInit] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'status': frontpage_initializer.get_status()
        }), 200  # Return 200 to avoid breaking frontend

@frontpage_init_bp.route('/api/frontpage/status', methods=['GET'])
@frontpage_init_bp.route('/vidgenerator/api/frontpage/status', methods=['GET'])
def get_init_status():
    """Get initialization status"""
    try:
        return jsonify({
            'success': True,
            'status': frontpage_initializer.get_status()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200
