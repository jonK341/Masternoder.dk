#!/usr/bin/env python3
"""
Hard Reset Web Services - Complete reset of all web services and caches
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def hard_reset():
    """Perform hard reset of all web services"""
    print("=" * 70)
    print("HARD RESET: WEB SERVICES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect
        print("[1/7] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Step 1: Stop all services
        print("[2/7] Stopping all services...")
        services = ['uwsgi-vidgenerator', 'python-proxy', 'nginx']
        for service in services:
            print(f"  Stopping {service}...")
            ssh.exec_command(f"systemctl stop {service} > /dev/null 2>&1 &", timeout=5)
            time.sleep(2)
        print("  [OK] All services stopped")
        time.sleep(3)
        print()
        
        # Step 2: Kill any remaining processes
        print("[3/7] Killing remaining processes...")
        kill_commands = [
            "pkill -9 -f 'uwsgi.*vidgenerator' 2>/dev/null || true",
            "pkill -9 -f 'python.*run.py' 2>/dev/null || true",
            "pkill -9 -f 'python.*proxy' 2>/dev/null || true",
        ]
        for cmd in kill_commands:
            ssh.exec_command(cmd, timeout=5)
        time.sleep(2)
        print("  [OK] Processes killed")
        print()
        
        # Step 3: Clear Python cache
        print("[4/7] Clearing Python cache...")
        cache_commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyo' -delete 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.py~' -delete 2>/dev/null || true",
        ]
        for cmd in cache_commands:
            ssh.exec_command(cmd, timeout=30)
        print("  [OK] Python cache cleared")
        print()
        
        # Step 4: Clear nginx cache
        print("[5/7] Clearing nginx cache...")
        nginx_commands = [
            "rm -rf /var/cache/nginx/* 2>/dev/null || true",
            "rm -rf /var/lib/nginx/cache/* 2>/dev/null || true",
            "rm -rf /tmp/nginx_* 2>/dev/null || true",
        ]
        for cmd in nginx_commands:
            ssh.exec_command(cmd, timeout=10)
        print("  [OK] Nginx cache cleared")
        print()
        
        # Step 5: Clear temporary files
        print("[6/7] Clearing temporary files...")
        temp_commands = [
            "rm -rf /tmp/uwsgi_* 2>/dev/null || true",
            "rm -rf /tmp/.uwsgi_* 2>/dev/null || true",
            "find /tmp -name '*.sock' -type f -delete 2>/dev/null || true",
        ]
        for cmd in temp_commands:
            ssh.exec_command(cmd, timeout=10)
        print("  [OK] Temporary files cleared")
        print()
        
        # Step 6: Test nginx configuration
        print("[7/7] Testing and starting services...")
        
        # Test nginx config
        stdin, stdout, stderr = ssh.exec_command("nginx -t 2>&1", timeout=10)
        nginx_test = stdout.read().decode()
        if "syntax is ok" in nginx_test.lower():
            print("  [OK] Nginx configuration is valid")
        else:
            print(f"  [WARN] Nginx config test: {nginx_test[:100]}")
        
        time.sleep(2)
        
        # Start nginx
        print("  Starting nginx...")
        ssh.exec_command("systemctl start nginx > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        
        # Start uwsgi
        print("  Starting uwsgi-vidgenerator...")
        ssh.exec_command("systemctl start uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        
        # Start python-proxy
        print("  Starting python-proxy...")
        ssh.exec_command("systemctl start python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        
        print("  [OK] All services started")
        print()
        
        # Verify services
        print("Verifying services...")
        time.sleep(10)  # Give services time to fully start
        
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service}", timeout=5)
            status = stdout.read().decode().strip()
            if status == 'active':
                print(f"  [OK] {service}: active")
            else:
                print(f"  [WARN] {service}: {status}")
        
        print()
        print("=" * 70)
        print("HARD RESET COMPLETE")
        print("=" * 70)
        print()
        print("Services Status:")
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service}", timeout=5)
            status = stdout.read().decode().strip()
            print(f"  {service}: {status}")
        print()
        print("Next Steps:")
        print("  1. Wait 15-20 seconds for services to fully initialize")
        print("  2. Clear your browser cache completely (Ctrl+Shift+Delete)")
        print("  3. Or use incognito/private window")
        print("  4. Test profile page: https://masternoder.dk/vidgenerator/profile")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Hard reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = hard_reset()
    sys.exit(0 if success else 1)
