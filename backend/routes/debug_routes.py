"""
Comprehensive Debug Routes
All debug endpoints for the debugger site
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional
import os
import sys
import json
import importlib
import inspect
from datetime import datetime

debug_bp = Blueprint('debug', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@debug_bp.route('/api/debug/system/<system_name>', methods=['GET'])
def debug_system(system_name: str):
    """Debug a specific system"""
    try:
        # Try to import and analyze the system
        system_info = {
            'name': system_name,
            'status': 'unknown',
            'module_path': None,
            'functions': [],
            'classes': [],
            'errors': []
        }
        
        # Try to find the system module
        try:
            # Common system locations
            possible_paths = [
                f'backend.services.{system_name}',
                f'backend.{system_name}',
                f'services.{system_name}',
                system_name
            ]
            
            module = None
            for path in possible_paths:
                try:
                    module = importlib.import_module(path)
                    system_info['module_path'] = path
                    break
                except ImportError:
                    continue
            
            if module:
                # Get all functions and classes
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj):
                        system_info['functions'].append({
                            'name': name,
                            'signature': str(inspect.signature(obj))
                        })
                    elif inspect.isclass(obj):
                        system_info['classes'].append({
                            'name': name,
                            'methods': [m for m in dir(obj) if not m.startswith('_')]
                        })
                
                system_info['status'] = 'found'
            else:
                system_info['status'] = 'not_found'
                system_info['errors'].append(f'Could not import system: {system_name}')
        except Exception as e:
            system_info['status'] = 'error'
            system_info['errors'].append(str(e))
        
        return jsonify({
            'success': True,
            'system': system_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/all-systems', methods=['GET'])
def debug_all_systems():
    """Debug all systems"""
    try:
        systems_dir = os.path.join(BASE_DIR, 'backend', 'services')
        systems = []
        
        if os.path.exists(systems_dir):
            for filename in os.listdir(systems_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    system_name = filename[:-3]
                    systems.append({
                        'name': system_name,
                        'file': filename,
                        'path': os.path.join(systems_dir, filename)
                    })
        
        return jsonify({
            'success': True,
            'systems': systems,
            'count': len(systems)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/route', methods=['GET'])
def debug_route():
    """Debug a specific route"""
    try:
        route_path = request.args.get('path', '')
        
        route_info = {
            'path': route_path,
            'status': 'unknown',
            'blueprint': None,
            'methods': [],
            'handler': None,
            'errors': []
        }
        
        # Try to find the route in registered blueprints
        from flask import current_app
        try:
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    if route_path in str(rule):
                        route_info['blueprint'] = rule.endpoint.split('.')[0] if '.' in rule.endpoint else rule.endpoint
                        route_info['methods'] = list(rule.methods)
                        route_info['handler'] = rule.endpoint
                        route_info['status'] = 'found'
                        break
                
                if route_info['status'] == 'unknown':
                    route_info['status'] = 'not_found'
                    route_info['errors'].append(f'Route not found: {route_path}')
        except Exception as e:
            route_info['status'] = 'error'
            route_info['errors'].append(str(e))
        
        return jsonify({
            'success': True,
            'route': route_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/all-routes', methods=['GET'])
def debug_all_routes():
    """Get all registered routes"""
    try:
        from flask import current_app
        routes = []
        
        try:
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    routes.append({
                        'path': str(rule),
                        'endpoint': rule.endpoint,
                        'methods': list(rule.methods),
                        'blueprint': rule.endpoint.split('.')[0] if '.' in rule.endpoint else rule.endpoint
                    })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
        return jsonify({
            'success': True,
            'routes': routes,
            'count': len(routes)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/frontend', methods=['GET'])
def debug_frontend():
    """Debug frontend page"""
    try:
        page_path = request.args.get('path', '')
        
        page_info = {
            'path': page_path,
            'status': 'unknown',
            'exists': False,
            'file_path': None,
            'size': 0,
            'errors': []
        }
        
        # Try to find the file
        full_path = os.path.join(BASE_DIR, page_path)
        if os.path.exists(full_path):
            page_info['exists'] = True
            page_info['file_path'] = full_path
            page_info['size'] = os.path.getsize(full_path)
            page_info['status'] = 'found'
        else:
            # Try common locations
            possible_paths = [
                os.path.join(BASE_DIR, 'vidgenerator', page_path),
                os.path.join(BASE_DIR, page_path),
                os.path.join(BASE_DIR, 'vidgenerator', page_path, 'index.html')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    page_info['exists'] = True
                    page_info['file_path'] = path
                    page_info['size'] = os.path.getsize(path)
                    page_info['status'] = 'found'
                    break
            
            if not page_info['exists']:
                page_info['status'] = 'not_found'
                page_info['errors'].append(f'File not found: {page_path}')
        
        return jsonify({
            'success': True,
            'page': page_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/test-url', methods=['GET'])
def test_url():
    """Test a URL"""
    try:
        import requests
        url = request.args.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL parameter required'
            }), 400
        
        result = {
            'url': url,
            'status': 'unknown',
            'status_code': None,
            'response_time': None,
            'headers': {},
            'errors': []
        }
        
        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=10, allow_redirects=True)
            end_time = datetime.now()
            
            result['status_code'] = response.status_code
            result['response_time'] = (end_time - start_time).total_seconds()
            result['headers'] = dict(response.headers)
            result['status'] = 'success' if response.status_code == 200 else 'error'
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['errors'].append('Request timed out')
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
            result['errors'].append('Connection error')
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
        
        return jsonify({
            'success': True,
            'result': result
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'requests library not available'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/test-all-routes', methods=['GET'])
def test_all_routes():
    """Test all routes"""
    try:
        from flask import current_app, url_for
        import requests
        
        results = []
        
        try:
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    if 'GET' in rule.methods and not rule.rule.startswith('/static'):
                        try:
                            # Try to build URL
                            url = f"http://localhost{rule.rule}"
                            start_time = datetime.now()
                            response = requests.get(url, timeout=5, allow_redirects=False)
                            end_time = datetime.now()
                            
                            results.append({
                                'route': str(rule),
                                'status_code': response.status_code,
                                'response_time': (end_time - start_time).total_seconds(),
                                'status': 'success' if response.status_code < 400 else 'error'
                            })
                        except Exception as e:
                            results.append({
                                'route': str(rule),
                                'status': 'error',
                                'error': str(e)
                            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'requests library not available'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/find-broken-urls', methods=['GET'])
def find_broken_urls():
    """Find broken URLs"""
    try:
        from flask import current_app
        import requests
        
        broken_urls = []
        
        try:
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    if 'GET' in rule.methods and not rule.rule.startswith('/static'):
                        try:
                            url = f"http://localhost{rule.rule}"
                            response = requests.get(url, timeout=5, allow_redirects=False)
                            
                            if response.status_code >= 400:
                                broken_urls.append({
                                    'url': url,
                                    'route': str(rule),
                                    'status_code': response.status_code,
                                    'error': f'HTTP {response.status_code}'
                                })
                        except requests.exceptions.RequestException as e:
                            broken_urls.append({
                                'url': url if 'url' in locals() else str(rule),
                                'route': str(rule),
                                'status_code': None,
                                'error': str(e)
                            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
        return jsonify({
            'success': True,
            'broken_urls': broken_urls,
            'count': len(broken_urls)
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'requests library not available'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/check-duplicates', methods=['GET'])
def check_duplicates():
    """Check for duplicate blueprints"""
    try:
        from flask import current_app
        
        blueprints = {}
        duplicates = []
        
        try:
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    blueprint_name = rule.endpoint.split('.')[0] if '.' in rule.endpoint else rule.endpoint
                    
                    if blueprint_name not in blueprints:
                        blueprints[blueprint_name] = []
                    
                    blueprints[blueprint_name].append({
                        'route': str(rule),
                        'endpoint': rule.endpoint,
                        'methods': list(rule.methods)
                    })
                
                # Find duplicates
                for blueprint_name, routes in blueprints.items():
                    if len(routes) > 1:
                        duplicates.append({
                            'blueprint': blueprint_name,
                            'routes': routes,
                            'count': len(routes)
                        })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
        return jsonify({
            'success': True,
            'blueprints': blueprints,
            'duplicates': duplicates,
            'total_blueprints': len(blueprints),
            'duplicate_count': len(duplicates)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/report', methods=['GET'])
def generate_report():
    """Generate comprehensive debug report"""
    try:
        report = {
            'timestamp': datetime.now().isoformat(),
            'systems': {},
            'routes': {},
            'blueprints': {},
            'errors': []
        }
        
        # Get all systems
        try:
            systems_response = debug_all_systems()
            systems_data = systems_response.get_json()
            if systems_data.get('success'):
                report['systems'] = {
                    'count': systems_data.get('count', 0),
                    'systems': systems_data.get('systems', [])
                }
        except Exception as e:
            report['errors'].append(f'Systems error: {str(e)}')
        
        # Get all routes
        try:
            routes_response = debug_all_routes()
            routes_data = routes_response.get_json()
            if routes_data.get('success'):
                report['routes'] = {
                    'count': routes_data.get('count', 0),
                    'routes': routes_data.get('routes', [])
                }
        except Exception as e:
            report['errors'].append(f'Routes error: {str(e)}')
        
        # Get duplicates
        try:
            duplicates_response = check_duplicates()
            duplicates_data = duplicates_response.get_json()
            if duplicates_data.get('success'):
                report['blueprints'] = {
                    'total': duplicates_data.get('total_blueprints', 0),
                    'duplicates': duplicates_data.get('duplicates', [])
                }
        except Exception as e:
            report['errors'].append(f'Duplicates error: {str(e)}')
        
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debug_bp.route('/api/debug/diagnose', methods=['POST'])
def diagnose_error():
    """AI-powered error diagnosis"""
    try:
        data = request.get_json() or {}
        error_message = data.get('error', '').strip()
        context = data.get('context', {})
        stack_trace = data.get('stack_trace', '')
        
        if not error_message:
            return jsonify({
                'success': False,
                'error': 'Error message is required'
            }), 400
        
        result = {
            'success': True,
            'error_message': error_message,
            'diagnosis': None,
            'suggestions': [],
            'ai_powered': False
        }
        
        # Try AI diagnosis
        try:
            from backend.services.llm_service import llm_service
            if llm_service.is_available():
                context_str = f"Context: {json.dumps(context)}" if context else ""
                stack_str = f"Stack trace: {stack_trace[:500]}" if stack_trace else ""
                
                prompt = f"""Diagnose this error and suggest fixes:

