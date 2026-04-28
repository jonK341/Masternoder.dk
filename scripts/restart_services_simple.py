#!/usr/bin/env python3
"""
Restart Services - Simple restart
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_services():
    """Restart all services"""
    print("=" * 70)
    print("Service Restart - Production")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Restart services
        print("[2/4] Restarting services...")
        
        # Restart uwsgi-vidgenerator
        print("  Restarting uwsgi-vidgenerator...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
        print("  [OK] Restart command sent")
        
        # Restart python-proxy
        print("  Restarting python-proxy...")
        ssh.exec_command("systemctl restart python-proxy", timeout=5)
        print("  [OK] Restart command sent")
        
        print()
        
        # Wait for services to restart
        print("[3/4] Waiting for services to restart (15 seconds)...")
        time.sleep(15)
        print("  [OK] Wait complete")
        print()
        
        # Verify services
        print("[4/4] Verifying services...")
        
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
        print("✅ Services Restarted!")
        print("=" * 70)
        print()
        print("Services Status:")
        print(f"  uwsgi-vidgenerator: {uwsgi_status}")
        print(f"  python-proxy: {proxy_status}")
        print()
        print("Next Steps:")
        print("  1. Wait 10-15 seconds for services to fully initialize")
        print("  2. Test endpoints: python scripts/test_all_endpoints.py")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Restart failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = restart_services()
    sys.exit(0 if success else 1)
