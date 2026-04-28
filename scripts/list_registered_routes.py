#!/usr/bin/env python3
"""
List Registered Routes
Lists all registered Flask routes on the server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def list_routes():
    """List all registered routes"""
    print("="*70)
    print("LISTING REGISTERED FLASK ROUTES")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # List routes using Flask app
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

from src.app import create_app

app = create_app()
with app.app_context():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    
    # Filter for API routes we care about
    api_routes = [r for r in routes if 'api' in r['path'].lower() or 'unified' in r['path'].lower() or 'monetization' in r['path'].lower() or 'tech-tree' in r['path'].lower() or 'agent' in r['path'].lower() or 'points' in r['path'].lower()]
    
    print(f"Total routes: {len(routes)}")
    print(f"API-related routes: {len(api_routes)}")
    print()
    print("API Routes:")
    for route in sorted(api_routes, key=lambda x: x['path']):
        methods = ', '.join([m for m in route['methods'] if m != 'HEAD' and m != 'OPTIONS'])
        print(f"  {route['path']:<60} [{methods}]")
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(output)
        if error and "Traceback" in error:
            print(f"\n[ERROR OUTPUT]\n{error}")
        
        print()
        print("="*70)
        print("ROUTE LISTING COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    list_routes()
