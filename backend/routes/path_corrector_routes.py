"""
Path Corrector Routes
API endpoints for path correction
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List

path_corrector_bp = Blueprint('path_corrector', __name__)


@path_corrector_bp.route('/api/paths/correct', methods=['POST'])
def correct_path():
    """Correct a single path"""
    try:
        data = request.get_json() or {}
        path = data.get('path', '')
        context = data.get('context', {})
        
        if not path:
            return jsonify({
                'success': False,
                'error': 'path is required'
            }), 400
        
        from backend.services.path_corrector import path_corrector
        
        corrected_path, correction_info = path_corrector.correct_path(path, context)
        
        return jsonify({
            'success': True,
            'original': path,
            'corrected': corrected_path,
            'correction_info': correction_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@path_corrector_bp.route('/api/paths/correct-multiple', methods=['POST'])
def correct_paths():
    """Correct multiple paths"""
    try:
        data = request.get_json() or {}
        paths = data.get('paths', [])
        context = data.get('context', {})
        
        if not paths or not isinstance(paths, list):
            return jsonify({
                'success': False,
                'error': 'paths array is required'
            }), 400
        
        from backend.services.path_corrector import path_corrector
        
        corrected_paths = path_corrector.correct_paths_crossways(paths, context)
        
        return jsonify({
            'success': True,
            'corrections': [
                {
                    'original': orig,
                    'corrected': corr,
                    'info': info
                }
                for orig, corr, info in corrected_paths
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@path_corrector_bp.route('/api/paths/learn', methods=['POST'])
def learn_correction():
    """Learn a path correction"""
    try:
        data = request.get_json() or {}
        original_path = data.get('original_path', '')
        corrected_path = data.get('corrected_path', '')
        context = data.get('context', {})
        success = data.get('success', True)
        
        if not original_path or not corrected_path:
            return jsonify({
                'success': False,
                'error': 'original_path and corrected_path are required'
            }), 400
        
        from backend.services.path_corrector import path_corrector
        
        path_corrector.learn_correction(
            original_path=original_path,
            corrected_path=corrected_path,
            context=context,
            success=success
        )
        
        return jsonify({
            'success': True,
            'message': 'Correction learned'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@path_corrector_bp.route('/api/paths/stats', methods=['GET'])
def get_path_stats():
    """Get path correction statistics"""
    try:
        from backend.services.path_corrector import path_corrector
        
        stats = path_corrector.get_correction_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
