"""
Create test script on server to check routes
"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

TEST_SCRIPT = '''#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/html')

try:
    from backend.routes.game import game_bp
    print(f"OK: game_bp imported: {game_bp.name}")
    
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(game_bp)
    
    all_routes = list(app.url_map.iter_rules())
    print(f"OK: Total routes: {len(all_routes)}")
    
    stats_routes = [r for r in all_routes if 'stats' in r.rule]
    print(f"OK: Stats routes: {len(stats_routes)}")
    
    if stats_routes:
        for route in stats_routes:
            methods = list(route.methods - {'HEAD', 'OPTIONS'})
            print(f"  {methods} {route.rule}")
    else:
        print("ERROR: No stats routes found")
        for route in all_routes[:10]:
            methods = list(route.methods - {'HEAD', 'OPTIONS'})
            print(f"  {methods} {route.rule}")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

def create_test():
    """Create and run test on server"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        
        # Write test file
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/test_game_routes.py', 'w') as f:
            f.write(TEST_SCRIPT)
        sftp.close()
        
        # Make executable and run
        stdin, stdout, stderr = ssh.exec_command('chmod +x /tmp/test_game_routes.py && python3 /tmp/test_game_routes.py')
        result = stdout.read().decode('utf-8', errors='replace')
        errors = stderr.read().decode('utf-8', errors='replace')
        
        print(result)
        if errors:
            print("\n[ERROR]")
            print(errors)
        
        # Cleanup
        ssh.exec_command('rm -f /tmp/test_game_routes.py')
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test()

