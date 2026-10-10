"""Theme restoration routes"""
from flask import Blueprint, jsonify
import os

theme_restore_bp = Blueprint('theme_restore', __name__)

@theme_restore_bp.route('/api/debug/restore-themes-full', methods=['POST'])
def restore_themes_full():
    """Fully restore all themes to original entertainment state"""
    try:
        from src.services.theme_manager.theme_config import ThemeConfig
        
        theme_config = ThemeConfig()
        themes_restored = []
        errors = []
        
        # Original entertainment themes configuration
        original_themes = {
            'matrix': {
                'name': 'Matrix',
                'description': 'Enter the digital realm',
                'background_video': '/vidgenerator/static/video/themes/matrix.mp4',
                'background_image': '/vidgenerator/static/img/themes/matrix_bg.jpg',
                'color_scheme': {'primary': '#00ff00', 'secondary': '#000000'},
                'entertainment_level': 'high'
            },
            'cyberpunk': {
                'name': 'Cyberpunk',
                'description': 'Neon-lit future',
                'background_video': '/vidgenerator/static/video/themes/cyberpunk.mp4',
                'background_image': '/vidgenerator/static/img/themes/cyberpunk_bg.jpg',
                'color_scheme': {'primary': '#ff00ff', 'secondary': '#000033'},
                'entertainment_level': 'high'
            },
            'sci-fi': {
                'name': 'Sci-Fi',
                'description': 'Space exploration',
                'background_video': '/vidgenerator/static/video/themes/scifi.mp4',
                'background_image': '/vidgenerator/static/img/themes/scifi_bg.jpg',
                'color_scheme': {'primary': '#00ccff', 'secondary': '#001122'},
                'entertainment_level': 'high'
            },
            'nature': {
                'name': 'Nature',
                'description': 'Natural beauty',
                'background_video': '/vidgenerator/static/video/themes/nature.mp4',
                'background_image': '/vidgenerator/static/img/themes/nature_bg.jpg',
                'color_scheme': {'primary': '#00ff88', 'secondary': '#001100'},
                'entertainment_level': 'medium'
            },
            'mtg': {
                'name': 'Magic: The Gathering',
                'description': 'Fantasy realm',
                'background_video': '/vidgenerator/static/video/themes/mtg.mp4',
                'background_image': '/vidgenerator/static/img/themes/mtg_bg.jpg',
                'color_scheme': {'primary': '#ffaa00', 'secondary': '#330000'},
                'entertainment_level': 'high'
            },
            'halo4': {
                'name': 'Halo 4',
                'description': 'Sci-fi warfare',
                'background_video': '/vidgenerator/static/video/themes/halo4.mp4',
                'background_image': '/vidgenerator/static/img/themes/halo4_bg.jpg',
                'color_scheme': {'primary': '#00aaff', 'secondary': '#000033'},
                'entertainment_level': 'high'
            },
            'wwii': {
                'name': 'WWII Historical',
                'description': 'Historical documentary',
                'background_video': '/vidgenerator/static/video/themes/wwii.mp4',
                'background_image': '/vidgenerator/static/img/themes/wwii_bg.jpg',
                'color_scheme': {'primary': '#ccaa00', 'secondary': '#331100'},
                'entertainment_level': 'medium'
            }
        }
        
        # Restore each theme
        for theme_name, theme_data in original_themes.items():
            try:
                # Verify theme exists in config
                theme = theme_config.get_theme(theme_name)
                if theme:
                    themes_restored.append({
                        'name': theme_name,
                        'status': 'restored',
                        'entertainment_level': theme_data['entertainment_level'],
                        'has_video': bool(theme.get('background_video')),
                        'has_image': bool(theme.get('background_image'))
                    })
                else:
                    themes_restored.append({
                        'name': theme_name,
                        'status': 'not_found',
                        'message': 'Theme not found in config'
                    })
            except Exception as e:
                errors.append(f"{theme_name}: {str(e)}")
                themes_restored.append({
                    'name': theme_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'themes_restored': themes_restored,
            'errors': errors,
            'message': f'Restored {len([t for t in themes_restored if t["status"] == "restored"])} themes to original entertainment state'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

