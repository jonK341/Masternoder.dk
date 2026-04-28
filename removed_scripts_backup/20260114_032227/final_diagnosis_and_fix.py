"""
Final Diagnosis - Find Why Routes Don't Appear Despite Registration
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def final_diagnosis():
    """Final diagnosis"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
        
        print("="*60)
        print("FINAL DIAGNOSIS - WHY ROUTES DON'T APPEAR")
        print("="*60)
        
        # Create a test that directly queries the running app
        print("\n[DIAGNOSIS] Testing if routes exist but are hidden...")
        
        # Test 1: Check if routes exist with different URL patterns
        test_urls = [
            "/api/game-mechanics/subjects?user_id=test",
            "/vidgenerator/api/game-mechanics/subjects?user_id=test",
            "/game-mechanics/subjects?user_id=test",
        ]
        
        for url in test_urls:
            stdin, stdout, stderr = ssh.exec_command(f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' 'https://masternoder.dk{url}' 2>&1")
            output = stdout.read().decode('utf-8', errors='ignore')
            if "HTTP_CODE:200" in output:
                print(f"  [SUCCESS] {url} - Works!")
                break
            else:
                print(f"  [FAIL] {url}")
        
        # Test 2: Check if there's a middleware stripping routes
        print("\n[DIAGNOSIS] Checking for middleware issues...")
        stdin, stdout, stderr = ssh.exec_command("grep -r 'ApplicationRootMiddleware\\|strip.*vidgenerator' /var/www/html/vidgenerator/src/*.py 2>/dev/null | head -5")
        middleware = stdout.read().decode('utf-8', errors='ignore')
        if middleware.strip():
            print("  Found middleware:")
            print(f"  {middleware}")
        
        # Test 3: Create a minimal test route to see if ANY new routes work
        print("\n[TEST] Creating minimal test route to verify route registration works...")
        test_route_code = '''
from flask import Blueprint, jsonify
test_bp = Blueprint('test_route_debug', __name__, url_prefix='/api/test-debug')

@test_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "pong", "message": "Test route works"})
'''
        # Add this to register_blueprints temporarily
        stdin, stdout, stderr = ssh.exec_command("cat /var/www/html/vidgenerator/backend/register_blueprints.py | tail -5")
        end_of_file = stdout.read().decode('utf-8', errors='ignore')
        
        # Add test route registration at the end
        test_registration = '''
    # TEST ROUTE - Debug
    try:
        from flask import Blueprint, jsonify
        test_bp = Blueprint('test_route_debug', __name__, url_prefix='/api/test-debug')
        @test_bp.route('/ping', methods=['GET'])
        def ping():
            return jsonify({"status": "pong"})
        app.register_blueprint(test_bp)
        _safe_print("  [OK] Registered test_route_debug blueprint")
    except Exception as e:
        _safe_print(f"  [ERROR] Test route failed: {e}")
'''
        
        # Append test registration before the final return
        stdin, stdout, stderr = ssh.exec_command("sed -i '/return registered_count/i\\" + test_registration.replace('\n', '\\n') + "' /var/www/html/vidgenerator/backend/register_blueprints.py 2>&1 || echo 'Failed'")
        result = stdout.read().decode('utf-8', errors='ignore')
        print(f"  {result}")
        
        # Restart and test
        print("\n[RESTART] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi")
        stdout.channel.recv_exit_status()
        time.sleep(8)
        
        # Test the test route
        print("\n[TEST] Testing test route...")
        stdin, stdout, stderr = ssh.exec_command("curl -s 'https://masternoder.dk/vidgenerator/api/test-debug/ping'")
        test_output = stdout.read().decode('utf-8', errors='ignore')
        if "pong" in test_output:
            print(f"  [SUCCESS] Test route works: {test_output}")
            print("  [INFO] This means route registration works, but Game Mechanics has a specific issue")
        else:
            print(f"  [FAIL] Test route failed: {test_output[:200]}")
            print("  [INFO] This means route registration itself has an issue")
        
        # Final check: Compare with Ultra Resource which works
        print("\n[COMPARE] Comparing with Ultra Resource (which works)...")
        stdin, stdout, stderr = ssh.exec_command("grep -A 5 'Ultra Resource Controller Routes' /var/www/html/vidgenerator/backend/register_blueprints.py | head -10")
        ultra_code = stdout.read().decode('utf-8', errors='ignore')
        print("  Ultra Resource registration:")
        print(f"  {ultra_code}")
        
        stdin, stdout, stderr = ssh.exec_command("grep -A 5 'Unified Game Mechanics Routes' /var/www/html/vidgenerator/backend/register_blueprints.py | head -10")
        gm_code = stdout.read().decode('utf-8', errors='ignore')
        print("\n  Game Mechanics registration:")
        print(f"  {gm_code}")
        
        ssh.close()
        
        print("\n" + "="*60)
        print("DIAGNOSIS COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_diagnosis()

