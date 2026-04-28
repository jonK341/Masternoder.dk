#!/usr/bin/env python3
"""
Hard Reset uWSGI
Force stops and restarts uWSGI service
"""
import paramiko
import os
import sys
import time
from datetime import datetime

# Fix Windows console encoding issues (systemctl output contains unicode bullets)
if os.name == 'nt':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def hard_reset_uwsgi():
    """Hard reset uWSGI service"""
    print("="*80)
    print("HARD RESET uWSGI SERVICE")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Check current status
        print("[2/6] Checking current status...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator 2>&1 | head -5", timeout=5)
        status_output = stdout.read().decode()
        print(f"  Current status:\n{status_output}")
        print()
        
        # Force stop
        print("[3/6] Force stopping uWSGI...")
        ssh.exec_command("systemctl stop uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(3)
        
        # Kill any remaining processes
        print("  Killing any remaining uWSGI processes...")
        ssh.exec_command("pkill -9 -f uwsgi 2>&1 || true", timeout=5)
        time.sleep(2)
        
        # Verify stopped
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        status = stdout.read().decode().strip()
        if status == "inactive" or "inactive" in status.lower():
            print("  [OK] uWSGI stopped")
        else:
            print(f"  [WARN] Status: {status}")
        print()
        
        # Clear cache
        print("[4/6] Clearing Python cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Start service
        print("[5/6] Starting uWSGI service...")
        ssh.exec_command("systemctl start uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(5)
        print("  [OK] Start command executed")
        print()
        
        # Wait and verify
        print("[6/6] Verifying service status...")
        time.sleep(10)  # Wait for service to fully start
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        status = stdout.read().decode().strip()
        
        if status == "active":
            print(f"  [OK] uWSGI is ACTIVE")
        else:
            print(f"  [WARN] uWSGI status: {status}")
            # Check logs
            print("  Checking logs...")
            stdin, stdout, stderr = ssh.exec_command("journalctl -u uwsgi-vidgenerator -n 20 --no-pager 2>&1", timeout=5)
            logs = stdout.read().decode()
            print(f"  Recent logs:\n{logs[-500:]}")
        
        # Get detailed status
        print()
        print("  Detailed status:")
        stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator 2>&1 | head -15", timeout=5)
        detailed_status = stdout.read().decode()
        print(detailed_status)
        
        print()
        print("="*80)
        print("HARD RESET COMPLETE")
        print("="*80)
        print(f"Final status: {status}")
        print()
        
        ssh.close()
        return status == "active"
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = hard_reset_uwsgi()
    sys.exit(0 if success else 1)
