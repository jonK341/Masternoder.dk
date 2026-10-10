"""
Academic Perspective Routes
API endpoints for 12 religion barriers and walls system
"""
from flask import Blueprint, request, jsonify
from backend.services.academic_perspective_system import academic_perspective_system
import logging

logger = logging.getLogger(__name__)

academic_perspective_bp = Blueprint('academic_perspective', __name__)

@academic_perspective_bp.route('/api/academic/barriers', methods=['GET'])
def get_barriers():
    """Get all 12 religion barriers"""
    try:
        barriers = academic_perspective_system.barriers
        return jsonify({
            'success': True,
            'barriers': barriers,
            'count': len(barriers)
        }), 200
    except Exception as e:
        logger.error(f"Error getting barriers: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@academic_perspective_bp.route('/api/academic/walls', methods=['GET'])
def get_walls():
    """Get all 12 religion walls"""
    try:
        walls = academic_perspective_system.walls
        return jsonify({
            'success': True,
            'walls': walls,
            'count': len(walls)
        }), 200
    except Exception as e:
        logger.error(f"Error getting walls: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@academic_perspective_bp.route('/api/academic/break-barrier', methods=['POST'])
def break_barrier():
    """Break through a religion barrier"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        barrier_id = data.get('barrier_id')
        method = data.get('method', 'understanding')
        
        if not barrier_id:
            return jsonify({
                'success': False,
                'error': 'barrier_id is required'
            }), 400
        
        result = academic_perspective_system.break_barrier(user_id, barrier_id, method)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error breaking barrier: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@academic_perspective_bp.route('/api/academic/penetrate-wall', methods=['POST'])
def penetrate_wall():
    """Penetrate a religion wall"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        wall_id = data.get('wall_id')
        approach = data.get('approach', 'analysis')
        
        if not wall_id:
            return jsonify({
                'success': False,
                'error': 'wall_id is required'
            }), 400
        
        result = academic_perspective_system.penetrate_wall(user_id, wall_id, approach)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error penetrating wall: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@academic_perspective_bp.route('/api/academic/create-synergy', methods=['POST'])
def create_synergy():
    """Create synergy between systems"""
    try:
        data = request.get_json()
        system1 = data.get('system1')
        system2 = data.get('system2')
        synergy_type = data.get('synergy_type', 'complementary')
        
        if not system1 or not system2:
            return jsonify({
                'success': False,
                'error': 'system1 and system2 are required'
            }), 400
        
        result = academic_perspective_system.create_synergy(system1, system2, synergy_type)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating synergy: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@academic_perspective_bp.route('/api/academic/perspective', methods=['GET'])
def get_perspective():
    """Get user's academic perspective"""
    try:
        user_id = request.args.get('user_id', 'default')
        perspective = academic_perspective_system.get_academic_perspective(user_id)
        return jsonify({
            'success': True,
            'perspective': perspective
        }), 200
    except Exception as e:
        logger.error(f"Error getting perspective: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

