#!/usr/bin/env python3
"""
Restart uWSGI Safe
Safely restarts uWSGI with proper error handling
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_safe():
    """Restart uWSGI safely"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Clear cache
        print("[1/4] Clearing cache...")
        stdin, stdout, stderr = ssh.exec_command(
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo 'Done'",
            timeout=30
        )
        stdout.read()
        print("  [OK] Cache cleared")
        
        # Stop uWSGI
        print()
        print("[2/4] Stopping uWSGI...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "systemctl stop uwsgi-vidgenerator.service",
            timeout=30
        )
        stdout2.read()
        time.sleep(2)
        print("  [OK] Stopped")
        
        # Start uWSGI
        print()
        print("[3/4] Starting uWSGI...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "systemctl start uwsgi-vidgenerator.service",
            timeout=30
        )
        stdout3.read()
        time.sleep(5)
        print("  [OK] Started")
        
        # Check status
        print()
        print("[4/4] Checking status...")
        time.sleep(3)
        stdin4, stdout4, stderr4 = ssh.exec_command(
            "systemctl is-active uwsgi-vidgenerator.service",
            timeout=5
        )
        status = stdout4.read().decode().strip()
        print(f"  Status: {status}")
        
        if status == 'active':
            # Test a route
            print()
            print("Testing route...")
            time.sleep(2)
            stdin5, stdout5, stderr5 = ssh.exec_command(
                "curl -s -w '\\nHTTP_STATUS:%{http_code}' http://127.0.0.1:5000/api/monetization/top50?limit=6 2>&1 | head -3",
                timeout=10
            )
            response = stdout5.read().decode().strip()
            if 'HTTP_STATUS:200' in response:
                print("  ✅ Route test: 200")
            else:
                status_code = response.split('HTTP_STATUS:')[-1] if 'HTTP_STATUS:' in response else 'unknown'
                print(f"  ⚠️  Route test: {status_code}")
        
        print()
        print("="*70)
        print("RESTART COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    restart_safe()
