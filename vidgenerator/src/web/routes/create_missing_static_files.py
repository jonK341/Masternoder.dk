"""
Create Missing Static Files
Automatically creates missing CSS/JS files as minimal fallbacks
"""
from flask import Blueprint, jsonify
import os
from pathlib import Path

create_missing_static_bp = Blueprint('create_missing_static', __name__)

BASE_STATIC = Path('/var/www/html/vidgenerator/src/web/static')

def create_file_if_missing(filepath, content):
    """Create file if it doesn't exist"""
    try:
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            os.chmod(filepath, 0o644)
            return True
    except Exception as e:
        print(f"Error creating {filepath}: {e}")
    return False

@create_missing_static_bp.route('/api/fix/create-all-missing-files', methods=['POST'])
@create_missing_static_bp.route('/vidgenerator/api/fix/create-all-missing-files', methods=['POST'])
def create_all_missing_files():
    """Create all missing CSS/JS files"""
    created = []
    
    # CSS files
    css_files = {
        'generator-modern.css': '/* Generator Modern */\n',
        'monitor-fixes.css': '/* Monitor Fixes */\n',
        'monitor-tabs.css': '/* Monitor Tabs */\n',
        'monitor-enhanced.css': '/* Monitor Enhanced */\n',
        'clip-duration-control.css': '/* Clip Duration Control */\n',
        'generator-ui-modern.css': '/* Generator UI Modern */\n',
        'generator-tools-tabs.css': '/* Generator Tools Tabs */\n',
        'generator-two-frame.css': '/* Generator Two Frame */\n',
        'generation-status.css': '/* Generation Status */\n',
        'error-handler.css': '/* Error Handler */\n',
        'phase-frames.css': '/* Phase Frames */\n',
        'design-system.css': '/* Design System */\n'
    }
    
    for filename, content in css_files.items():
        filepath = BASE_STATIC / 'css' / filename
        if create_file_if_missing(filepath, content):
            created.append(f'css/{filename}')
    
    # JS files in generator/
    js_generator_files = {
        'generator-button-fixed.js': '// Generator Button Fixed\n',
        'generator-button-activator.js': '// Generator Button Activator\n',
        'generator-button-simple-fix.js': '// Generator Button Simple Fix\n',
        'generator-button-debug.js': '// Generator Button Debug\n',
        'generator-button-reload.js': '// Generator Button Reload\n',
        'generator-button-ai-integrated.js': '// Generator Button AI Integrated\n',
        'generator-button-simple-ai.js': '// Generator Button Simple AI\n',
        'generator-button-final-fix.js': '// Generator Button Final Fix\n',
        'clip-duration-control.js': '// Clip Duration Control\n',
        'theme-cache.js': '// Theme Cache\n',
        'theme-selector.js': '// Theme Selector\n',
        'clip-count-control.js': '// Clip Count Control\n',
        'monitor-slideshow.js': '// Monitor Slideshow\n',
        'clip-storage.js': '// Clip Storage\n',
        'generation-status.js': '// Generation Status\n',
        'error-handler.js': '// Error Handler\n',
        'json-response-handler.js': '// JSON Response Handler\n',
        'retry-manager.js': '// Retry Manager\n',
        'input-validator.js': '// Input Validator\n',
        'progress-persistence.js': '// Progress Persistence\n',
        'two-phase-simplified.js': '// Two Phase Simplified\n',
        'xp-integration.js': '// XP Integration\n'
    }
    
    for filename, content in js_generator_files.items():
        filepath = BASE_STATIC / 'js' / 'generator' / filename
        if create_file_if_missing(filepath, content):
            created.append(f'js/generator/{filename}')
    
    # JS files in root
    js_root_files = {
        'service-worker-register.js': '// Service Worker Register\n',
        'ai-engine-simple.js': '// AI Engine Simple\n',
        'service-worker-ai-integration.js': '// Service Worker AI Integration\n',
        'stats-counter.js': '// Stats Counter\n',
        'utils.js': '// Utils\n',
        'main.js': '// Main\n',
        'additional_themes.js': '// Additional Themes\n',
        'theme_model.js': '// Theme Model\n',
        'hybrid-storage-manager.js': '// Hybrid Storage Manager\n',
        'monitor-enhanced-logic.js': '// Monitor Enhanced Logic\n',
        'stats-frame-extractor.js': '// Stats Frame Extractor\n',
        'monitor-caption-updater.js': '// Monitor Caption Updater\n',
        'generator-frame-extractor.js': '// Generator Frame Extractor\n'
    }
    
    for filename, content in js_root_files.items():
        filepath = BASE_STATIC / 'js' / filename
        if create_file_if_missing(filepath, content):
            created.append(f'js/{filename}')
    
    # Image files
    img_files = {
        'masternoder2_sword.gif': b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00;'
    }
    
    for filename, content in img_files.items():
        filepath = BASE_STATIC / 'img' / filename
        try:
            if not filepath.exists():
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(content)
                os.chmod(filepath, 0o644)
                created.append(f'img/{filename}')
        except Exception as e:
            print(f"Error creating {filepath}: {e}")
    
    return jsonify({
        'success': True,
        'created': created,
        'count': len(created),
        'message': f'Created {len(created)} missing files'
    })

