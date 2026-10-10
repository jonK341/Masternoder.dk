"""
Advanced API Status and Diagnostic Page
Shows all registered routes, API endpoints, and system status
"""
from flask import Blueprint, render_template, jsonify, request
import os
import subprocess
from pathlib import Path
from datetime import datetime

api_status_bp = Blueprint('api_status', __name__)

@api_status_bp.route('/api/status', methods=['GET'])
@api_status_bp.route('/vidgenerator/api/status', methods=['GET'])
@api_status_bp.route('/api', methods=['GET'])
@api_status_bp.route('/vidgenerator/api', methods=['GET'])
def api_status_page():
    """Advanced API status page"""
    try:
        # Get all registered routes
        from flask import current_app
        routes = []
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': rule.rule,
                    'arguments': list(rule.arguments)
                })
        
        # System status
        system_status = {
            'timestamp': datetime.now().isoformat(),
            'uwsgi_running': False,
            'apache_running': False,
            'python_processes': [],
            'disk_space': {},
            'memory': {}
        }
        
        try:
            # Check processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'uwsgi' in line.lower() and 'grep' not in line.lower():
                        system_status['uwsgi_running'] = True
                    if 'apache' in line.lower() or 'httpd' in line.lower():
                        if 'grep' not in line.lower():
                            system_status['apache_running'] = True
                    if 'python' in line.lower() and 'flask' in line.lower():
                        parts = line.split()
                        if len(parts) > 1:
                            system_status['python_processes'].append({
                                'pid': parts[1],
                                'command': ' '.join(parts[10:])[:100]
                            })
        except Exception as e:
            system_status['error'] = str(e)
        
        # Check disk space
        try:
            result = subprocess.run(['df', '-h', '/var/www/html/vidgenerator'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        system_status['disk_space'] = {
                            'total': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'percent': parts[4]
                        }
        except Exception:
            pass
        
        # File system check
        base_path = Path('/var/www/html/vidgenerator')
        file_checks = {
            'app.py': (base_path / 'src/app.py').exists(),
            'routes/__init__.py': (base_path / 'src/web/routes/__init__.py').exists(),
            'generator.py': (base_path / 'src/web/routes/generator.py').exists(),
            'generator_debugger.py': (base_path / 'src/web/routes/generator_debugger.py').exists(),
            'templates/generator/index.html': (base_path / 'src/web/templates/generator/index.html').exists(),
        }
        
        # API endpoints status
        api_endpoints = {
            '/api/status': 'Available',
            '/api/fix/create-all-missing-files': 'Check routes',
            '/api/generator/fix': 'Check routes',
            '/api/documentary/generate': 'Check routes',
            '/api/generator/check-processes': 'Check routes',
        }
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'system': system_status,
            'routes': routes,
            'file_checks': file_checks,
            'api_endpoints': api_endpoints,
            'message': 'API Status Page - All registered routes and system info'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'message': 'Error generating API status'
        }), 500

