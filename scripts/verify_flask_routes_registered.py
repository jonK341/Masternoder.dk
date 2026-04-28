#!/usr/bin/env python3
"""
Verify Flask Routes Are Registered
Checks if routes are actually registered in the Flask app
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_routes_registered():
    """Verify routes are registered in Flask app"""
    print("="*70)
    print("VERIFYING FLASK ROUTES ARE REGISTERED")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test if we can create Flask app and list routes
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

try:
    from src.app import create_app
    app = create_app()
    
    print("Flask app created successfully")
    print()
    print("Registered Routes:")
    print("-" * 70)
    
    routes_found = []
    for rule in app.url_map.iter_rules():
        # Filter out internal Flask routes
        if rule.endpoint not in ['static', 'serve_static_files']:
            methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
            routes_found.append(f"{rule.rule} [{methods}] -> {rule.endpoint}")
    
    # Sort and display
    for route in sorted(routes_found):
        if any(keyword in route for keyword in ['unified-dashboard', 'monetization', 'agent', 'points', 'tech-tree']):
            print(f"  {route}")
    
    print()
    print(f"Total routes found: {len(routes_found)}")
    print()
    
    # Test specific routes
    test_routes = [
        '/api/unified-dashboard/data',
        '/vidgenerator/api/unified-dashboard/data',
        '/api/monetization/top50',
        '/vidgenerator/api/monetization/top50',
        '/api/agent/get-all',
        '/vidgenerator/api/agent/get-all',
        '/api/points/statistics',
        '/vidgenerator/api/points/statistics',
        '/api/tech-tree',
        '/vidgenerator/api/tech-tree',
    ]
    
    print("Testing route matching:")
    print("-" * 70)
    with app.test_request_context():
        from flask import url_for
        for route in test_routes:
            try:
                # Try to match the route
                adapter = app.url_map.bind('localhost')
                endpoint, args = adapter.match(route.split('?')[0])
                print(f"  [OK] {route} -> {endpoint}")
            except Exception as e:
                print(f"  [ERROR] {route} -> {str(e)[:80]}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(output)
        if error:
            print(f"\n[ERROR OUTPUT]\n{error}")
        
        print()
        print("="*70)
        print("ROUTE VERIFICATION COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_routes_registered()
