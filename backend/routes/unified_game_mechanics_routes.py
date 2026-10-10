"""
Routes for Unified Game Mechanics Constructor
"""
from flask import Blueprint, jsonify, request
from backend.services.unified_game_mechanics_constructor import unified_game_mechanics

unified_mechanics_bp = Blueprint('unified_game_mechanics', __name__, url_prefix='/api/game-mechanics')


@unified_mechanics_bp.route('/subjects', methods=['GET'])
def get_all_subjects():
    """Get all subjects organized by academic classes"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = unified_game_mechanics.get_all_subjects(user_id=user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@unified_mechanics_bp.route('/subject/start', methods=['POST'])
def start_subject():
    """Start learning a subject"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        subject_id = data.get('subject_id')
        
        if not subject_id:
            return jsonify({
                'success': False,
                'error': 'subject_id required'
            }), 400
        
        result = unified_game_mechanics.start_subject(user_id, subject_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@unified_mechanics_bp.route('/function/use', methods=['POST'])
def use_function():
    """Use a function from a subject"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        subject_id = data.get('subject_id')
        function_name = data.get('function_name')
        function_type = data.get('function_type', 'practical')
        
        if not subject_id or not function_name:
            return jsonify({
                'success': False,
                'error': 'subject_id and function_name required'
            }), 400
        
        result = unified_game_mechanics.use_function(user_id, subject_id, function_name, function_type)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@unified_mechanics_bp.route('/subject/complete', methods=['POST'])
def complete_subject():
    """Complete a subject"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        subject_id = data.get('subject_id')
        
        if not subject_id:
            return jsonify({
                'success': False,
                'error': 'subject_id required'
            }), 400
        
        result = unified_game_mechanics.complete_subject(user_id, subject_id)
        
        # Save to file
        unified_game_mechanics.save_to_file(user_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@unified_mechanics_bp.route('/progress', methods=['GET'])
def get_user_progress():
    """Get user's progress across all subjects"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Load from file if exists
        unified_game_mechanics.load_from_file(user_id)
        
        result = unified_game_mechanics.get_user_progress(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

