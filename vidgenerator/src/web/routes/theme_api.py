"""
Theme API Routes
Provides theme detection, configuration, and selection endpoints
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

theme_api_bp = Blueprint('theme_api', __name__)

# Import theme systems
try:
    from src.services.theme_manager.theme_selector import IntelligentThemeSelector
    from src.services.theme_manager.theme_config import ThemeConfig
except ImportError as e:
    print(f"[ThemeAPI] Warning: Theme systems not available: {e}")
    IntelligentThemeSelector = None
    ThemeConfig = None


@theme_api_bp.route('/api/theme/detect', methods=['POST'])
@theme_api_bp.route('/vidgenerator/api/theme/detect', methods=['POST'])
def detect_theme():
    """Auto-detect theme from prompt"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        title = data.get('title')
        
        if not IntelligentThemeSelector:
            return jsonify({
                'theme': 'matrix',
                'confidence': 0.5,
                'config': {},
                'error': 'Theme selector not available'
            }), 200
        
        selector = IntelligentThemeSelector()
        result = selector.get_intelligent_theme(prompt, title)
        
        return jsonify({
            'theme': result['theme'],
            'confidence': result['confidence'],
            'config': result['config'],
            'auto_detected': result['auto_detected']
        }), 200
        
    except Exception as e:
        return jsonify({
            'theme': 'matrix',
            'confidence': 0.5,
            'error': str(e)
        }), 500


@theme_api_bp.route('/api/theme/config/<theme_name>', methods=['GET'])
@theme_api_bp.route('/vidgenerator/api/theme/config/<theme_name>', methods=['GET'])
def get_theme_config(theme_name: str):
    """Get theme configuration"""
    try:
        prompt = request.args.get('prompt')
        title = request.args.get('title')
        
        if not ThemeConfig:
            return jsonify({'error': 'Theme config not available'}), 500
        
        config = ThemeConfig.get_theme(theme_name, prompt, title)
        
        return jsonify(config), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_api_bp.route('/api/theme/list', methods=['GET'])
@theme_api_bp.route('/vidgenerator/api/theme/list', methods=['GET'])
def list_themes():
    """List all available themes"""
    try:
        if not IntelligentThemeSelector:
            return jsonify({
                'themes': [],
                'error': 'Theme selector not available'
            }), 200
        
        selector = IntelligentThemeSelector()
        themes = selector.list_available_themes()
        
        return jsonify({
            'themes': themes,
            'count': len(themes)
        }), 200
        
    except Exception as e:
        return jsonify({
            'themes': [],
            'error': str(e)
        }), 500

