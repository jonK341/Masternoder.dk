#!/usr/bin/env python3
"""
Verify and Restart Comprehensive
Verifies routes are correct and restarts services
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_and_restart():
    """Verify and restart"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # 1. Clear Python cache
        print("[1/5] Clearing Python cache...")
        stdin, stdout, stderr = ssh.exec_command(
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo 'Cache cleared'",
            timeout=30
        )
        stdout.read()
        print("  [OK] Cache cleared")
        
        # 2. Verify route file has correct decorators
        print()
        print("[2/5] Verifying route file...")
        route_file = "/var/www/html/vidgenerator/backend/routes/monetization_top50_routes.py"
        stdin2, stdout2, stderr2 = ssh.exec_command(
            f"grep -c '@monetization_top50_bp.route.*top50' {route_file}",
            timeout=5
        )
        route_count = stdout2.read().decode().strip()
        if route_count and int(route_count) > 0:
            print(f"  [OK] Found {route_count} route decorators")
        else:
            print("  [WARN] No route decorators found - file may need updating")
        
        # 3. Restart uWSGI
        print()
        print("[3/5] Restarting uWSGI...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "systemctl restart uwsgi-vidgenerator.service",
            timeout=30
        )
        stdout3.read()
        print("  [OK] uWSGI restarted")
        
        # 4. Wait for uWSGI to start
        print()
        print("[4/5] Waiting for uWSGI to start...")
        time.sleep(5)
        stdin4, stdout4, stderr4 = ssh.exec_command(
            "systemctl is-active uwsgi-vidgenerator.service",
            timeout=5
        )
        status = stdout4.read().decode().strip()
        if status == 'active':
            print("  [OK] uWSGI is active")
        else:
            print(f"  [WARN] uWSGI status: {status}")
        
        # 5. Test route
        print()
        print("[5/5] Testing route...")
        time.sleep(2)
        stdin5, stdout5, stderr5 = ssh.exec_command(
            "curl -s -w '\\nHTTP_STATUS:%{http_code}' http://127.0.0.1:5000/api/monetization/top50?limit=6 2>&1 | head -5",
            timeout=10
        )
        response = stdout5.read().decode().strip()
        if 'HTTP_STATUS:200' in response:
            print("  [OK] Route returns 200")
        elif 'HTTP_STATUS:404' in response:
            print("  [ERROR] Route still returns 404")
        else:
            print(f"  [WARN] Response: {response[:100]}")
        
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
    verify_and_restart()
