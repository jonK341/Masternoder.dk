#!/usr/bin/env python3
"""
Comprehensive Nginx Route Test
Tests all routes through nginx to identify bottlenecks
"""
import paramiko
import os
import requests
import time
from urllib.parse import urljoin

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_URL = "https://masternoder.dk"

def test_route(url, method='GET', timeout=10):
    """Test a single route"""
    try:
        start = time.time()
        if method == 'GET':
            response = requests.get(url, timeout=timeout, verify=False, allow_redirects=False)
        else:
            response = requests.post(url, timeout=timeout, verify=False, allow_redirects=False)
        elapsed = time.time() - start
        
        status = response.status_code
        size = len(response.content)
        content_type = response.headers.get('Content-Type', 'unknown')
        
        # Check if it's JSON
        is_json = False
        try:
            if 'application/json' in content_type:
                data = response.json()
                is_json = True
        except:
            pass
        
        return {
            'url': url,
            'status': status,
            'time': round(elapsed * 1000, 2),  # ms
            'size': size,
            'content_type': content_type,
            'is_json': is_json,
            'success': 200 <= status < 400
        }
    except requests.exceptions.Timeout:
        return {'url': url, 'status': 'TIMEOUT', 'time': timeout * 1000, 'success': False}
    except Exception as e:
        return {'url': url, 'status': 'ERROR', 'error': str(e), 'success': False}

def get_nginx_config():
    """Get nginx configuration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Get nginx config
        stdin, stdout, stderr = ssh.exec_command(
            "cat /etc/nginx/sites-available/masternoder.dk 2>/dev/null || cat /etc/nginx/nginx.conf | grep -A 100 'server {'",
            timeout=10
        )
        config = stdout.read().decode('utf-8', errors='ignore')
        ssh.close()
        return config
    except Exception as e:
        return f"Error getting config: {e}"

def get_all_flask_routes():
    """Get all Flask routes from server"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")
from src.app import create_app
app = create_app()
routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        routes.append({
            'rule': str(rule),
            'methods': list(rule.methods),
            'endpoint': rule.endpoint
        })
import json
print(json.dumps(routes))
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        ssh.close()
        
        # Filter out startup logs
        lines = output.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('[') or line.strip().startswith('{'):
                json_start = i
                break
        
        if json_start is not None:
            json_output = '\n'.join(lines[json_start:])
            try:
                import json
                return json.loads(json_output)
            except:
                pass
        
        return []
    except Exception as e:
        print(f"Error getting Flask routes: {e}")
        return []

def main():
    """Main test function"""
    print("="*80)
    print("COMPREHENSIVE NGINX ROUTE TEST")
    print("="*80)
    print()
    
    # Get nginx config
    print("[1/4] Getting nginx configuration...")
    nginx_config = get_nginx_config()
    print(f"  Config length: {len(nginx_config)} chars")
    print()
    
    # Get Flask routes
    print("[2/4] Getting Flask routes...")
    flask_routes = get_all_flask_routes()
    print(f"  Found {len(flask_routes)} Flask routes")
    print()
    
    # Define critical routes to test
    critical_routes = [
        # Unified Dashboard
        '/vidgenerator/unified_dashboard',
        '/vidgenerator/unified_dashboard/',
        '/vidgenerator/api/unified-dashboard/data',
        
        # Leaderboards
        '/vidgenerator/leaderboards',
        '/vidgenerator/api/leaderboard/all',
        '/vidgenerator/api/leaderboard/stats',
        
        # API Routes
        '/vidgenerator/api/monetization/top50',
        '/vidgenerator/api/monetization/cash',
        '/vidgenerator/api/tech-tree/knowledge',
        '/vidgenerator/api/tech-tree',
        '/vidgenerator/api/agent/get-all',
        '/vidgenerator/api/agent/recommendations',
        '/vidgenerator/api/points/statistics',
        '/vidgenerator/api/points/calculator/predict',
        '/vidgenerator/api/points/history/analytics',
        
        # Static files
        '/vidgenerator/static/css/modern-design-system.css',
        '/vidgenerator/static/css/navigation-toolbar.css',
        '/vidgenerator/static/js/navigation-toolbar.js',
        '/vidgenerator/static/js/comprehensive-auto-save.js',
        
        # Main pages
        '/vidgenerator/',
        '/vidgenerator/index.html',
        '/vidgenerator/battle',
        '/vidgenerator/gallery',
        
        # Health check
        '/vidgenerator/api/health',
        '/health',
    ]
    
    print("[3/4] Testing critical routes...")
    print()
    
    results = []
    for route in critical_routes:
        url = urljoin(BASE_URL, route)
        print(f"  Testing: {route}")
        result = test_route(url)
        results.append(result)
        
        if result.get('success'):
            print(f"    ✅ {result['status']} - {result['time']}ms - {result['size']} bytes")
        else:
            print(f"    ❌ {result.get('status', 'ERROR')} - {result.get('time', 0)}ms")
        time.sleep(0.1)  # Small delay between requests
    
    print()
    print("[4/4] Analyzing results...")
    print()
    
    # Summary
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total routes tested: {len(results)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    print()
    
    if successful:
        avg_time = sum(r['time'] for r in successful if 'time' in r) / len(successful)
        max_time = max((r['time'] for r in successful if 'time' in r), default=0)
        print(f"Average response time: {avg_time:.2f}ms")
        print(f"Max response time: {max_time:.2f}ms")
        print()
    
    if failed:
        print("FAILED ROUTES:")
        for r in failed:
            print(f"  ❌ {r['url']} - {r.get('status', 'ERROR')}")
        print()
    
    # Check for bottlenecks (slow routes)
    slow_routes = [r for r in successful if 'time' in r and r['time'] > 1000]
    if slow_routes:
        print("SLOW ROUTES (>1000ms):")
        for r in sorted(slow_routes, key=lambda x: x.get('time', 0), reverse=True):
            print(f"  ⚠️  {r['url']} - {r['time']}ms")
        print()
    
    # Check nginx config for issues
    print("NGINX CONFIGURATION ANALYSIS:")
    if 'location /vidgenerator' in nginx_config:
        print("  ✅ /vidgenerator location block found")
    else:
        print("  ❌ /vidgenerator location block NOT found")
    
    if 'proxy_pass' in nginx_config:
        print("  ✅ proxy_pass directive found")
        # Count proxy_pass directives
        proxy_count = nginx_config.count('proxy_pass')
        print(f"  Found {proxy_count} proxy_pass directives")
    else:
        print("  ❌ proxy_pass directive NOT found")
    
    if 'location ~ \\.(css|js|png|jpg|jpeg|gif|ico|svg)' in nginx_config:
        print("  ✅ Static file location block found")
    else:
        print("  ⚠️  Static file location block may be missing")
    
    print()
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()
