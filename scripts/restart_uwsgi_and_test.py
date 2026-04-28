#!/usr/bin/env python3
"""
Restart uWSGI and Test
Restarts uWSGI and tests all routes
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def restart_and_test():
    """Restart and test"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Clear cache
        print("[1/4] Clearing Python cache...")
        stdin, stdout, stderr = ssh.exec_command(
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo 'Done'",
            timeout=30
        )
        stdout.read()
        print("  [OK] Cache cleared")
        
        # Restart uWSGI
        print()
        print("[2/4] Restarting uWSGI...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "systemctl restart uwsgi-vidgenerator.service && echo 'Restarted'",
            timeout=30
        )
        result = stdout2.read().decode().strip()
        print(f"  {result}")
        
        # Wait for startup
        print()
        print("[3/4] Waiting for uWSGI to start...")
        time.sleep(8)
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "systemctl is-active uwsgi-vidgenerator.service",
            timeout=5
        )
        status = stdout3.read().decode().strip()
        print(f"  Status: {status}")
        
        # Test routes
        print()
        print("[4/4] Testing routes...")
        test_routes = [
            ("/api/monetization/top50?limit=6", "monetization/top50"),
            ("/api/monetization/cash?user_id=test", "monetization/cash"),
            ("/api/tech-tree/knowledge?user_id=test", "tech-tree/knowledge"),
            ("/api/agent/get-all?user_id=test", "agent/get-all"),
            ("/api/points/statistics?user_id=test&days=30", "points/statistics"),
        ]
        
        for route, name in test_routes:
            url = f"http://127.0.0.1:5000{route}"
            stdin4, stdout4, stderr4 = ssh.exec_command(
                f"curl -s -w '\\nHTTP_STATUS:%{{http_code}}' {url} 2>&1 | head -3",
                timeout=10
            )
            response = stdout4.read().decode().strip()
            if 'HTTP_STATUS:200' in response:
                print(f"  ✅ {name}: 200")
            elif 'HTTP_STATUS:404' in response:
                print(f"  ❌ {name}: 404")
            else:
                status = response.split('HTTP_STATUS:')[-1] if 'HTTP_STATUS:' in response else 'unknown'
                print(f"  ⚠️  {name}: {status}")
        
        print()
        print("="*70)
        print("RESTART AND TEST COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    restart_and_test()
