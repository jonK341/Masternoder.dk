#!/usr/bin/env python3
"""
Verify Routes Script
Tests if routes are actually accessible on the server
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_routes():
    """Verify routes are accessible"""
    print("="*70)
    print("VERIFYING ROUTES AND STATIC FILES")
    print("="*70)
    print()
    
    try:
        # Connect
        print("[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check if static files exist
        print("[2/4] Checking static files exist...")
        static_files = [
            "/var/www/html/vidgenerator/static/css/modern-design-system.css",
            "/var/www/html/vidgenerator/static/css/navigation-toolbar.css",
            "/var/www/html/vidgenerator/static/js/navigation-toolbar.js",
            "/var/www/html/vidgenerator/static/js/comprehensive-auto-save.js",
            "/var/www/html/vidgenerator/static/js/enhanced-frontpage-stats.js",
            "/var/www/html/vidgenerator/static/js/top50-monetization-frame.js",
            "/var/www/html/vidgenerator/static/js/energy-regeneration-timers.js",
        ]
        
        for file_path in static_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            result = stdout.read().decode().strip()
            if result == 'EXISTS':
                print(f"  [OK] {file_path.split('/')[-1]}")
            else:
                print(f"  [ERROR] {file_path.split('/')[-1]} - FILE MISSING!")
        print()
        
        # Check Flask logs for blueprint registration
        print("[3/4] Checking Flask application logs...")
        log_files = [
            "/var/log/uwsgi/app/vidgenerator.log",
            "/var/log/uwsgi/vidgenerator.log",
            "/var/www/html/logs/app.log",
        ]
        
        for log_file in log_files:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"test -f {log_file} && tail -50 {log_file} | grep -i 'blueprint\\|route\\|registered' | tail -10", timeout=5)
                output = stdout.read().decode().strip()
                if output:
                    print(f"  [OK] Found logs in {log_file}")
                    print(f"  {output[:200]}...")
                else:
                    print(f"  [INFO] No blueprint logs in {log_file}")
            except:
                pass
        print()
        
        # Test if we can curl the routes
        print("[4/4] Testing route accessibility...")
        test_routes = [
            ("/vidgenerator/api/unified-dashboard/data?user_id=test", "unified-dashboard/data"),
            ("/vidgenerator/api/monetization/top50?limit=6", "monetization/top50"),
            ("/vidgenerator/api/monetization/cash?user_id=test", "monetization/cash"),
            ("/vidgenerator/api/tech-tree/knowledge?user_id=test", "tech-tree/knowledge"),
            ("/vidgenerator/api/agent/get-all?user_id=test", "agent/get-all"),
            ("/vidgenerator/api/points/statistics?user_id=test", "points/statistics"),
            ("/vidgenerator/static/css/modern-design-system.css", "static/css/modern-design-system.css"),
        ]
        
        for route, name in test_routes:
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost{route} 2>&1",
                    timeout=10
                )
                status = stdout.read().decode().strip()
                if status == "200":
                    print(f"  [OK] {name}: 200")
                elif status == "404":
                    print(f"  [ERROR] {name}: 404 - Route not found")
                elif status == "500":
                    print(f"  [WARN] {name}: 500 - Server error")
                else:
                    print(f"  [INFO] {name}: {status}")
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
        
        print()
        print("="*70)
        print("VERIFICATION COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_routes()
    sys.exit(0 if success else 1)