Error: {error_message}
{context_str}
{stack_str}

Provide:
1. Root cause (1 sentence)
2. 2-3 specific fixes"""
                
                llm_result = llm_service.complete(
                    prompt=prompt,
                    system_prompt="You are a debugging expert. Be concise and specific.",
                    temperature=0.3,
                    max_tokens=300
                )
                
                if llm_result.success and llm_result.content:
                    result['diagnosis'] = llm_result.content.strip()
                    result['ai_powered'] = True
                    
                    # Extract suggestions (lines starting with numbers or bullets)
                    lines = llm_result.content.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                            result['suggestions'].append(line)
        except Exception as e:
            result['ai_error'] = str(e)
        
        # Fallback: basic pattern matching
        if not result['diagnosis']:
            if '404' in error_message or 'not found' in error_message.lower():
                result['diagnosis'] = 'Resource not found. Check the URL/path and ensure the endpoint or file exists.'
                result['suggestions'] = [
                    '1. Verify the API endpoint is registered',
                    '2. Check for typos in the URL',
                    '3. Ensure the resource file exists'
                ]
            elif '500' in error_message or 'internal server' in error_message.lower():
                result['diagnosis'] = 'Server error. Check logs for exceptions and stack traces.'
                result['suggestions'] = [
                    '1. Check server logs for detailed error',
                    '2. Verify database connections',
                    '3. Check for missing dependencies'
                ]
            elif 'timeout' in error_message.lower():
                result['diagnosis'] = 'Request timeout. The operation took too long to complete.'
                result['suggestions'] = [
                    '1. Increase timeout limits',
                    '2. Optimize slow queries or operations',
                    '3. Check network connectivity'
                ]
            else:
                result['diagnosis'] = 'Error detected. Review the error message and context for details.'
                result['suggestions'] = ['1. Check logs for more information', '2. Verify input data', '3. Test in isolation']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Unit test suite (ordered 1-7: Generator, Battle, Trophies, Chat, Gallery, Points, Shop)
UNIT_TEST_MODULES = [
    {'nr': 1, 'name': 'Generator', 'module': 'tests.unit.test_01_generator', 'description': 'generator_db_service, video_generator_service'},
    {'nr': 2, 'name': 'Battle', 'module': 'tests.unit.test_02_battle', 'description': 'battle_db_service'},
    {'nr': 3, 'name': 'Trophies', 'module': 'tests.unit.test_03_trophies', 'description': 'trophies_db_service'},
    {'nr': 4, 'name': 'Chat', 'module': 'tests.unit.test_04_chat', 'description': 'chat_db_service'},
    {'nr': 5, 'name': 'Gallery', 'module': 'tests.unit.test_05_gallery', 'description': 'gallery_db_service'},
    {'nr': 6, 'name': 'Points', 'module': 'tests.unit.test_06_points', 'description': 'points_db_service'},
    {'nr': 7, 'name': 'Shop', 'module': 'tests.unit.test_07_shop', 'description': 'shop_db_service'},
    {'nr': 8, 'name': 'Migrations', 'module': 'tests.unit.test_08_migrations', 'description': 'migration idempotency'},
    {'nr': 9, 'name': 'Solutions', 'module': 'tests.unit.test_09_solutions', 'description': 'response shapes, contracts'},
]


@debug_bp.route('/api/debug/unit-tests', methods=['GET'])
def debug_unit_tests():
    """
    List unit test suite (1-7) or run tests when run=1.
    Enhances debug experience: run backend service tests from the site.
    """
    run_tests = request.args.get('run') in ('1', 'true', 'yes')
    try:
        if run_tests:
            import subprocess
            unit_dir = os.path.join(BASE_DIR, 'tests', 'unit')
            if not os.path.isdir(unit_dir):
                return jsonify({
                    'success': True,
                    'run': True,
                    'error': 'tests/unit directory not found',
                    'modules': UNIT_TEST_MODULES,
                    'passed': 0,
                    'failed': 0,
                    'output': '',
                })
            cmd = [sys.executable, '-m', 'pytest', unit_dir, '-v', '--tb=short', '-q']
            try:
                result = subprocess.run(
                    cmd,
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                )
                out = (result.stdout or '') + (result.stderr or '')
                passed = failed = 0
                for line in out.splitlines():
                    if ' passed' in line and 'failed' not in line:
                        try:
                            passed = int(line.strip().split()[0])
                        except (ValueError, IndexError):
                            pass
                    if ' failed' in line:
                        try:
                            parts = line.strip().split()
                            for i, p in enumerate(parts):
                                if p == 'failed':
                                    failed = int(parts[i - 1]) if i > 0 else 0
                                    break
                        except (ValueError, IndexError):
                            pass
                return jsonify({
                    'success': True,
                    'run': True,
                    'passed': passed,
                    'failed': failed,
                    'returncode': result.returncode,
                    'output': out,
                    'modules': UNIT_TEST_MODULES,
                })
            except subprocess.TimeoutExpired:
                return jsonify({
                    'success': True,
                    'run': True,
                    'error': 'Tests timed out (120s)',
                    'modules': UNIT_TEST_MODULES,
                    'passed': 0,
                    'failed': 0,
                    'output': 'Timeout.',
                })
            except Exception as e:
                return jsonify({
                    'success': True,
                    'run': True,
                    'error': str(e),
                    'modules': UNIT_TEST_MODULES,
                    'passed': 0,
                    'failed': 0,
                    'output': str(e),
                })
        return jsonify({
            'success': True,
            'run': False,
            'modules': UNIT_TEST_MODULES,
            'description': 'Backend unit tests (services 1-7). Run to verify solutions.',
            'docs': 'tests/unit/README.md',
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'modules': UNIT_TEST_MODULES,
        }), 500


def _run_hard_test_generator(quick: bool, poll_seconds: int) -> Dict:
    """Run generator URL hard-tests via Flask test client. Returns result dict."""
    try:
        from src.app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()
    except Exception as e:
        return {'success': False, 'error': f'App/client: {e}', 'results': [], 'passed': 0, 'failed': 0}

    def get(path):
        r = client.get(path)
        return r.status_code, r.get_json() if r.content_type and 'json' in (r.content_type or '') else None

    def post(path, data=None):
        import json as _json
        r = client.post(path, data=_json.dumps(data or {}), content_type='application/json')
        return r.status_code, r.get_json() if r.content_type and 'json' in (r.content_type or '') else None

    results = []
    passed = 0

    # Health
    code, data = get('/api/generator/test')
    ok = code == 200 and data and data.get('success') and 'database_available' in data
    results.append({'name': 'GET /api/generator/test', 'ok': ok, 'code': code})
    if ok:
        passed += 1

    # Jobs
    code, data = get('/api/generator/jobs?limit=5')
    ok = code == 200 and data and data.get('success') and 'jobs' in data
    results.append({'name': 'GET /api/generator/jobs', 'ok': ok, 'code': code})
    if ok:
        passed += 1

    # History
    code, data = get('/api/generator/history?user_id=debug&limit=5')
    ok = code == 200 and data and data.get('success') and 'history' in data
    results.append({'name': 'GET /api/generator/history', 'ok': ok, 'code': code})
    if ok:
        passed += 1

    # Statistics
    code, data = get('/api/generator/statistics?user_id=debug')
    ok = code == 200 and data and data.get('success') and 'statistics' in data
    results.append({'name': 'GET /api/generator/statistics', 'ok': ok, 'code': code})
    if ok:
        passed += 1

    # Performance
    code, data = get('/api/generator/performance?user_id=debug')
    ok = code == 200 and data and data.get('success') and 'performance' in data
    results.append({'name': 'GET /api/generator/performance', 'ok': ok, 'code': code})
    if ok:
        passed += 1

    if not quick:
        # Create
        code, data = post('/api/generator/create', {
            'title': 'Debug hard-test',
            'description': 'From /api/debug/hard-test-generator',
            'user_id': 'debug',
        })
        ok = code in (200, 201, 202) and data and data.get('success') and data.get('documentary_id')
        results.append({'name': 'POST /api/generator/create', 'ok': ok, 'code': code, 'doc_id': data.get('documentary_id') if data else None})
        if ok:
            passed += 1
        if not ok:
            results.append({'name': 'Documentary create→progress→video', 'ok': False, 'message': 'Create failed'})
        else:
            doc_id = data.get('documentary_id')
            import time as _time
            deadline = _time.monotonic() + min(poll_seconds, 60)
            while _time.monotonic() < deadline:
                code, prog = get(f'/api/documentary/progress/{doc_id}')
                if code != 200 or not prog or not prog.get('success'):
                    break
                st = prog.get('status')
                if st == 'completed':
                    code2, _ = get(f'/api/documentary/video/{doc_id}')
                    results.append({'name': 'Documentary create→progress→video', 'ok': True, 'doc_id': doc_id, 'video_status': code2})
                    passed += 1
                    break
                if st in ('failed', 'error'):
                    results.append({'name': 'Documentary create→progress→video', 'ok': True, 'doc_id': doc_id, 'status': st, 'error_message': prog.get('error_message') or prog.get('message')})
                    passed += 1
                    break
                _time.sleep(1.5)
            else:
                results.append({'name': 'Documentary create→progress→video', 'ok': False, 'message': 'Timeout'})

    total = len([r for r in results if 'ok' in r and isinstance(r.get('ok'), bool)])
    return {
        'success': True,
        'passed': passed,
        'failed': total - passed,
        'results': results,
        'quick': quick,
    }


@debug_bp.route('/api/debug/hard-test-generator', methods=['GET'])
def debug_hard_test_generator():
    """
    Run generator URL hard-tests (test, jobs, history, statistics, performance,
    and optionally create→progress→video). Same logic as scripts/hard_test_generator_urls.py.
    Query: run=1 to execute; quick=1 to skip documentary poll.
    """
    run = request.args.get('run') in ('1', 'true', 'yes')
    quick = request.args.get('quick') in ('1', 'true', 'yes')
    poll = min(120, max(10, int(request.args.get('poll', 60))))
    if not run:
        return jsonify({
            'success': True,
            'run': False,
            'description': 'Generator URL hard-tests (health, jobs, history, stats, create→video)',
            'usage': '?run=1 to execute; ?run=1&quick=1 to skip documentary; ?poll=60',
        })
    try:
        out = _run_hard_test_generator(quick=quick, poll_seconds=poll)
        return jsonify({**out, 'run': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'run': True,
            'error': str(e),
            'passed': 0,
            'failed': 0,
            'results': [],
        }), 500
