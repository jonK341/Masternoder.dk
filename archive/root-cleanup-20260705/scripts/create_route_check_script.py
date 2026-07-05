"""
Create and run route check script on server
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SCRIPT_CONTENT = '''import sys
sys.path.insert(0, '/var/www/html')

from flask import Flask
app = Flask(__name__)

try:
    from backend.routes.game import game_bp
    app.register_blueprint(game_bp)
    
    # Check for comprehensive route
    comprehensive_routes = [r for r in app.url_map.iter_rules() if 'comprehensive' in r.rule]
    print(f"Found {len(comprehensive_routes)} comprehensive routes")
    for r in comprehensive_routes:
        methods = list(r.methods - {'HEAD', 'OPTIONS'})
        print(f"  {methods} {r.rule}")
    
    # Check for test-simple route
    test_routes = [r for r in app.url_map.iter_rules() if 'test-simple' in r.rule]
    print(f"\\nFound {len(test_routes)} test-simple routes")
    for r in test_routes:
        methods = list(r.methods - {'HEAD', 'OPTIONS'})
        print(f"  {methods} {r.rule}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''

def create_and_run():
    """Create script and run it"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        
        # Write script
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/route_check.py', 'w') as f:
            f.write(SCRIPT_CONTENT)
        sftp.close()
        
        # Run it
        stdin, stdout, stderr = ssh.exec_command('python3 /tmp/route_check.py')
        result = stdout.read().decode('utf-8', errors='replace')
        errors = stderr.read().decode('utf-8', errors='replace')
        
        print(result)
        if errors:
            print("\nStderr:")
            print(errors)
        
        # Cleanup
        ssh.exec_command('rm -f /tmp/route_check.py')
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_and_run()

