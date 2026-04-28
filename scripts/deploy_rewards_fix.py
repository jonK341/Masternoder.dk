#!/usr/bin/env python3
"""
Deploy Rewards System Fix
Deploys the fixed rewards_system_v2.py with _apply_gems_reward method
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy_fix():
    """Deploy rewards system fix"""
    print("="*80)
    print("DEPLOYING REWARDS SYSTEM FIX")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy file
        print("[1/4] Deploying rewards_system_v2.py...")
        sftp = ssh.open_sftp()
        
        local_file = "backend/services/rewards_system_v2.py"
        remote_file = "/var/www/html/backend/services/rewards_system_v2.py"
        
        with open(local_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with sftp.file(remote_file, 'w') as rf:
            rf.write(content)
        
        print(f"  [OK] {local_file} deployed")
        sftp.close()
        print()
        
        # Clear cache
        print("[2/4] Clearing cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[3/4] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(15)
        print("  [OK] Services restarted")
        print()
        
        # Verify
        print("[4/4] Verifying...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        status = stdout.read().decode().strip()
        if status == "active":
            print(f"  [OK] uwsgi-vidgenerator is ACTIVE")
        else:
            print(f"  [WARN] Status: {status}")
        
        print()
        print("="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy_fix()
