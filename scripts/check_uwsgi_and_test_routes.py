#!/usr/bin/env python3
"""
Check uWSGI and Test Routes
Checks uwsgi config and tests routes directly
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_uwsgi():
    """Check uwsgi and test routes"""
    print("="*70)
    print("CHECKING UWSGI AND TESTING ROUTES")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check uwsgi.ini
        print("[1/4] Checking uwsgi.ini configuration...")
        uwsgi_ini_paths = [
            "/var/www/html/vidgenerator/uwsgi.ini",
            "/var/www/html/uwsgi.ini",
        ]
        
        for ini_path in uwsgi_ini_paths:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"test -f {ini_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
                result = stdout.read().decode().strip()
                if result == 'EXISTS':
                    print(f"  [OK] Found: {ini_path}")
                    # Read key parts
                    stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -E 'socket|module|callable|chdir' {ini_path} 2>&1 | head -10", timeout=5)
                    config = stdout2.read().decode().strip()
                    if config:
                        print("  Configuration:")
                        for line in config.split('\n'):
                            print(f"    {line}")
            except Exception as e:
                pass
        print()
        
        # Check uwsgi process
        print("[2/4] Checking uwsgi process...")
        try:
            stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | head -3", timeout=5)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n'):
                    if line.strip():
                        print(f"  {line[:100]}")
            else:
                print("  [WARN] No uwsgi process found")
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
        
        # Test routes using Python requests directly to Flask
        print("[3/4] Testing routes directly to Flask (bypassing nginx)...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")

from src.app import create_app

app = create_app()
with app.test_client() as client:
    test_routes = [
        "/api/unified-dashboard/data?user_id=test_user_1",
        "/api/monetization/top50?limit=6",
        "/api/agent/get-all?user_id=test_user_1",
        "/api/points/statistics?user_id=test_user_1&days=30",
        "/api/tech-tree?user_id=test_user_1",
    ]
    
    for route in test_routes:
        try:
            response = client.get(route)
            status = response.status_code
            if status == 200:
                print(f"  [OK] {route[:50]}... -> 200")
            else:
                print(f"  [ERROR] {route[:50]}... -> {status}")
        except Exception as e:
            print(f"  [ERROR] {route[:50]}... -> {str(e)[:50]}")
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=60
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(output)
        if error and "Traceback" not in error:
            print(f"\n[ERROR OUTPUT]\n{error}")
        print()
        
        # Check nginx proxy_pass configuration
        print("[4/4] Checking nginx proxy_pass configuration...")
        try:
            stdin, stdout, stderr = ssh.exec_command("grep -A 10 'location /vidgenerator/' /etc/nginx/sites-enabled/masternoder.dk | grep -E 'proxy_pass|rewrite'", timeout=10)
            output = stdout.read().decode().strip()
            if output:
                print("  Nginx proxy configuration:")
                for line in output.split('\n'):
                    print(f"    {line}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        print()
        print("="*70)
        print("UWSGI AND ROUTE CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_uwsgi()
