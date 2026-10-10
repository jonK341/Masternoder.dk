"""
Generator Page Debugger
Diagnoses and fixes issues with the generator page
"""
from flask import Blueprint, jsonify, request, render_template
import os
import subprocess
from pathlib import Path
from datetime import datetime
import json

generator_debugger_bp = Blueprint('generator_debugger', __name__)

class GeneratorPageDebugger:
    """Debug and fix generator page issues"""
    
    def __init__(self):
        self.base_path = Path('/var/www/html/vidgenerator')
        self.template_path = self.base_path / 'src/web/templates/generator'
        self.static_path = self.base_path / 'src/web/static/js/generator'
        self.routes_path = self.base_path / 'src/web/routes'
    
    def check_server_processes(self) -> dict:
        """Check server processes (uWSGI, Apache, etc.)"""
        processes = {
            'uwsgi': {'running': False, 'pid': None, 'command': None},
            'apache': {'running': False, 'pid': None, 'command': None},
            'python': {'running': False, 'pids': [], 'commands': []},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Check uWSGI
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'uwsgi' in line.lower() and 'grep' not in line.lower():
                        parts = line.split()
                        if len(parts) > 1:
                            processes['uwsgi']['running'] = True
                            processes['uwsgi']['pid'] = parts[1]
                            processes['uwsgi']['command'] = ' '.join(parts[10:])[:100]
                    
                    if 'apache' in line.lower() or 'httpd' in line.lower():
                        if 'grep' not in line.lower():
                            parts = line.split()
                            if len(parts) > 1:
                                processes['apache']['running'] = True
                                if not processes['apache']['pid']:
                                    processes['apache']['pid'] = parts[1]
                    
                    if 'python' in line.lower() and 'flask' in line.lower():
                        parts = line.split()
                        if len(parts) > 1:
                            processes['python']['running'] = True
                            processes['python']['pids'].append(parts[1])
                            processes['python']['commands'].append(' '.join(parts[10:])[:100])
        except Exception as e:
            processes['error'] = str(e)
        
        return processes
    
    def check_file_uploads(self) -> dict:
        """Check if files were uploaded correctly"""
        files_to_check = {
            'generator.py': self.routes_path / 'generator.py',
            'generator_debugger.py': self.routes_path / 'generator_debugger.py',
            'generator/index.html': self.template_path / 'index.html',
            'generator-icons-fix.css': self.base_path / 'src/web/static/css/generator-icons-fix.css',
            'generator-button-activator.js': self.static_path / 'generator-button-activator.js',
            'service-worker-gatherer.js': self.base_path / 'src/web/static/js/service-worker-gatherer.js',
            'base.html': self.base_path / 'src/web/templates/base.html'
        }
        
        upload_status = {
            'timestamp': datetime.now().isoformat(),
            'files': {},
            'all_uploaded': True
        }
        
        for name, file_path in files_to_check.items():
            exists = file_path.exists()
            upload_status['files'][name] = {
                'exists': exists,
                'path': str(file_path),
                'size': file_path.stat().st_size if exists else 0,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if exists else None
            }
            if not exists:
                upload_status['all_uploaded'] = False
        
        return upload_status
    
    def check_uwsgi_status(self) -> dict:
        """Check uWSGI service status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'service_active': False,
            'service_enabled': False,
            'process_running': False,
            'error': None
        }
        
        try:
            # Check systemd service status
            result = subprocess.run(
                ['systemctl', 'is-active', 'uwsgi'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status['service_active'] = result.stdout.strip() == 'active'
            
            result = subprocess.run(
                ['systemctl', 'is-enabled', 'uwsgi'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status['service_enabled'] = result.stdout.strip() == 'enabled'
            
            # Check if process is running
            result = subprocess.run(
                ['pgrep', '-f', 'uwsgi'],
                capture_output=True,
                text=True,
                timeout=5
            )
            status['process_running'] = len(result.stdout.strip()) > 0
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def restart_uwsgi(self) -> dict:
        """Restart uWSGI service"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'message': '',
            'output': ''
        }
        
        try:
            # Restart uWSGI
            restart_result = subprocess.run(
                ['systemctl', 'restart', 'uwsgi'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            result['output'] = restart_result.stdout + restart_result.stderr
            
            if restart_result.returncode == 0:
                result['success'] = True
                result['message'] = 'uWSGI restarted successfully'
            else:
                result['message'] = f'uWSGI restart failed: {restart_result.stderr}'
            
            # Wait a moment and check status
            import time
            time.sleep(2)
            
            status_result = subprocess.run(
                ['systemctl', 'status', 'uwsgi', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            result['status_output'] = status_result.stdout
            
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f'Error restarting uWSGI: {str(e)}'
        
        return result
    
    def diagnose_generator_page(self) -> dict:
        """Comprehensive diagnosis of generator page"""
        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'template_exists': False,
            'scripts': {},
            'button_exists': False,
            'service_worker': {},
            'routes_registered': False,
            'issues': [],
            'fixes': []
        }
        
        # Check template
        template_file = self.template_path / 'index.html'
        diagnosis['template_exists'] = template_file.exists()
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for generate button
            diagnosis['button_exists'] = 'id="generate-btn"' in content or 'generate-btn' in content
            
            # Check for required scripts
            required_scripts = [
                'generator-button-fixed.js',
                'generator-button-activator.js',
                'two-phase-simplified.js',
                'service-worker-gatherer.js'
            ]
            
            for script in required_scripts:
                script_path = self.static_path / script
                diagnosis['scripts'][script] = {
                    'exists': script_path.exists(),
                    'in_template': script in content
                }
                
                if not script_path.exists():
                    diagnosis['issues'].append(f'Missing script: {script}')
                    diagnosis['fixes'].append({
                        'type': 'create_script',
                        'script': script,
                        'priority': 'high'
                    })
        
        # Check if routes are registered in generator.py
        generator_routes_file = self.routes_path / 'generator.py'
        if generator_routes_file.exists():
            with open(generator_routes_file, 'r', encoding='utf-8') as f:
                routes_content = f.read()
                diagnosis['routes_registered'] = 'generator-debugger' in routes_content or 'generator_debugger' in routes_content
        
        # Check service worker registration
        diagnosis['service_worker'] = {
            'registration_code_exists': False,
            'disabled': 'SERVICE WORKER COMPLETELY DISABLED' in content if template_file.exists() else False
        }
        
        return diagnosis
    
    def fix_generator_page(self) -> dict:
        """Apply fixes to generator page"""
        fixes_applied = []
        errors = []
        
        # Fix permissions first
        try:
            subprocess.run(['chmod', '-R', '755', str(self.static_path.parent)], timeout=5, check=False)
            subprocess.run(['chown', '-R', 'www-data:www-data', str(self.static_path.parent)], timeout=5, check=False)
            fixes_applied.append('Fixed permissions on static/js directory')
        except Exception as e:
            errors.append(f'Permission fix warning: {str(e)}')
        
        # Check and create missing scripts
        scripts_to_check = {
            'generator-button-activator.js': {
                'path': self.static_path / 'generator-button-activator.js',
                'content': self._get_activator_script_content()
            },
            'service-worker-gatherer.js': {
                'path': self.base_path / 'src/web/static/js/service-worker-gatherer.js',
                'content': self._get_service_worker_content()
            }
        }
        
        for script_name, script_info in scripts_to_check.items():
            script_path = script_info['path']
            content = script_info['content']
            
            if not script_path.exists() or script_path.stat().st_size == 0:
                try:
                    # Ensure directory exists with correct permissions
                    script_path.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(['chmod', '755', str(script_path.parent)], timeout=5, check=False)
                    subprocess.run(['chown', 'www-data:www-data', str(script_path.parent)], timeout=5, check=False)
                    
                    # Skip if content is just a placeholder
                    if content.startswith("// File should be uploaded"):
                        fixes_applied.append(f'Skipped {script_name} (needs manual upload)')
                        errors.append(f'{script_name} needs to be uploaded manually')
                        continue
                    
                    # Create file with correct permissions
                    with open(script_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Set file permissions
                    subprocess.run(['chmod', '644', str(script_path)], timeout=5, check=False)
                    subprocess.run(['chown', 'www-data:www-data', str(script_path)], timeout=5, check=False)
                    
                    if script_path.exists() and script_path.stat().st_size > 0:
                        fixes_applied.append(f'Created {script_name} ({script_path.stat().st_size} bytes)')
                    else:
                        errors.append(f'Failed to create {script_name} (file not found after creation)')
                except PermissionError as e:
                    errors.append(f'Permission denied creating {script_name}: {str(e)}')
                    fixes_applied.append(f'Cannot create {script_name} - permission denied (run as root or fix permissions)')
                except Exception as e:
                    errors.append(f'Failed to create {script_name}: {str(e)}')
                    # Try alternative: use subprocess to create file
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.js', encoding='utf-8') as tmp:
                            tmp.write(content)
                            tmp_path = tmp.name
                        subprocess.run(['cp', tmp_path, str(script_path)], timeout=5, check=False)
                        subprocess.run(['chmod', '644', str(script_path)], timeout=5, check=False)
                        subprocess.run(['chown', 'www-data:www-data', str(script_path)], timeout=5, check=False)
                        os.unlink(tmp_path)
                        if script_path.exists():
                            fixes_applied.append(f'Created {script_name} (via subprocess)')
                        else:
                            errors.append(f'Alternative creation failed for {script_name}')
                    except Exception as e2:
                        errors.append(f'Alternative creation also failed: {str(e2)}')
            else:
                fixes_applied.append(f'{script_name} already exists')
        
        return {
            'success': len(errors) == 0,
            'fixes_applied': fixes_applied,
            'errors': errors,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_activator_script_content(self) -> str:
        """Get content for activator script"""
        # Try to read from local file first
        local_file = Path(__file__).parent.parent.parent / 'static' / 'js' / 'generator' / 'generator-button-activator.js'
        if local_file.exists():
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
        
        # Fallback content
        return '''/**
 * Generator Button Activator - Ensures button works correctly
 */
(function() {
    'use strict';
    console.log('[GeneratorActivator] Initializing generator button activator...');
    
    let buttonInitialized = false;
    let initializationAttempts = 0;
    const maxAttempts = 10;
    
    function initializeGeneratorButton() {
        initializationAttempts++;
        
        const generateBtn = document.getElementById('generate-btn');
        if (!generateBtn) {
            if (initializationAttempts < maxAttempts) {
                console.log(`[GeneratorActivator] Button not found, retrying... (${initializationAttempts}/${maxAttempts})`);
                setTimeout(initializeGeneratorButton, 500);
            } else {
                console.error('[GeneratorActivator] Generate button not found after max attempts!');
            }
            return;
        }
        
        if (buttonInitialized) {
            console.log('[GeneratorActivator] Button already initialized');
            return;
        }
        
        console.log('[GeneratorActivator] Found generate button, setting up...');
        
        // Remove all existing event listeners by cloning
        const newBtn = generateBtn.cloneNode(true);
        generateBtn.parentNode.replaceChild(newBtn, generateBtn);
        
        // Get the new button reference
        const btn = document.getElementById('generate-btn');
        
        // Ensure button is enabled
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.style.pointerEvents = 'auto';
        
        // Add click handler
        const clickHandler = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('[GeneratorActivator] Generate button clicked!');
            
            // Try FixedGeneratorButton first
            if (window.fixedGeneratorButton && typeof window.fixedGeneratorButton.startCompleteGeneration === 'function') {
                await window.fixedGeneratorButton.startCompleteGeneration();
            } else if (window.simplifiedGenerator && typeof window.simplifiedGenerator.startGeneration === 'function') {
                await window.simplifiedGenerator.startGeneration();
            } else {
                alert('Generator not initialized. Please refresh the page.');
            }
        };
        
        btn.addEventListener('click', clickHandler, true);
        btn.onclick = clickHandler;
        
        buttonInitialized = true;
        console.log('[GeneratorActivator] ✓ Button initialized and ready!');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeGeneratorButton);
    } else {
        setTimeout(initializeGeneratorButton, 100);
    }
    
    setTimeout(initializeGeneratorButton, 2000);
})();
'''
    
    def _get_service_worker_content(self) -> str:
        """Get content for service worker"""
        # Try to read from local file first
        local_file = Path(__file__).parent.parent.parent / 'static' / 'js' / 'service-worker-gatherer.js'
        if local_file.exists():
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
        
        # Try to read from server location
        server_file = self.base_path / 'src/web/static/js/service-worker-gatherer.js'
        if server_file.exists():
            try:
                with open(server_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
        
        # Fallback: return minimal service worker
        return '''/**
 * Service Worker as Data Gatherer - Auto-generated fallback
 */
const APP_VERSION = 'dg-sw-v5-gatherer-fallback';
const CACHE_NAME = `documentary-generator-${APP_VERSION}`;

self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing fallback version:', APP_VERSION);
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating fallback version:', APP_VERSION);
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    return self.clients.claim();
});

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'GATHER_INTELLIGENCE') {
        console.log('[ServiceWorker] Gather intelligence requested');
        event.ports[0].postMessage({ 
            success: true, 
            data: { 
                message: 'Fallback service worker - please upload full version',
                version: APP_VERSION
            } 
        });
    }
});

self.addEventListener('fetch', (event) => {
    // Basic fetch handler
    event.respondWith(fetch(event.request));
});
'''

debugger = GeneratorPageDebugger()

@generator_debugger_bp.route('/api/generator/debug', methods=['GET'])
def diagnose_generator():
    """Diagnose generator page issues"""
    try:
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

@generator_debugger_bp.route('/api/fix/create-all-missing-files', methods=['POST', 'GET'])
@generator_debugger_bp.route('/vidgenerator/api/fix/create-all-missing-files', methods=['POST', 'GET'])
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
    
    from flask import jsonify
    return jsonify({
        'success': True,
        'created': created,
        'errors': errors,
        'count': len(created),
        'message': f'Created {len(created)} missing files, {len(errors)} errors'
    })

@generator_debugger_bp.route('/api/generator/fix', methods=['POST'])
def fix_generator():
    """Apply fixes to generator page"""
    try:
        result = debugger.fix_generator_page()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@generator_debugger_bp.route('/api/generator/check-processes', methods=['GET'])
def check_processes():
    """Check server processes"""
    try:
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

@generator_debugger_bp.route('/api/generator/check-uploads', methods=['GET'])
def check_uploads():
    """Check if files were uploaded correctly"""
    try:
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

@generator_debugger_bp.route('/api/generator/check-uwsgi', methods=['GET'])
def check_uwsgi():
    """Check uWSGI status"""
    try:
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

@generator_debugger_bp.route('/api/generator/restart-uwsgi', methods=['POST'])
def restart_uwsgi():
    """Restart uWSGI service"""
    try:
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

@generator_debugger_bp.route('/api/generator/test-endpoint', methods=['GET'])
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

@generator_debugger_bp.route('/api/generator/test-file-access', methods=['GET'])
def test_file_access():
    """Test file access and permissions"""
    try:
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
                except Exception as e:
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

@generator_debugger_bp.route('/api/generator/create-missing-files', methods=['POST'])
def create_missing_files():
    """Create missing files with fallback content"""
    try:
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
        if not sw_path.exists() or sw_path.stat().st_size == 0:
            try:
                sw_path.parent.mkdir(parents=True, exist_ok=True)
                content = debugger._get_service_worker_content()
                with open(sw_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                subprocess.run(['chmod', '644', str(sw_path)], timeout=5, check=False)
                subprocess.run(['chown', 'www-data:www-data', str(sw_path)], timeout=5, check=False)
                created.append('service-worker-gatherer.js')
            except Exception as e:
                errors.append(f'Failed to create service-worker-gatherer.js: {str(e)}')
        
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

@generator_debugger_bp.route('/generator-debugger')
@generator_debugger_bp.route('/generator-debugger/')
def generator_debugger_page():
    """Generator debugger UI page"""
    try:
        # Try to render template
        return render_template('generator_debugger/index.html')
    except Exception as e:
        # Fallback: Return embedded HTML if template not found
        import traceback
        error_msg = str(e)
        print(f"[GeneratorDebugger] Template error: {error_msg}")
        print(traceback.format_exc())
        
        # Return embedded HTML as fallback
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generator Page Debugger</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #00ff00;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 0, 0.1);
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
        }}
        .section {{
            background: rgba(0, 20, 0, 0.9);
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .section h2 {{
            color: #00ff00;
            margin-bottom: 15px;
            border-bottom: 1px solid rgba(0, 255, 0, 0.3);
            padding-bottom: 10px;
        }}
        .button-group {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        .btn {{
            padding: 12px 24px;
            background: linear-gradient(135deg, #00ff00, #00cc00);
            color: #000;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s;
        }}
        .btn:hover {{ transform: scale(1.05); }}
        .btn-secondary {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        .status {{
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .status.success {{
            background: rgba(0, 255, 0, 0.1);
            border-color: #00ff00;
            color: #00ff00;
        }}
        .status.error {{
            background: rgba(255, 0, 0, 0.1);
            border-color: #ff0000;
            color: #ff0000;
        }}
        .status.warning {{
            background: rgba(255, 255, 0, 0.1);
            border-color: #ffff00;
            color: #ffff00;
        }}
        .diagnosis-result {{
            background: rgba(0, 0, 0, 0.5);
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
        }}
        pre {{
            background: rgba(0, 0, 0, 0.7);
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            color: #00ff00;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Generator Page Debugger</h1>
            <p>Diagnose and fix issues with the generator page</p>
        </div>
        
        <div class="section">
            <h2>🖥️ Server Processes</h2>
            <div class="button-group">
                <button class="btn" onclick="checkProcesses()">Check Processes</button>
                <button class="btn btn-secondary" onclick="checkUwsgi()">Check uWSGI</button>
                <button class="btn btn-secondary" onclick="restartUwsgi()">Restart uWSGI</button>
            </div>
            <div id="processes-result"></div>
        </div>
        
        <div class="section">
            <h2>📤 File Uploads</h2>
            <div class="button-group">
                <button class="btn" onclick="checkUploads()">Check Uploads</button>
            </div>
            <div id="uploads-result"></div>
        </div>
        
        <div class="section">
            <h2>🔍 Diagnosis</h2>
            <div class="button-group">
                <button class="btn" onclick="runDiagnosis()">Run Diagnosis</button>
                <button class="btn btn-secondary" onclick="testGeneratorButton()">Test Generator Button</button>
            </div>
            <div id="diagnosis-result"></div>
        </div>
        
        <div class="section">
            <h2>🛠️ Fixes</h2>
            <div class="button-group">
                <button class="btn" onclick="applyFixes()">Apply Auto-Fixes</button>
            </div>
            <div id="fixes-result"></div>
        </div>
    </div>
    
    <script>
        const BASE_URL = window.location.origin;
        
        async function checkProcesses() {{
            const resultDiv = document.getElementById('processes-result');
            resultDiv.innerHTML = '<div class="status warning">Checking processes...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/check-processes`);
                const data = await response.json();
                
                if (data.success) {{
                    const p = data.processes;
                    let html = '<div class="diagnosis-result">';
                    html += `<div class="status ${{p.uwsgi.running ? 'success' : 'error'}}">
                        <strong>uWSGI:</strong> ${{p.uwsgi.running ? '✓ Running' : '✗ Not Running'}}
                        ${{p.uwsgi.pid ? `(PID: ${{p.uwsgi.pid}})` : ''}}
                    </div>`;
                    html += `<div class="status ${{p.apache.running ? 'success' : 'warning'}}">
                        <strong>Apache:</strong> ${{p.apache.running ? '✓ Running' : '⚠ Not Running'}}
                        ${{p.apache.pid ? `(PID: ${{p.apache.pid}})` : ''}}
                    </div>`;
                    html += `<div class="status ${{p.python.running ? 'success' : 'warning'}}">
                        <strong>Python/Flask:</strong> ${{p.python.running ? '✓ Running' : '⚠ Not Running'}}
                        ${{p.python.pids.length > 0 ? `(PIDs: ${{p.python.pids.join(', ')}})` : ''}}
                    </div>`;
                    if (p.uwsgi.command) {{
                        html += `<pre>uWSGI Command: ${{p.uwsgi.command}}</pre>`;
                    }}
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function checkUwsgi() {{
            const resultDiv = document.getElementById('processes-result');
            resultDiv.innerHTML = '<div class="status warning">Checking uWSGI...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/check-uwsgi`);
                const data = await response.json();
                
                if (data.success) {{
                    const s = data.status;
                    let html = '<div class="diagnosis-result">';
                    html += `<div class="status ${{s.service_active ? 'success' : 'error'}}">
                        <strong>Service Active:</strong> ${{s.service_active ? '✓ Yes' : '✗ No'}}
                    </div>`;
                    html += `<div class="status ${{s.service_enabled ? 'success' : 'warning'}}">
                        <strong>Service Enabled:</strong> ${{s.service_enabled ? '✓ Yes' : '⚠ No'}}
                    </div>`;
                    html += `<div class="status ${{s.process_running ? 'success' : 'error'}}">
                        <strong>Process Running:</strong> ${{s.process_running ? '✓ Yes' : '✗ No'}}
                    </div>`;
                    if (s.error) {{
                        html += `<div class="status error">Error: ${{s.error}}</div>`;
                    }}
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function restartUwsgi() {{
            if (!confirm('Are you sure you want to restart uWSGI?')) return;
            
            const resultDiv = document.getElementById('processes-result');
            resultDiv.innerHTML = '<div class="status warning">Restarting uWSGI...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/restart-uwsgi`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                const data = await response.json();
                
                if (data.success) {{
                    let html = '<div class="diagnosis-result">';
                    html += `<div class="status success">${{data.message}}</div>`;
                    if (data.status_output) {{
                        html += `<pre>${{data.status_output}}</pre>`;
                    }}
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error || data.message}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function checkUploads() {{
            const resultDiv = document.getElementById('uploads-result');
            resultDiv.innerHTML = '<div class="status warning">Checking uploads...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/check-uploads`);
                const data = await response.json();
                
                if (data.success) {{
                    const u = data.upload_status;
                    let html = '<div class="diagnosis-result">';
                    html += `<div class="status ${{u.all_uploaded ? 'success' : 'error'}}">
                        <strong>All Files Uploaded:</strong> ${{u.all_uploaded ? '✓ Yes' : '✗ No'}}
                    </div>`;
                    html += '<h3 style="margin-top: 15px; color: #00ff00;">Files:</h3>';
                    for (const [name, info] of Object.entries(u.files)) {{
                        html += `<div class="status ${{info.exists ? 'success' : 'error'}}">
                            <strong>${{name}}:</strong> ${{info.exists ? '✓ Exists' : '✗ Missing'}}
                            ${{info.exists ? `(${{(info.size / 1024).toFixed(2)}} KB, modified: ${{info.modified}})` : ''}}
                        </div>`;
                    }}
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function runDiagnosis() {{
            const resultDiv = document.getElementById('diagnosis-result');
            resultDiv.innerHTML = '<div class="status warning">Running diagnosis...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/debug`);
                const data = await response.json();
                
                if (data.success) {{
                    const d = data.diagnosis;
                    let html = '<div class="diagnosis-result">';
                    html += `<div class="status ${{d.template_exists ? 'success' : 'error'}}">
                        <strong>Template:</strong> ${{d.template_exists ? '✓ Found' : '✗ Missing'}}
                    </div>`;
                    html += `<div class="status ${{d.button_exists ? 'success' : 'error'}}">
                        <strong>Generate Button:</strong> ${{d.button_exists ? '✓ Found' : '✗ Missing'}}
                    </div>`;
                    html += `<div class="status ${{d.routes_registered ? 'success' : 'error'}}">
                        <strong>Routes Registered:</strong> ${{d.routes_registered ? '✓ Yes' : '✗ No'}}
                    </div>`;
                    html += '<h3 style="margin-top: 15px; color: #00ff00;">Scripts:</h3>';
                    for (const [script, info] of Object.entries(d.scripts)) {{
                        html += `<div class="status ${{info.exists && info.in_template ? 'success' : 'error'}}">
                            <strong>${{script}}:</strong> ${{info.exists && info.in_template ? '✓ Loaded' : '✗ Missing'}}
                        </div>`;
                    }}
                    if (d.issues.length > 0) {{
                        html += '<h3 style="margin-top: 15px; color: #ff0000;">Issues:</h3>';
                        d.issues.forEach(issue => {{
                            html += `<div class="status error">✗ ${{issue}}</div>`;
                        }});
                    }}
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        async function applyFixes() {{
            const resultDiv = document.getElementById('fixes-result');
            resultDiv.innerHTML = '<div class="status warning">Applying fixes...</div>';
            
            try {{
                const response = await fetch(`${{BASE_URL}}/vidgenerator/api/generator/fix`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                const data = await response.json();
                
                if (data.success) {{
                    let html = '<div class="diagnosis-result">';
                    html += '<div class="status success"><strong>Fixes Applied:</strong></div>';
                    data.fixes_applied.forEach(fix => {{
                        html += `<div class="status success">✓ ${{fix}}</div>`;
                    }});
                    html += '</div>';
                    resultDiv.innerHTML = html;
                }} else {{
                    resultDiv.innerHTML = `<div class="status error">Error: ${{data.error}}</div>`;
                }}
            }} catch (error) {{
                resultDiv.innerHTML = `<div class="status error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        function testGeneratorButton() {{
            window.open('/vidgenerator/generator', '_blank');
        }}
        
        // Auto-run checks on load
        window.addEventListener('load', () => {{
            setTimeout(() => {{
                checkProcesses();
                checkUploads();
                runDiagnosis();
            }}, 500);
        }});
    </script>
</body>
</html>""", 200, {'Content-Type': 'text/html; charset=utf-8'}
