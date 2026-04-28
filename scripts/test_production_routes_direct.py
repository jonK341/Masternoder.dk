#!/usr/bin/env python3
"""
Test Production Routes Directly
Tests routes directly using curl on the server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_routes_direct():
    """Test routes directly on server"""
    print("="*70)
    print("TESTING PRODUCTION ROUTES DIRECTLY")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test routes using curl through uwsgi socket
        test_routes = [
            ("/vidgenerator/api/unified-dashboard/data?user_id=test_user_1", "unified-dashboard/data"),
            ("/vidgenerator/api/monetization/top50?limit=6", "monetization/top50"),
            ("/vidgenerator/api/monetization/cash?user_id=test_user_1", "monetization/cash"),
            ("/vidgenerator/api/tech-tree/knowledge?user_id=test_user_1", "tech-tree/knowledge"),
            ("/vidgenerator/api/agent/get-all?user_id=test_user_1", "agent/get-all"),
            ("/vidgenerator/api/points/statistics?user_id=test_user_1&days=30", "points/statistics"),
            ("/vidgenerator/static/css/modern-design-system.css", "static/css/modern-design-system.css"),
            ("/vidgenerator/static/js/navigation-toolbar.js", "static/js/navigation-toolbar.js"),
        ]
        
        print("Testing routes through uwsgi...")
        for route, name in test_routes:
            try:
                # Use curl to test through uwsgi socket
                cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --unix-socket /run/uwsgi/app/vidgenerator/socket http://localhost{route} 2>&1 | head -1"
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                status = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                if status == "200":
                    print(f"  [OK] {name}: 200")
                elif status == "404":
                    print(f"  [ERROR] {name}: 404 - Route not found")
                elif status == "500":
                    print(f"  [ERROR] {name}: 500 - Server error")
                else:
                    print(f"  [WARN] {name}: {status}")
                    if error:
                        print(f"    Error: {error[:100]}")
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
        
        print()
        
        # Check if static files exist
        print("Checking if static files exist...")
        static_files = [
            "/var/www/html/vidgenerator/static/css/modern-design-system.css",
            "/var/www/html/vidgenerator/static/css/navigation-toolbar.css",
            "/var/www/html/vidgenerator/static/js/navigation-toolbar.js",
            "/var/www/html/vidgenerator/static/js/comprehensive-auto-save.js",
        ]
        
        for file_path in static_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            result = stdout.read().decode().strip()
            if result == 'EXISTS':
                print(f"  [OK] {file_path.split('/')[-1]}")
            else:
                print(f"  [ERROR] {file_path.split('/')[-1]} - FILE MISSING!")
        
        print()
        print("="*70)
        print("DIRECT ROUTE TEST COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_routes_direct()
