#!/usr/bin/env python3
"""
Verify and Restart Production Script
Verifies files are on server and restarts services
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_and_restart():
    """Verify files and restart services"""
    print("="*70)
    print("VERIFYING FILES AND RESTARTING PRODUCTION")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check if critical files exist
        print("[1/4] Verifying critical files exist...")
        critical_files = [
            "/var/www/html/src/app.py",
            "/var/www/html/backend/routes/unified_dashboard_routes.py",
            "/var/www/html/backend/routes/monetization_top50_routes.py",
            "/var/www/html/backend/routes/agent_routes.py",
            "/var/www/html/backend/routes/unified_points.py",
            "/var/www/html/backend/routes/point_analytics_routes.py",
            "/var/www/html/backend/routes/point_calculator_routes.py",
            "/var/www/html/backend/routes/tech_tree_routes.py",
            "/var/www/html/vidgenerator/static/css/modern-design-system.css",
            "/var/www/html/vidgenerator/static/js/navigation-toolbar.js",
        ]
        
        for file_path in critical_files:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            result = stdout.read().decode().strip()
            if result == 'EXISTS':
                print(f"  [OK] {file_path.split('/')[-1]}")
            else:
                print(f"  [ERROR] {file_path.split('/')[-1]} - FILE MISSING!")
        print()
        
        # Check Flask app can import routes
        print("[2/4] Testing Flask route imports...")
        test_script = '''
import sys
sys.path.insert(0, "/var/www/html")
try:
    from backend.routes.unified_dashboard_routes import unified_dashboard_bp
    from backend.routes.monetization_top50_routes import monetization_top50_bp
    from backend.routes.agent_routes import agent_bp
    print("SUCCESS: All route blueprints imported")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''
        
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 << 'ENDPYTHON'\n{test_script}\nENDPYTHON",
            timeout=30
        )
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if output:
            print(f"  {output}")
        if error:
            print(f"  [ERROR] {error}")
        print()
        
        # Restart uwsgi service
        print("[3/4] Restarting uwsgi service...")
        try:
            stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=30)
            stdout.read()  # Wait for command to complete
            print("  [OK] uwsgi service restarted")
        except Exception as e:
            print(f"  [ERROR] Could not restart uwsgi: {e}")
        print()
        
        # Wait for service to start
        print("[4/4] Waiting for service to start...")
        import time
        time.sleep(5)
        
        # Check service status
        try:
            stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
            status = stdout.read().decode().strip()
            if status == "active":
                print("  [OK] uwsgi service is active")
            else:
                print(f"  [WARN] uwsgi service status: {status}")
        except Exception as e:
            print(f"  [WARN] Could not check status: {e}")
        
        print()
        print("="*70)
        print("VERIFICATION AND RESTART COMPLETE")
        print("="*70)
        print()
        print("Next steps:")
        print("  1. Wait 10 seconds for Flask to fully start")
        print("  2. Test URL: https://masternoder.dk/vidgenerator/unified_dashboard")
        print("  3. Hard refresh browser (Ctrl+F5)")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_and_restart()
