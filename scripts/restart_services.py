#!/usr/bin/env python3
"""
Restart Services - Turn services off and on
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
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Stop services
        print("[2/6] Stopping services...")
        
        # Stop uwsgi-vidgenerator
        print("  Stopping uwsgi-vidgenerator...")
        ssh.exec_command("systemctl stop uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        print("  [OK] uwsgi-vidgenerator stop command sent")
        
        # Stop python-proxy
        print("  Stopping python-proxy...")
        ssh.exec_command("systemctl stop python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        print("  [OK] python-proxy stop command sent")
        
        print()
        
        # Verify stopped
        print("[3/6] Verifying services are stopped...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        
        if uwsgi_status == "inactive":
            print("  [OK] uwsgi-vidgenerator is inactive")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {uwsgi_status}")
        
        if proxy_status == "inactive":
            print("  [OK] python-proxy is inactive")
        else:
            print(f"  [WARN] python-proxy status: {proxy_status}")
        
        print()
        
        # Wait a moment
        print("[4/6] Waiting 5 seconds...")
        time.sleep(5)
        print("  [OK] Wait complete")
        print()
        
        # Start services
        print("[5/6] Starting services...")
        
        # Start uwsgi-vidgenerator
        print("  Starting uwsgi-vidgenerator...")
        ssh.exec_command("systemctl start uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        print("  [OK] uwsgi-vidgenerator start command sent")
        
        # Start python-proxy
        print("  Starting python-proxy...")
        ssh.exec_command("systemctl start python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        print("  [OK] python-proxy start command sent")
        
        print()
        
        # Verify started
        print("[6/6] Verifying services are running...")
        time.sleep(5)  # Give services time to start
        
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
        
        # Get service status details
        print()
        print("Service Status Details:")
        print("  uwsgi-vidgenerator:")
        stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator --no-pager | head -5", timeout=5)
        status = stdout.read().decode().strip()
        for line in status.split('\n'):
            if line.strip():
                print(f"    {line}")
        
        print("  python-proxy:")
        stdin, stdout, stderr = ssh.exec_command("systemctl status python-proxy --no-pager | head -5", timeout=5)
        status = stdout.read().decode().strip()
        for line in status.split('\n'):
            if line.strip():
                print(f"    {line}")
        
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
        print("  3. Check logs if issues persist")
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
