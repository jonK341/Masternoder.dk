#!/usr/bin/env python3
"""
Test Production Routes Script
Tests routes directly on the production server
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def test_production_routes():
    """Test routes on production server"""
    print("="*70)
    print("TESTING PRODUCTION ROUTES")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Test routes using curl
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
        
        print("Testing routes on production server...")
        for route, name in test_routes:
            try:
                # Use curl to test the route
                cmd = f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost{route} 2>&1"
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
        
        # Check if Flask app is running
        print("Checking Flask application status...")
        try:
            stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator 2>&1 | head -5", timeout=5)
            output = stdout.read().decode().strip()
            if output:
                print(f"  {output}")
        except Exception as e:
            print(f"  [WARN] Could not check uwsgi status: {e}")
        
        print()
        
        # Check Flask logs for errors
        print("Checking Flask application logs (last 20 lines)...")
        log_files = [
            "/var/log/uwsgi/app/vidgenerator.log",
            "/var/log/uwsgi/vidgenerator.log",
        ]
        
        for log_file in log_files:
            try:
                stdin, stdout, stderr = ssh.exec_command(f"tail -20 {log_file} 2>&1", timeout=5)
                output = stdout.read().decode().strip()
                if output and 'No such file' not in output:
                    print(f"  [INFO] {log_file}:")
                    for line in output.split('\n')[-10:]:
                        if line.strip():
                            print(f"    {line[:100]}")
            except Exception as e:
                pass
        
        print()
        print("="*70)
        print("PRODUCTION ROUTE TEST COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_production_routes()
