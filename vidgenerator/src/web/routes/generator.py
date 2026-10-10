"""Generator routes"""
from flask import render_template, request, jsonify, send_file, make_response
from src.db.models import db, Documentary, MovieClip
from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
from src.services.cache.query_cache import query_cache
import threading
import uuid
import os
import json
from datetime import datetime


def register_generator_routes(app):
    """Register generator routes"""
    
    # Don't initialize heavy services at module level - create them on demand
    pipeline = None
    
    def get_pipeline():
        """Get pipeline instance (lazy initialization)"""
        nonlocal pipeline
        if pipeline is None:
            pipeline = PipelineOrchestrator()
        return pipeline
    
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/generator', endpoint='generator', strict_slashes=False)
    @app.route('/generator/', endpoint='generator_slash', strict_slashes=False)
    def generator_index():
        """Generator interface page"""
        try:
            import time
            import random
            version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            # Force template reload by clearing Jinja cache
            from flask import current_app
            if hasattr(current_app, 'jinja_env'):
                current_app.jinja_env.cache.clear()
            response = make_response(render_template('generator/index.html', page_version=version))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, proxy-revalidate, no-transform'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Content-Version'] = version
            response.headers['X-Timestamp'] = str(time.time())
            # Add unique ETag based on version
            response.headers['ETag'] = f'"{version}"'
            return response
        except Exception as e:
            return f"Error loading generator: {e}", 500
    
    # NOTE: /vidgenerator route is handled by home.py (register_home_routes)
    # Do NOT register /vidgenerator here to avoid route conflicts
    
    # Generator Debugger Routes (registered directly like other generator routes)
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/generator-debugger', endpoint='generator_debugger', strict_slashes=False)
    @app.route('/generator-debugger/', endpoint='generator_debugger_slash', strict_slashes=False)
    def generator_debugger_page():
        """Generator debugger UI page"""
        try:
            from src.web.routes.generator_debugger import debugger
            # Try to render template
            return render_template('generator_debugger/index.html')
        except Exception as e:
            # Fallback: Return embedded HTML if template not found
            import traceback
            error_msg = str(e)
            print(f"[GeneratorDebugger] Template error: {error_msg}")
            return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Generator Debugger</title>