@api_status_bp.route('/api/status/html', methods=['GET'])
@api_status_bp.route('/vidgenerator/api/status/html', methods=['GET'])
def api_status_html():
    """HTML version of API status page"""
    try:
        from flask import current_app
        routes = []
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': rule.rule
                })
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Status - MasterNoder</title>
            <style>
                body {{ font-family: monospace; background: #0a0a0a; color: #00ff00; padding: 20px; }}
                h1 {{ color: #00ffff; }}
                .route {{ margin: 10px 0; padding: 10px; background: rgba(0,255,0,0.1); border-left: 3px solid #00ff00; }}
                .method {{ color: #ffff00; }}
                .path {{ color: #00ffff; }}
            </style>
        </head>
        <body>
            <h1>🔍 API Status & Routes</h1>
            <p>Total Routes: {len(routes)}</p>
            <h2>All Registered Routes:</h2>
            {'<br>'.join([f'<div class="route"><span class="method">{", ".join(r["methods"])}</span> <span class="path">{r["path"]}</span> <small>({r["endpoint"]})</small></div>' for r in routes[:100]])}
            <h2>Quick Actions:</h2>
            <ul>
                <li><a href="/api/status" style="color: #00ffff;">JSON API Status (GET)</a></li>
                <li><a href="/api/status/html" style="color: #00ffff;">HTML API Status (GET)</a></li>
                <li>
                    <form action="/api/fix/create-all-missing-files" method="POST" style="display: inline;">
                        <button type="submit" style="background: #00ff00; color: #000; border: none; padding: 5px 10px; cursor: pointer;">Create Missing Files (POST)</button>
                    </form>
                    <a href="/api/fix/create-all-missing-files" style="color: #00ffff; margin-left: 10px;">(or GET)</a>
                </li>
                <li><a href="/api/generator/check-processes" style="color: #00ffff;">Check Processes (GET)</a></li>
                <li><a href="/api/generator/check-uwsgi" style="color: #00ffff;">Check uWSGI (GET)</a></li>
                <li>
                    <form action="/api/generator/restart-uwsgi" method="POST" style="display: inline;">
                        <button type="submit" style="background: #ff0000; color: #fff; border: none; padding: 5px 10px; cursor: pointer;">Restart uWSGI (POST)</button>
                    </form>
                </li>
                <li><a href="/api/debugger" style="color: #00ffff;">API Debugger (GET)</a></li>
                <li><a href="/vidgenerator/debugger" style="color: #00ffff;">Generator Debugger Page</a></li>
            </ul>
        </body>
        </html>
        """
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", 500

@api_status_bp.route('/api/fix/create-all-missing-files', methods=['POST', 'GET'])
@api_status_bp.route('/vidgenerator/api/fix/create-all-missing-files', methods=['POST', 'GET'])
def create_all_missing_files():
    """Create all missing CSS/JS files - Direct route"""
    from pathlib import Path
    import os
    
    BASE_STATIC = Path('/var/www/html/vidgenerator/src/web/static')
    created = []
    errors = []
    
    def create_file_if_missing(filepath, content, is_binary=False):
        try:
            if not filepath.exists():
                filepath.parent.mkdir(parents=True, exist_ok=True)
                if is_binary:
                    with open(filepath, 'wb') as f:
                        f.write(content)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                os.chmod(filepath, 0o644)
                return True
        except Exception as e:
            errors.append(f'{filepath.name}: {str(e)}')
        return False
    
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
    
    # JS files
    js_generator_files = {
        'generator-button-fixed.js': '// Generator Button Fixed\n',
        'generator-button-activator.js': '// Generator Button Activator\n',
        'generator-button-simple-fix.js': '// Generator Button Simple Fix\n',
        'generator-button-debug.js': '// Generator Button Debug\n',
        'generator-button-reload.js': '// Generator Button Reload\n',
        'generator-button-ai-integrated.js': '// Generator Button AI Integrated\n',
        'generator-button-simple-ai.js': '// Generator Button Simple AI\n',
        'generator-button-final-fix.js': '// Generator Button Final Fix\n',
        'generator-button-working.js': '// Generator Button Working\n',
    }
    
    for filename, content in js_generator_files.items():
        filepath = BASE_STATIC / 'js' / 'generator' / filename
        if create_file_if_missing(filepath, content):
            created.append(f'js/generator/{filename}')
    
    js_root_files = {
        'service-worker-register.js': '// Service Worker Register\n',
        'ai-engine-simple.js': '// AI Engine Simple\n',
        'service-worker-ai-integration.js': '// Service Worker AI Integration\n',
        'stats-counter.js': '// Stats Counter\n',
        'utils.js': '// Utils\n',
        'main.js': '// Main\n',
    }
    
    for filename, content in js_root_files.items():
        filepath = BASE_STATIC / 'js' / filename
        if create_file_if_missing(filepath, content):
            created.append(f'js/{filename}')
    
    return jsonify({
        'success': True,
        'created': created,
        'errors': errors,
        'count': len(created),
        'message': f'Created {len(created)} missing files, {len(errors)} errors'
    })

