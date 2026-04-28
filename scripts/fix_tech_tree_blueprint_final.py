#!/usr/bin/env python3
"""
Fix Tech Tree Blueprint Final
Tries to import and register the blueprint directly to see the actual error
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_blueprint():
    """Fix blueprint"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Try to import and see the actual error
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

try:
    from backend.routes.tech_tree_routes import tech_tree_bp
    print("OK: Successfully imported tech_tree_bp")
    print(f"OK: Blueprint name: {tech_tree_bp.name}")
    
    # Check routes
    rules = list(tech_tree_bp.deferred_functions)
    print(f"OK: Found {len(rules)} deferred functions")
    
    # Try to see what routes would be registered
    from flask import Flask
    test_app = Flask(__name__)
    test_app.register_blueprint(tech_tree_bp)
    
    routes = [str(r) for r in test_app.url_map.iter_rules() if 'knowledge' in str(r)]
    if routes:
        print(f"OK: Found {len(routes)} knowledge routes:")
        for r in routes[:5]:
            print(f"  {r}")
    else:
        print("ERROR: No knowledge routes found")
        
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
'''
        
        print("[1/1] Testing blueprint import...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=120
        )
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        print(output)
        if error:
            print()
            print("STDERR:")
            print(error)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_blueprint()