<style>body{{font-family:monospace;background:#0a0a0a;color:#00ff00;padding:20px}}
.btn{{padding:10px 20px;background:#00ff00;color:#000;border:none;cursor:pointer;margin:5px}}
.status{{padding:10px;margin:10px 0;border-left:4px solid #00ff00;background:rgba(0,255,0,0.1)}}
</style></head><body>
<h1>🔧 Generator Page Debugger</h1>
<div class="status">Template error: {error_msg}</div>
<button class="btn" onclick="fetch('/vidgenerator/api/generator/debug').then(r=>r.json()).then(d=>alert(JSON.stringify(d)))">Test API</button>
</body></html>""", 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/api/generator/debug', methods=['GET'], endpoint='generator_debug_api', strict_slashes=False)
    def diagnose_generator():
        """Diagnose generator page issues"""
        try:
            from src.web.routes.generator_debugger import debugger
            diagnosis = debugger.diagnose_generator_page()
            return jsonify({
                'success': True,
                'diagnosis': diagnosis
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/fix/create-all-missing-files', methods=['POST', 'GET'], endpoint='create_all_missing_files', strict_slashes=False)
    @app.route('/vidgenerator/api/fix/create-all-missing-files', methods=['POST', 'GET'], endpoint='create_all_missing_files_vidgenerator', strict_slashes=False)
    def create_all_missing_files():
        """Create all missing CSS/JS files"""
        from pathlib import Path
        import os
        
        BASE_STATIC = Path('/var/www/html/vidgenerator/src/web/static')
        created = []
        errors = []
        
        def create_file_if_missing(filepath, content, is_binary=False):
            """Create file if it doesn't exist"""
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
            if create_file_if_missing(filepath, content, is_binary=True):
                created.append(f'img/{filename}')
        
        return jsonify({
            'success': True,
            'created': created,
            'errors': errors,
            'count': len(created),
            'message': f'Created {len(created)} missing files, {len(errors)} errors'
        })
    
    @app.route('/api/generator/fix', methods=['POST'], endpoint='generator_fix_api', strict_slashes=False)
    def fix_generator():
        """Apply fixes to generator page"""
        try:
            from src.web.routes.generator_debugger import debugger
            result = debugger.fix_generator_page()
            return jsonify(result)
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/generator/check-processes', methods=['GET'], endpoint='generator_check_processes', strict_slashes=False)
    def check_processes():
        """Check server processes"""
        try:
            from src.web.routes.generator_debugger import debugger
            processes = debugger.check_server_processes()
            return jsonify({
                'success': True,
                'processes': processes
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/generator/check-uploads', methods=['GET'], endpoint='generator_check_uploads', strict_slashes=False)
    def check_uploads():
        """Check if files were uploaded correctly"""
        try:
            from src.web.routes.generator_debugger import debugger
            upload_status = debugger.check_file_uploads()
            return jsonify({
                'success': True,
                'upload_status': upload_status
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/generator/check-uwsgi', methods=['GET'], endpoint='generator_check_uwsgi', strict_slashes=False)
    def check_uwsgi():
        """Check uWSGI status"""
        try:
            from src.web.routes.generator_debugger import debugger
            status = debugger.check_uwsgi_status()
            return jsonify({
                'success': True,
                'status': status
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/api/generator/restart-uwsgi', methods=['POST'], endpoint='generator_restart_uwsgi', strict_slashes=False)
    def restart_uwsgi():
        """Restart uWSGI service"""
        try:
            from src.web.routes.generator_debugger import debugger
            result = debugger.restart_uwsgi()
            return jsonify({
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'output': result.get('output', ''),
                'status_output': result.get('status_output', '')
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    # Additional debugger API endpoints
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/api/generator/test-endpoint', methods=['GET'], endpoint='test_endpoint_api', strict_slashes=False)
    def test_endpoint():
        """Test endpoint connectivity"""
        return jsonify({
            'success': True,
            'message': 'Debugger API is working',
            'timestamp': datetime.now().isoformat(),
            'endpoints': {
                'debug': '/api/generator/debug',
                'fix': '/api/generator/fix',
                'check-processes': '/api/generator/check-processes',
                'check-uploads': '/api/generator/check-uploads',
                'check-uwsgi': '/api/generator/check-uwsgi',
                'restart-uwsgi': '/api/generator/restart-uwsgi',
                'test-endpoint': '/api/generator/test-endpoint',
                'test-file-access': '/api/generator/test-file-access',
                'create-missing-files': '/api/generator/create-missing-files'
            }
        })
    
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/api/generator/test-file-access', methods=['GET'], endpoint='test_file_access_api', strict_slashes=False)
    def test_file_access():
        """Test file access and permissions"""
        try:
            from src.web.routes.generator_debugger import debugger
            
            test_results = {
                'timestamp': datetime.now().isoformat(),
                'files': {},
                'permissions': {}
            }
            
            # Test critical files
            test_files = {
                'generator-button-activator.js': debugger.static_path / 'generator-button-activator.js',
                'service-worker-gatherer.js': debugger.base_path / 'src/web/static/js/service-worker-gatherer.js',
                'generator/index.html': debugger.template_path / 'index.html',
                'generator.py': debugger.routes_path / 'generator.py'
            }
            
            for name, path in test_files.items():
                exists = path.exists()
                readable = False
                writable = False
                size = 0
                
                if exists:
                    try:
                        stat = path.stat()
                        size = stat.st_size
                        readable = os.access(path, os.R_OK)
                        writable = os.access(path, os.W_OK)
                    except Exception:
                        pass
                
                test_results['files'][name] = {
                    'exists': exists,
                    'readable': readable,
                    'writable': writable,
                    'size': size,
                    'path': str(path)
                }
            
            # Test directory permissions
            test_dirs = {
                'static/js': debugger.static_path,
                'static/js/generator': debugger.static_path / 'generator',
                'templates/generator': debugger.template_path
            }
            
            for name, path in test_dirs.items():
                exists = path.exists()
                readable = False
                writable = False
                
                if exists:
                    readable = os.access(path, os.R_OK)
                    writable = os.access(path, os.W_OK)
                
                test_results['permissions'][name] = {
                    'exists': exists,
                    'readable': readable,
                    'writable': writable,
                    'path': str(path)
                }
            
            return jsonify({
                'success': True,
                'results': test_results
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    # NOTE: Middleware strips /vidgenerator, so register WITHOUT prefix
    @app.route('/api/generator/create-missing-files', methods=['POST'], endpoint='create_missing_files_api', strict_slashes=False)
    def create_missing_files():
        """Create missing files with fallback content"""
        try:
            from src.web.routes.generator_debugger import debugger
            import subprocess
            
            created = []
            errors = []
            
            # Create generator-button-activator.js if missing
            activator_path = debugger.static_path / 'generator-button-activator.js'
            if not activator_path.exists() or activator_path.stat().st_size == 0:
                try:
                    activator_path.parent.mkdir(parents=True, exist_ok=True)
                    content = debugger._get_activator_script_content()
                    if not content.startswith("// File should be uploaded"):
                        with open(activator_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        subprocess.run(['chmod', '644', str(activator_path)], timeout=5, check=False)
                        subprocess.run(['chown', 'www-data:www-data', str(activator_path)], timeout=5, check=False)
                        created.append('generator-button-activator.js')
                except Exception as e:
                    errors.append(f'Failed to create generator-button-activator.js: {str(e)}')
            
            # Create service-worker-gatherer.js if missing
            sw_path = debugger.base_path / 'src/web/static/js/service-worker-gatherer.js'
            if not sw_path.exists() or (sw_path.exists() and sw_path.stat().st_size == 0):
                try:
                    sw_path.parent.mkdir(parents=True, exist_ok=True)
                    content = debugger._get_service_worker_content()
                    # Always create with fallback content if file doesn't exist
                    if content:
                        with open(sw_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        subprocess.run(['chmod', '644', str(sw_path)], timeout=5, check=False)
                        subprocess.run(['chown', 'www-data:www-data', str(sw_path)], timeout=5, check=False)
                        if sw_path.exists() and sw_path.stat().st_size > 0:
                            created.append('service-worker-gatherer.js')
                        else:
                            errors.append('service-worker-gatherer.js file created but is empty')
                    else:
                        errors.append('service-worker-gatherer.js: Could not get content')
                except Exception as e:
                    errors.append(f'Failed to create service-worker-gatherer.js: {str(e)}')
                    import traceback
                    errors.append(f'Traceback: {traceback.format_exc()[:500]}')
            
            return jsonify({
                'success': len(errors) == 0,
                'created': created,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            import traceback
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    # Include all generator-related API routes from original routes.py
    # (Copy all the API routes related to generation here)
    # For now, keeping them in original routes.py for backward compatibility
    # These will be moved gradually

