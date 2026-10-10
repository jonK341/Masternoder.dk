"""API routes for theme debugger engine"""
from flask import Blueprint, jsonify, request
from src.services.theme_manager.theme_debugger_engine import ThemeDebuggerEngine

theme_debugger_bp = Blueprint('theme_debugger', __name__)

# Initialize debugger engine
debugger_engine = ThemeDebuggerEngine()

@theme_debugger_bp.route('/api/theme/debug/<theme_name>', methods=['GET'])
def debug_theme(theme_name):
    """Debug a specific theme"""
    try:
        result = debugger_engine.debug_theme(theme_name)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@theme_debugger_bp.route('/api/theme/debug-all', methods=['GET'])
def debug_all_themes():
    """Debug all themes"""
    try:
        result = debugger_engine.debug_all_themes()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@theme_debugger_bp.route('/api/theme/generate-assets/<theme_name>', methods=['POST'])
def generate_theme_assets(theme_name):
    """Generate assets for a specific theme"""
    try:
        result = debugger_engine.generate_theme_assets(theme_name)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@theme_debugger_bp.route('/api/theme/generate-all-assets', methods=['POST'])
def generate_all_theme_assets():
    """Generate assets for all themes"""
    try:
        result = debugger_engine.generate_all_theme_assets()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@theme_debugger_bp.route('/api/theme/list', methods=['GET'])
def list_themes():
    """List all available themes"""
    try:
        return jsonify({
            'success': True,
            'themes': debugger_engine.ALL_THEMES,
            'count': len(debugger_engine.ALL_THEMES)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

