#!/usr/bin/env python3
"""
Final Restart and Verify
Restarts uWSGI and verifies all routes work
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_and_verify():
    """Restart and verify"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Clear cache
        print("[1/6] Clearing Python cache...")
        stdin, stdout, stderr = ssh.exec_command(
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo 'Done'",
            timeout=30
        )
        stdout.read()
        print("  [OK] Cache cleared")
        
        # Restart uWSGI (non-blocking)
        print()
        print("[2/6] Restarting uWSGI...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "systemctl restart uwsgi-vidgenerator.service",
            timeout=30
        )
        # Don't wait for output - just start the restart
        print("  [OK] Restart command sent")
        
        # Wait for restart
        print()
        print("[3/6] Waiting for uWSGI to restart...")
        time.sleep(10)
        
        # Check status
        print()
        print("[4/6] Checking uWSGI status...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "systemctl is-active uwsgi-vidgenerator.service",
            timeout=5
        )
        status = stdout3.read().decode().strip()
        print(f"  Status: {status}")
        
        # Verify routes are registered
        print()
        print("[5/6] Verifying routes are registered...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html/vidgenerator")

from src.app import create_app

app = create_app()

routes_to_check = [
    '/api/monetization/top50',
    '/api/monetization/cash',
    '/api/tech-tree/knowledge',
    '/api/agent/get-all',
    '/api/points/statistics',
    '/api/points/calculator/predict',
]

print("Checking routes...")
for route in routes_to_check:
    found = False
    for rule in app.url_map.iter_rules():
        if route in str(rule):
            found = True
            print(f"  ✅ {route}")
            break
    if not found:
        print(f"  ❌ {route} NOT FOUND")
'''
        
        stdin4, stdout4, stderr4 = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout4.read().decode().strip()
        if output:
            print(output)
        
        # Test routes via HTTP
        print()
        print("[6/6] Testing routes via HTTP...")
        test_routes = [
            ("/api/monetization/top50?limit=6", "monetization/top50"),
            ("/api/monetization/cash?user_id=test", "monetization/cash"),
            ("/api/tech-tree/knowledge?user_id=test", "tech-tree/knowledge"),
            ("/api/agent/get-all?user_id=test", "agent/get-all"),
            ("/api/points/statistics?user_id=test&days=30", "points/statistics"),
            ("/api/points/calculator/predict?user_id=test&activity_type=general&base_points=100&days=7", "points/calculator/predict"),
        ]
        
        for route, name in test_routes:
            url = f"http://127.0.0.1:5000{route}"
            stdin5, stdout5, stderr5 = ssh.exec_command(
                f"curl -s -w '\\nHTTP_STATUS:%{{http_code}}' {url} 2>&1 | head -3",
                timeout=10
            )
            response = stdout5.read().decode().strip()
            if 'HTTP_STATUS:200' in response:
                print(f"  ✅ {name}: 200")
            elif 'HTTP_STATUS:404' in response:
                print(f"  ❌ {name}: 404")
            else:
                status = response.split('HTTP_STATUS:')[-1] if 'HTTP_STATUS:' in response else 'unknown'
                print(f"  ⚠️  {name}: {status}")
        
        print()
        print("="*70)
        print("RESTART AND VERIFICATION COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    restart_and_verify()
