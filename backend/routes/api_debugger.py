"""
API Debugger - Test all API endpoints and fix method issues
"""
from flask import Blueprint, jsonify, render_template, request, current_app
from datetime import datetime

api_debugger_bp = Blueprint('api_debugger', __name__)

def test_endpoint_with_client(path, method='GET', data=None):
    """Test an API endpoint using Flask test client"""
    try:
        with current_app.test_client() as client:
            if method == 'GET':
                response = client.get(path)
            elif method == 'POST':
                response = client.post(path, json=data or {}, content_type='application/json')
            elif method == 'PUT':
                response = client.put(path, json=data or {}, content_type='application/json')
            elif method == 'DELETE':
                response = client.delete(path)
            else:
                return {'error': f'Unsupported method: {method}'}
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'method': method,
                'path': path,
                'content_type': response.content_type,
                'is_json': 'application/json' in response.content_type,
                'response_preview': response.get_data(as_text=True)[:500] if response.data else '',
                'error': None
            }
    except Exception as e:
        return {
            'success': False,
            'status_code': None,
            'method': method,
            'path': path,
            'error': str(e),
            'response_preview': ''
        }

@api_debugger_bp.route('/api/debugger', methods=['GET'], strict_slashes=False)
@api_debugger_bp.route('/vidgenerator/api/debugger', methods=['GET'], strict_slashes=False)
def api_debugger_page():
    """API Debugger HTML page"""
    try:
        return render_template('api_debugger.html')
    except Exception as e:
        # Log error but still return fallback
        import logging
        logging.error(f"Error rendering api_debugger.html: {e}")
        # Fallback HTML if template doesn't exist
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Debugger - MasterNoder</title>
            <style>
                body { font-family: monospace; background: #0a0a0a; color: #00ff00; padding: 20px; }
                h1 { color: #00ffff; }
                .endpoint { margin: 10px 0; padding: 15px; background: rgba(0,255,0,0.1); border-left: 3px solid #00ff00; }
                .method { color: #ffff00; font-weight: bold; }
                .status-ok { color: #00ff00; }
                .status-error { color: #ff0000; }
                .btn { padding: 10px 20px; background: #00ff00; color: #000; border: none; cursor: pointer; margin: 5px; }
                .btn:hover { background: #00cc00; }
                .result { margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.5); }
            </style>
        </head>
        <body>
            <h1>🔍 API Debugger</h1>
            <p>Testing all API endpoints...</p>
            <div id="results"></div>
            <button class="btn" onclick="runAllTests()">Run All Tests</button>
            <script>
                async function testEndpoint(url, method='GET') {
                    try {
                        const options = { method: method };
                        if (method === 'POST' || method === 'PUT') {
                            options.headers = { 'Content-Type': 'application/json' };
                            options.body = JSON.stringify({});
                        }
                        const response = await fetch(url, options);
                        return {
                            success: response.ok,
                            status: response.status,
                            method: method,
                            url: url
                        };
                    } catch (e) {
                        return { success: false, error: e.message, method: method, url: url };
                    }
                }
                
                async function runAllTests() {
                    const results = document.getElementById('results');
                    results.innerHTML = '<p>Testing...</p>';
                    
                    const endpoints = [
                        { url: '/api/status', methods: ['GET'] },
                        { url: '/api/fix/create-all-missing-files', methods: ['GET', 'POST'] },
                        { url: '/api/generator/debug', methods: ['GET'] },
                        { url: '/api/generator/check-processes', methods: ['GET'] },
                        { url: '/api/generator/check-uwsgi', methods: ['GET'] },
                        { url: '/api/generator/restart-uwsgi', methods: ['POST'] },
                        { url: '/api/documentary/generate', methods: ['POST'] },
                        { url: '/api/themes/all', methods: ['GET'] },
                        { url: '/api/defense/calculate', methods: ['POST'] },
                        { url: '/api/game/sync', methods: ['POST'] }
                    ];
                    
                    let html = '';
                    for (const ep of endpoints) {
                        for (const method of ep.methods) {
                            const result = await testEndpoint(ep.url, method);
                            const statusClass = result.success ? 'status-ok' : 'status-error';
                            html += `<div class="endpoint">
                                <span class="method">${method}</span> ${ep.url}
                                <span class="${statusClass}">Status: ${result.status || 'ERROR'}</span>
                            </div>`;
                        }
                    }
                    results.innerHTML = html;
                }
                
                // Auto-run on load
                window.addEventListener('load', () => runAllTests());
            </script>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html; charset=utf-8'}

@api_debugger_bp.route('/api/debugger/test', methods=['GET', 'POST'], strict_slashes=False)
@api_debugger_bp.route('/vidgenerator/api/debugger/test', methods=['GET', 'POST'], strict_slashes=False)
def test_api_endpoints():
    """Test all API endpoints and return results"""
    from flask import current_app
    
    # Get all registered routes
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint != 'static' and '/api/' in rule.rule:
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                'path': rule.rule
            })
    
    # Test endpoints
    results = []
    test_urls = [
        {'url': '/api/status', 'methods': ['GET']},
        {'url': '/api/status/html', 'methods': ['GET']},
        {'url': '/api/fix/create-all-missing-files', 'methods': ['GET', 'POST']},
        {'url': '/api/generator/debug', 'methods': ['GET']},
        {'url': '/api/generator/check-processes', 'methods': ['GET']},
        {'url': '/api/generator/check-uploads', 'methods': ['GET']},
        {'url': '/api/generator/check-uwsgi', 'methods': ['GET']},
        {'url': '/api/generator/restart-uwsgi', 'methods': ['POST']},
        {'url': '/api/generator/test-endpoint', 'methods': ['GET']},
        {'url': '/api/generator/test-file-access', 'methods': ['GET']},
        {'url': '/api/documentary/generate', 'methods': ['POST']},
        {'url': '/api/themes/all', 'methods': ['GET']},
        {'url': '/api/defense/calculate', 'methods': ['POST']},
        {'url': '/api/defense/enemies', 'methods': ['GET']},
        {'url': '/api/game/sync', 'methods': ['POST']},
        {'url': '/api/game/hunters-enhanced/start', 'methods': ['POST']},
    ]
    
    for test in test_urls:
        for method in test['methods']:
            # Test both with and without /vidgenerator prefix
            for prefix in ['', '/vidgenerator']:
                full_path = prefix + test['url']
                result = test_endpoint_with_client(full_path, method)
                result['expected_method'] = method
                result['tested_path'] = full_path
                results.append(result)
    
    # Find routes that match each endpoint
    endpoint_analysis = {}
    for test in test_urls:
        endpoint_analysis[test['url']] = {
            'expected_methods': test['methods'],
            'registered_routes': [r for r in routes if test['url'] in r['path']],
            'test_results': [r for r in results if test['url'] in r.get('url', '')]
        }
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(results),
        'passed': len([r for r in results if r.get('success')]),
        'failed': len([r for r in results if not r.get('success')]),
        'endpoint_analysis': endpoint_analysis,
        'all_results': results,
        'registered_routes': routes,
        'message': 'API endpoint testing complete. Check endpoint_analysis for method mismatches.'
    })

@api_debugger_bp.route('/api/debugger/fix-links', methods=['GET'], strict_slashes=False)
@api_debugger_bp.route('/vidgenerator/api/debugger/fix-links', methods=['GET'], strict_slashes=False)
def get_fixed_links():
    """Return corrected quick links with proper HTTP methods"""
    return jsonify({
        'success': True,
        'quick_links': [
            {'url': '/api/status', 'method': 'GET', 'label': 'API Status (JSON)'},
            {'url': '/api/status/html', 'method': 'GET', 'label': 'API Status (HTML)'},
            {'url': '/api/fix/create-all-missing-files', 'method': 'POST', 'label': 'Create Missing Files', 'note': 'Also accepts GET'},
            {'url': '/api/generator/debug', 'method': 'GET', 'label': 'Generator Debug'},
            {'url': '/api/generator/check-processes', 'method': 'GET', 'label': 'Check Processes'},
            {'url': '/api/generator/check-uwsgi', 'method': 'GET', 'label': 'Check uWSGI'},
            {'url': '/api/generator/restart-uwsgi', 'method': 'POST', 'label': 'Restart uWSGI', 'note': 'POST only'},
            {'url': '/api/documentary/generate', 'method': 'POST', 'label': 'Generate Documentary', 'note': 'POST only'},
            {'url': '/api/themes/all', 'method': 'GET', 'label': 'All Themes'},
            {'url': '/api/defense/calculate', 'method': 'POST', 'label': 'Calculate Defense', 'note': 'POST only'},
            {'url': '/api/game/sync', 'method': 'POST', 'label': 'Game Sync', 'note': 'POST only'},
        ]
    })

