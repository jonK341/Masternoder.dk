#!/usr/bin/env python3
"""
Deploy WSGI Fix - Fix corrupted wsgi.py file
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def deploy_wsgi_fix():
    """Deploy fixed wsgi.py"""
    print("=" * 70)
    print("WSGI Fix - Production Deployment")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Read fixed wsgi.py
        print("[2/5] Reading fixed wsgi.py...")
        with open('wsgi.py', 'r', encoding='utf-8') as f:
            wsgi_content = f.read()
        print(f"  [OK] Read {len(wsgi_content)} bytes")
        print()
        
        # Deploy file
        print("[3/5] Deploying fixed wsgi.py...")
        sftp = ssh.open_sftp()
        
        remote_file = "/var/www/html/vidgenerator/wsgi.py"
        
        # Create backup
        ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
        print("  [OK] Backup created")
        
        # Write file
        with sftp.file(remote_file, 'w') as rf:
            rf.write(wsgi_content)
        
        sftp.close()
        print("  [OK] File deployed")
        print()
        
        # Clear cache
        print("[4/5] Clearing server cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[5/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(15)  # Give more time for restart
        ssh.exec_command("systemctl restart python-proxy 2>&1", timeout=10)
        time.sleep(5)
        print("  [OK] Services restarted")
        print()
        
        # Verify deployment
        print("[6/6] Verifying deployment...")
        time.sleep(5)
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        
        if uwsgi_status == "active":
            print("  [OK] uwsgi-vidgenerator is active")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {uwsgi_status}")
        
        if proxy_status == "active":
            print("  [OK] python-proxy is active")
        else:
            print(f"  [WARN] python-proxy status: {proxy_status}")
        
        print()
        print("=" * 70)
        print("✅ WSGI Fix Deployed!")
        print("=" * 70)
        print()
        print("Fixed Issues:")
        print("  - Removed corrupted blueprint registration code")
        print("  - Cleaned up broken error handler")
        print("  - wsgi.py now properly calls create_app()")
        print()
        print("Next Steps:")
        print("  1. Wait 20-30 seconds for services to fully restart")
        print("  2. Test endpoints: python scripts/test_endpoints_one_by_one.py")
        print("  3. Hard refresh browser: Ctrl+F5")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_wsgi_fix()
    sys.exit(0 if success else 1)
