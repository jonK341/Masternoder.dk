"""
Theme Debugger Engine
Comprehensive debugging and generation system for all 12 themes
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ThemeDebuggerEngine:
    """Debugger engine for all themes with comprehensive logic"""
    
    # All 12 themes
    ALL_THEMES = [
        'matrix',
        'cyberpunk',
        'sci-fi',
        'nature',
        'mtg',
        'halo4',
        'wwii',
        'fantasy',
        'horror',
        'comedy',
        'romance',
        'action'
    ]
    
    def __init__(self):
        self.theme_configs = {}
        self.debug_log = []
        self.load_all_themes()
    
    def load_all_themes(self):
        """Load all theme configurations"""
        try:
            from .theme_config import ThemeConfig
            self.theme_config = ThemeConfig()
            
            for theme_name in self.ALL_THEMES:
                try:
                    theme = self.theme_config.get_theme(theme_name)
                    if theme:
                        self.theme_configs[theme_name] = theme
                        self.log(f"Loaded theme: {theme_name}", 'info')
                    else:
                        self.log(f"Theme not found: {theme_name}", 'warning')
                        # Create default config
                        self.theme_configs[theme_name] = self._create_default_theme(theme_name)
                except Exception as e:
                    self.log(f"Error loading theme {theme_name}: {e}", 'error')
                    self.theme_configs[theme_name] = self._create_default_theme(theme_name)
        except Exception as e:
            logger.error(f"Failed to load theme config: {e}")
    
    def _create_default_theme(self, theme_name: str) -> Dict:
        """Create default theme configuration"""
        defaults = {
            'matrix': {
                'name': 'Matrix',
                'description': 'Digital realm with green code rain',
                'background_video': '/vidgenerator/static/video/themes/matrix.mp4',
                'background_image': '/vidgenerator/static/img/themes/matrix_bg.jpg',
                'color_scheme': {'primary': '#00ff00', 'secondary': '#000000'},
                'entertainment_level': 'high',
                'mood': 'cyberpunk',
                'era': 'future'
            },
            'cyberpunk': {
                'name': 'Cyberpunk',
                'description': 'Neon-lit future city',
                'background_video': '/vidgenerator/static/video/themes/cyberpunk.mp4',
                'background_image': '/vidgenerator/static/img/themes/cyberpunk_bg.jpg',
                'color_scheme': {'primary': '#ff00ff', 'secondary': '#000033'},
                'entertainment_level': 'high',
                'mood': 'futuristic',
                'era': 'future'
            },
            'sci-fi': {
                'name': 'Sci-Fi',
                'description': 'Space exploration and technology',
                'background_video': '/vidgenerator/static/video/themes/scifi.mp4',
                'background_image': '/vidgenerator/static/img/themes/scifi_bg.jpg',
                'color_scheme': {'primary': '#00ccff', 'secondary': '#001122'},
                'entertainment_level': 'high',
                'mood': 'exploratory',
                'era': 'future'
            },
            'nature': {
                'name': 'Nature',
                'description': 'Natural beauty and landscapes',
                'background_video': '/vidgenerator/static/video/themes/nature.mp4',
                'background_image': '/vidgenerator/static/img/themes/nature_bg.jpg',
                'color_scheme': {'primary': '#00ff88', 'secondary': '#001100'},
                'entertainment_level': 'medium',
                'mood': 'peaceful',
                'era': 'timeless'
            },
            'mtg': {
                'name': 'Magic: The Gathering',
                'description': 'Fantasy realm with magic',
                'background_video': '/vidgenerator/static/video/themes/mtg.mp4',
                'background_image': '/vidgenerator/static/img/themes/mtg_bg.jpg',
                'color_scheme': {'primary': '#ffaa00', 'secondary': '#330000'},
                'entertainment_level': 'high',
                'mood': 'magical',
                'era': 'fantasy'
            },
            'halo4': {
                'name': 'Halo 4',
                'description': 'Sci-fi warfare and combat',
                'background_video': '/vidgenerator/static/video/themes/halo4.mp4',
                'background_image': '/vidgenerator/static/img/themes/halo4_bg.jpg',
                'color_scheme': {'primary': '#00aaff', 'secondary': '#000033'},
                'entertainment_level': 'high',
                'mood': 'intense',
                'era': 'future'
            },
            'wwii': {
                'name': 'WWII Historical',
                'description': 'Historical World War II documentary',
                'background_video': '/vidgenerator/static/video/themes/wwii.mp4',
                'background_image': '/vidgenerator/static/img/themes/wwii_bg.jpg',
                'color_scheme': {'primary': '#ccaa00', 'secondary': '#331100'},
                'entertainment_level': 'medium',
                'mood': 'historical',
                'era': '1940s',
                'historical_accuracy': True,
                'sensitive_content': True
            },
            'fantasy': {
                'name': 'Fantasy',
                'description': 'Medieval fantasy world',
                'background_video': '/vidgenerator/static/video/themes/fantasy.mp4',
                'background_image': '/vidgenerator/static/img/themes/fantasy_bg.jpg',
                'color_scheme': {'primary': '#aa00ff', 'secondary': '#220033'},
                'entertainment_level': 'high',
                'mood': 'adventurous',
                'era': 'medieval'
            },
            'horror': {
                'name': 'Horror',
                'description': 'Dark and scary atmosphere',
                'background_video': '/vidgenerator/static/video/themes/horror.mp4',
                'background_image': '/vidgenerator/static/img/themes/horror_bg.jpg',
                'color_scheme': {'primary': '#ff0000', 'secondary': '#000000'},
                'entertainment_level': 'high',
                'mood': 'frightening',
                'era': 'timeless',
                'content_warning': True
            },
            'comedy': {
                'name': 'Comedy',
                'description': 'Light-hearted and funny',
                'background_video': '/vidgenerator/static/video/themes/comedy.mp4',
                'background_image': '/vidgenerator/static/img/themes/comedy_bg.jpg',
                'color_scheme': {'primary': '#ffff00', 'secondary': '#ffaa00'},
                'entertainment_level': 'high',
                'mood': 'humorous',
                'era': 'modern'
            },
            'romance': {
                'name': 'Romance',
                'description': 'Romantic and emotional',
                'background_video': '/vidgenerator/static/video/themes/romance.mp4',
                'background_image': '/vidgenerator/static/img/themes/romance_bg.jpg',
                'color_scheme': {'primary': '#ff88cc', 'secondary': '#ffccff'},
                'entertainment_level': 'medium',
                'mood': 'romantic',
                'era': 'modern'
            },
            'action': {
                'name': 'Action',
                'description': 'High-energy action sequences',
                'background_video': '/vidgenerator/static/video/themes/action.mp4',
                'background_image': '/vidgenerator/static/img/themes/action_bg.jpg',
                'color_scheme': {'primary': '#ff3300', 'secondary': '#330000'},
                'entertainment_level': 'high',
                'mood': 'intense',
                'era': 'modern'
            }
        }
        
        return defaults.get(theme_name, {
            'name': theme_name.title(),
            'description': f'{theme_name} theme',
            'background_video': f'/vidgenerator/static/video/themes/{theme_name}.mp4',
            'background_image': f'/vidgenerator/static/img/themes/{theme_name}_bg.jpg',
            'color_scheme': {'primary': '#ffffff', 'secondary': '#000000'},
            'entertainment_level': 'medium',
            'mood': 'neutral',
            'era': 'modern'
        })
    
    def log(self, message: str, level: str = 'info'):
        """Log debug message"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.debug_log.append(entry)
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
    
    def debug_theme(self, theme_name: str) -> Dict[str, Any]:
        """Debug a specific theme"""
        self.log(f"Debugging theme: {theme_name}", 'info')
        
        if theme_name not in self.ALL_THEMES:
            return {
                'success': False,
                'error': f'Unknown theme: {theme_name}',
                'available_themes': self.ALL_THEMES
            }
        
        theme_config = self.theme_configs.get(theme_name, {})
        
        debug_result = {
            'theme_name': theme_name,
            'config_exists': bool(theme_config),
            'config': theme_config,
            'files': {},
            'validation': {},
            'recommendations': []
        }
        
        # Check files
        if theme_config:
            # Check video file
            video_path = theme_config.get('background_video', '')
            if video_path:
                full_path = self._resolve_path(video_path)
                debug_result['files']['video'] = {
                    'path': video_path,
                    'full_path': full_path,
                    'exists': os.path.exists(full_path),
                    'size': os.path.getsize(full_path) if os.path.exists(full_path) else 0
                }
            
            # Check image file
            image_path = theme_config.get('background_image', '')
            if image_path:
                full_path = self._resolve_path(image_path)
                debug_result['files']['image'] = {
                    'path': image_path,
                    'full_path': full_path,
                    'exists': os.path.exists(full_path),
                    'size': os.path.getsize(full_path) if os.path.exists(full_path) else 0
                }
        
        # Validate theme
        debug_result['validation'] = self._validate_theme(theme_name, theme_config)
        
        # Generate recommendations
        debug_result['recommendations'] = self._generate_recommendations(theme_name, theme_config, debug_result)
        
        debug_result['success'] = True
        return debug_result
    
    def _resolve_path(self, path: str) -> str:
        """Resolve theme file path"""
        if path.startswith('/'):
            return path
        elif path.startswith('/vidgenerator'):
            return path
        else:
            # Assume relative to static folder
            return f'/var/www/html/vidgenerator/src/web/static{path}'
    
    def _validate_theme(self, theme_name: str, theme_config: Dict) -> Dict:
        """Validate theme configuration"""
        validation = {
            'valid': True,
            'issues': [],
            'warnings': []
        }
        
        # Required fields
        required_fields = ['name', 'description', 'color_scheme']
        for field in required_fields:
            if field not in theme_config:
                validation['valid'] = False
                validation['issues'].append(f'Missing required field: {field}')
        
        # Check color scheme
        if 'color_scheme' in theme_config:
            color_scheme = theme_config['color_scheme']
            if not isinstance(color_scheme, dict):
                validation['valid'] = False
                validation['issues'].append('color_scheme must be a dictionary')
            elif 'primary' not in color_scheme:
                validation['warnings'].append('color_scheme missing primary color')
        
        # Check files exist
        if 'background_video' in theme_config:
            video_path = self._resolve_path(theme_config['background_video'])
            if not os.path.exists(video_path):
                validation['warnings'].append(f'Background video not found: {video_path}')
        
        if 'background_image' in theme_config:
            image_path = self._resolve_path(theme_config['background_image'])
            if not os.path.exists(image_path):
                validation['warnings'].append(f'Background image not found: {image_path}')
        
        # Special validation for WWII theme
        if theme_name == 'wwii':
            if not theme_config.get('historical_accuracy'):
                validation['warnings'].append('WWII theme should have historical_accuracy flag')
            if not theme_config.get('sensitive_content'):
                validation['warnings'].append('WWII theme should have sensitive_content flag')
        
        return validation
    
    def _generate_recommendations(self, theme_name: str, theme_config: Dict, debug_result: Dict) -> List[str]:
        """Generate recommendations for theme improvement"""
        recommendations = []
        
        # File recommendations
        if not debug_result['files'].get('video', {}).get('exists'):
            recommendations.append(f"Add background video for {theme_name} theme")
        
        if not debug_result['files'].get('image', {}).get('exists'):
            recommendations.append(f"Add background image for {theme_name} theme")
        
        # Configuration recommendations
        if 'entertainment_level' not in theme_config:
            recommendations.append(f"Add entertainment_level to {theme_name} theme")
        
        if 'mood' not in theme_config:
            recommendations.append(f"Add mood to {theme_name} theme")
        
        if 'era' not in theme_config:
            recommendations.append(f"Add era to {theme_name} theme")
        
        # WWII specific recommendations
        if theme_name == 'wwii':
            if not theme_config.get('historical_accuracy'):
                recommendations.append("Add historical_accuracy flag for WWII theme")
            if not theme_config.get('sensitive_content'):
                recommendations.append("Add sensitive_content warning for WWII theme")
            recommendations.append("Ensure WWII theme respects historical context")
            recommendations.append("Add content warnings for sensitive material")
        
        return recommendations
    
    def debug_all_themes(self) -> Dict[str, Any]:
        """Debug all themes"""
        self.log("Starting comprehensive theme debugging", 'info')
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'themes': {},
            'summary': {
                'total': len(self.ALL_THEMES),
                'valid': 0,
                'invalid': 0,
                'warnings': 0
            }
        }
        
        for theme_name in self.ALL_THEMES:
            debug_result = self.debug_theme(theme_name)
            results['themes'][theme_name] = debug_result
            
            if debug_result.get('success'):
                validation = debug_result.get('validation', {})
                if validation.get('valid'):
                    results['summary']['valid'] += 1
                else:
                    results['summary']['invalid'] += 1
                
                if validation.get('warnings'):
                    results['summary']['warnings'] += len(validation['warnings'])
        
        results['debug_log'] = self.debug_log[-50:]  # Last 50 entries
        
        return results
    
    def generate_theme_assets(self, theme_name: str) -> Dict[str, Any]:
        """Generate theme assets (placeholder for now)"""
        self.log(f"Generating assets for theme: {theme_name}", 'info')
        
        theme_config = self.theme_configs.get(theme_name, {})
        
        # Create directory structure
        video_dir = Path('/var/www/html/vidgenerator/src/web/static/video/themes')
        image_dir = Path('/var/www/html/vidgenerator/src/web/static/img/themes')
        
        video_dir.mkdir(parents=True, exist_ok=True)
        image_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'theme_name': theme_name,
            'assets_created': [],
            'errors': []
        }
        
        # Generate placeholder video (would use actual generation in production)
        video_path = video_dir / f"{theme_name}.mp4"
        if not video_path.exists():
            try:
                # Create placeholder (in production, use actual video generation)
                video_path.touch()
                result['assets_created'].append(f'Video placeholder: {video_path}')
            except Exception as e:
                result['errors'].append(f'Failed to create video: {e}')
        
        # Generate placeholder image
        image_path = image_dir / f"{theme_name}_bg.jpg"
        if not image_path.exists():
            try:
                image_path.touch()
                result['assets_created'].append(f'Image placeholder: {image_path}')
            except Exception as e:
                result['errors'].append(f'Failed to create image: {e}')
        
        return result
    
    def generate_all_theme_assets(self) -> Dict[str, Any]:
        """Generate assets for all themes"""
        self.log("Generating assets for all themes", 'info')
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'themes': {}
        }
        
        for theme_name in self.ALL_THEMES:
            results['themes'][theme_name] = self.generate_theme_assets(theme_name)
        
        return results

