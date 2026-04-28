#!/usr/bin/env python3
"""
Check Running App Routes
Checks what routes are registered in the running Flask app
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_routes():
    """Check routes in running app"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Use Python to connect to the running Flask app via uWSGI
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

# Try to get the Flask app from uWSGI
try:
    import uwsgi
    from uwsgidecorators import *
    
    @timer(1, target='spooler')
    def check_routes(signum):
        # This won't work directly, need different approach
        pass
except:
    pass

# Instead, let's check if we can import and see registered routes
# by checking the app module directly
try:
    # Import the app factory
    from src.app import create_app
    
    # Create app instance (same as uWSGI would)
    app = create_app()
    
    # Check for specific routes
    target_routes = [
        '/api/monetization/top50',
        '/api/monetization/cash',
        '/api/tech-tree/knowledge',
        '/api/agent/get-all',
        '/api/agent/recommendations',
        '/api/points/statistics',
        '/api/points/calculator/predict',
    ]
    
    print("Checking if routes are registered in app...")
    print()
    
    registered_routes = []
    for rule in app.url_map.iter_rules():
        registered_routes.append(str(rule))
    
    for target in target_routes:
        found = False
        for route in registered_routes:
            if target in route:
                found = True
                print(f"  [OK] {target:<40} -> {route[:60]}")
                break
        if not found:
            print(f"  [ERROR] {target:<40} NOT FOUND")
            # Show similar routes
            similar = [r for r in registered_routes if 'monetization' in r or 'agent' in r or 'points' in r or 'tech-tree' in r]
            if similar:
                print(f"    Similar routes found:")
                for s in similar[:3]:
                    print(f"      {s[:80]}")
    
except Exception as e:
    print(f"Error: {e}")
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
        if error and "Traceback" in error:
            print(f"\n[ERROR OUTPUT]\n{error[:500]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_routes()
