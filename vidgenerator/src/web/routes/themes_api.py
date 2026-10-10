"""
Themes API - Complete hardcoded themes
"""
from flask import Blueprint, jsonify, request
from src.services.themes.theme_definitions import theme_definitions, ThemeType

themes_api_bp = Blueprint('themes_api', __name__)

@themes_api_bp.route('/api/themes/all', methods=['GET'])
@themes_api_bp.route('/vidgenerator/api/themes/all', methods=['GET'])
def get_all_themes():
    """Get all 12 hardcoded themes"""
    try:
        themes = theme_definitions.get_theme_list()
        return jsonify({
            'success': True,
            'themes': themes,
            'count': len(themes)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@themes_api_bp.route('/api/themes/<theme_key>', methods=['GET'])
@themes_api_bp.route('/vidgenerator/api/themes/<theme_key>', methods=['GET'])
def get_theme(theme_key):
    """Get specific theme by key"""
    try:
        theme = theme_definitions.get_theme(theme_key)
        if not theme:
            return jsonify({
                'success': False,
                'error': f'Themes {theme_key} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'theme': {**theme, 'key': theme_key}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@themes_api_bp.route('/api/themes/<theme_key>/recommended-defense', methods=['GET'])
@themes_api_bp.route('/vidgenerator/api/themes/<theme_key>/recommended-defense', methods=['GET'])
def get_recommended_defense(theme_key):
    """Get recommended defense mechanism for theme"""
    try:
        mechanism = theme_definitions.get_recommended_defense_mechanism(theme_key)
        return jsonify({
            'success': True,
            'theme_key': theme_key,
            'recommended_defense_mechanism': mechanism
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@themes_api_bp.route('/api/themes/<theme_key>/enemy-match', methods=['GET'])
@themes_api_bp.route('/vidgenerator/api/themes/<theme_key>/enemy-match', methods=['GET'])
def get_enemy_match(theme_key):
    """Get matching enemy type for theme"""
    try:
        enemy_type = theme_definitions.get_theme_enemy_match(theme_key)
        return jsonify({
            'success': True,
            'theme_key': theme_key,
            'enemy_type': enemy_type
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@themes_api_bp.route('/api/themes/<theme_key>/prompts', methods=['GET'])
@themes_api_bp.route('/vidgenerator/api/themes/<theme_key>/prompts', methods=['GET'])
def get_theme_prompts(theme_key):
    """Get generation prompts for theme"""
    try:
        theme = theme_definitions.get_theme(theme_key)
        if not theme:
            return jsonify({
                'success': False,
                'error': f'Theme {theme_key} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'theme_key': theme_key,
            'generation_prompts': theme.get('generation_prompts', [])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

