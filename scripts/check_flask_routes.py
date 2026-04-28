#!/usr/bin/env python3
"""
Check Flask Routes
Simple script to check if routes are registered
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_routes():
    """Check Flask routes"""
    print("="*70)
    print("CHECKING FLASK ROUTES")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected")
        print()
        
        # Create a simple Python script to check routes
        python_code = '''
import sys
sys.path.insert(0, "/var/www/html")
try:
    from src.app import create_app
    app = create_app()
    print("APP CREATED SUCCESSFULLY")
    print()
    
    # List all routes
    api_routes = []
    static_routes = []
    for rule in app.url_map.iter_rules():
        route_str = f"{rule.rule} [{', '.join(sorted(rule.methods))}]"
        if "/api/" in rule.rule or "/vidgenerator/api/" in rule.rule:
            api_routes.append(route_str)
        elif "/static/" in rule.rule or "static" in rule.rule.lower():
            static_routes.append(route_str)
    
    print(f"API ROUTES ({len(api_routes)}):")
    for route in sorted(api_routes)[:20]:
        print(f"  {route}")
    print()
    print(f"STATIC ROUTES ({len(static_routes)}):")
    for route in sorted(static_routes)[:10]:
        print(f"  {route}")
        
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
'''
        
        # Write script to temp file
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{python_code}\nENDPYTHON",
            timeout=30
        )
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output:
            print(output)
        if error:
            print(f"\nERRORS:\n{error}")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_routes()
