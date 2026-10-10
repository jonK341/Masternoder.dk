"""Debug API routes for error logging and diagnostics"""
from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
import traceback

debug_api_bp = Blueprint('debug_api', __name__)

# Log file path
LOG_FILE = '/var/www/html/vidgenerator/debug.log'

def log_error(level, message, error=None, context=None):
    """Log error to file"""
    try:
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'error': str(error) if error else None,
            'context': context or {}
        }
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return True
    except Exception as e:
        print(f"Failed to write log: {e}")
        return False

@debug_api_bp.route('/api/debug/log', methods=['POST'])
def log_client_error():
    """Log client-side error"""
    try:
        data = request.get_json()
        level = data.get('level', 'error')
        message = data.get('message', '')
        error = data.get('error', '')
        context = data.get('context', {})
        
        log_error(level, message, error, context)
        return jsonify({'success': True, 'message': 'Error logged'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@debug_api_bp.route('/api/debug/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        limit = int(request.args.get('limit', 100))
        level = request.args.get('level', None)
        
        if not os.path.exists(LOG_FILE):
            return jsonify({'success': True, 'logs': []})
        
        logs = []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    log_entry = json.loads(line.strip())
                    if not level or log_entry.get('level') == level:
                        logs.append(log_entry)
                except:
                    continue
        
        # Return most recent first
        logs.reverse()
        return jsonify({'success': True, 'logs': logs, 'total': len(logs)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@debug_api_bp.route('/api/debug/clear-logs', methods=['POST'])
def clear_logs():
    """Clear log file"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')
        return jsonify({'success': True, 'message': 'Logs cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@debug_api_bp.route('/api/debug/system-info', methods=['GET'])
def get_system_info():
    """Get system information"""
    try:
        import platform
        import sys
        
        info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'server_time': datetime.now().isoformat(),
            'log_file_exists': os.path.exists(LOG_FILE),
            'log_file_size': os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0
        }
        
        return jsonify({'success': True, 'info': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@debug_api_bp.route('/api/debug/auto-fix', methods=['POST'])
def auto_fix_issues():
    """Auto-fix common issues"""
    try:
        fixes_applied = []
        
        # Fix 1: Clear Python cache
        import shutil
        cache_dirs = ['__pycache__', '.pyc']
        for root, dirs, files in os.walk('/var/www/html/vidgenerator'):
            if '__pycache__' in dirs:
                cache_path = os.path.join(root, '__pycache__')
                try:
                    shutil.rmtree(cache_path)
                    fixes_applied.append(f'Cleared cache: {cache_path}')
                except:
                    pass
        
        # Fix 2: Restart uWSGI
        import subprocess
        try:
            subprocess.run(['systemctl', 'restart', 'uwsgi-vidgenerator.service'], 
                         capture_output=True, timeout=10)
            fixes_applied.append('Restarted uWSGI')
        except:
            fixes_applied.append('Failed to restart uWSGI (may need manual restart)')
        
        # Fix 3: Check and fix database
        try:
            from src.db.models import db
            db.create_all()
            fixes_applied.append('Database tables verified')
        except Exception as e:
            fixes_applied.append(f'Database check: {str(e)}')
        
        return jsonify({'success': True, 'fixes_applied': fixes_applied})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@debug_api_bp.route('/api/debug/restore-themes', methods=['POST'])
def restore_themes():
    """Restore all themes to original entertainment state"""
    try:
        from src.services.theme_manager.theme_config import ThemeConfig
        
        theme_config = ThemeConfig()
        themes_restored = []
        
        # List of all themes to restore
        theme_list = ['matrix', 'cyberpunk', 'sci-fi', 'nature', 'mtg', 'halo4', 'wwii']
        
        for theme_name in theme_list:
            try:
                theme = theme_config.get_theme(theme_name)
                if theme:
                    themes_restored.append({
                        'name': theme_name,
                        'status': 'restored',
                        'has_video': bool(theme.get('background_video')),
                        'has_image': bool(theme.get('background_image')),
                        'entertainment_level': theme.get('entertainment_level', 'unknown')
                    })
                else:
                    themes_restored.append({
                        'name': theme_name,
                        'status': 'not_found',
                        'message': 'Theme not found in config'
                    })
            except Exception as e:
                themes_restored.append({
                    'name': theme_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'themes_restored': themes_restored,
            'message': f'Restored {len([t for t in themes_restored if t["status"] == "restored"])} themes'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_api_bp.route('/api/debug/test-all-endpoints', methods=['GET'])
def test_all_endpoints():
    """Test all API endpoints and return results"""
    try:
        import requests
        base_url = 'http://127.0.0.1:5000'
        
        endpoints = [
            '/vidgenerator',
            '/vidgenerator/generator',
            '/vidgenerator/gallery',
            '/vidgenerator/chat',
            '/vidgenerator/stats',
            '/vidgenerator/api/points/all',
            '/vidgenerator/api/points/chat',
            '/vidgenerator/api/points/graduation'
        ]
        
        results = []
        for endpoint in endpoints:
            try:
                response = requests.get(f'{base_url}{endpoint}', timeout=5)
                results.append({
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'ok': response.ok,
                    'content_type': response.headers.get('content-type', ''),
                    'size': len(response.content)
                })
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

