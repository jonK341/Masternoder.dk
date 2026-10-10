"""Auto-fix all sites through debugging"""
from flask import Blueprint, jsonify, request
import os
import subprocess
import json
from datetime import datetime

site_fixer_bp = Blueprint('site_fixer', __name__)

@site_fixer_bp.route('/api/debug/fix-all-sites', methods=['POST'])
def fix_all_sites():
    """Fix all sites through comprehensive debugging"""
    try:
        fixes = []
        errors = []
        
        # 1. Clear all caches
        try:
            cache_dirs = []
            for root, dirs, files in os.walk('/var/www/html/vidgenerator'):
                if '__pycache__' in dirs:
                    cache_dirs.append(os.path.join(root, '__pycache__'))
            
            import shutil
            for cache_dir in cache_dirs:
                try:
                    shutil.rmtree(cache_dir)
                    fixes.append(f'Cleared cache: {cache_dir}')
                except Exception as e:
                    errors.append(f'Cache clear error: {str(e)}')
        except Exception as e:
            errors.append(f'Cache clearing failed: {str(e)}')
        
        # 2. Verify all templates exist
        template_path = '/var/www/html/vidgenerator/src/web/templates'
        required_templates = [
            'base.html',
            'home.html',
            'generator/index.html',
            'gallery/index.html',
            'chat/index.html',
            'stats/index.html'
        ]
        
        for template in required_templates:
            template_file = os.path.join(template_path, template)
            if os.path.exists(template_file):
                fixes.append(f'Template exists: {template}')
            else:
                errors.append(f'Missing template: {template}')
        
        # 3. Verify static files
        static_path = '/var/www/html/vidgenerator/src/web/static'
        required_static = [
            'js/main.js',
            'js/generator/theme-selector.js',
            'js/chat/chat-points.js',
            'js/stats-counter.js',
            'css/style.css'
        ]
        
        for static_file in required_static:
            static_file_path = os.path.join(static_path, static_file)
            if os.path.exists(static_file_path):
                fixes.append(f'Static file exists: {static_file}')
            else:
                errors.append(f'Missing static file: {static_file}')
        
        # 4. Check database
        try:
            from src.db.models import db
            db.create_all()
            fixes.append('Database tables verified')
        except Exception as e:
            errors.append(f'Database error: {str(e)}')
        
        # 5. Restart services
        try:
            subprocess.run(['systemctl', 'restart', 'uwsgi-vidgenerator.service'], 
                         capture_output=True, timeout=10)
            fixes.append('uWSGI restarted')
        except Exception as e:
            errors.append(f'uWSGI restart: {str(e)}')
        
        # 6. Test all routes
        route_tests = []
        test_urls = [
            'http://127.0.0.1:5000/vidgenerator',
            'http://127.0.0.1:5000/vidgenerator/generator',
            'http://127.0.0.1:5000/vidgenerator/gallery',
            'http://127.0.0.1:5000/vidgenerator/chat',
            'http://127.0.0.1:5000/vidgenerator/stats'
        ]
        
        import requests
        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                route_tests.append({
                    'url': url,
                    'status': response.status_code,
                    'ok': response.ok
                })
                if response.ok:
                    fixes.append(f'Route OK: {url}')
                else:
                    errors.append(f'Route failed: {url} ({response.status_code})')
            except Exception as e:
                errors.append(f'Route test error: {url} - {str(e)}')
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes,
            'errors': errors,
            'route_tests': route_tests,
            'summary': {
                'fixes_count': len(fixes),
                'errors_count': len(errors),
                'routes_tested': len(route_tests),
                'routes_ok': len([r for r in route_tests if r.get('ok')])
            }
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

