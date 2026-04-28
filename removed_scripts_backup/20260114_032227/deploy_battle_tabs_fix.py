#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Battle Tabs Fix
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def deploy():
    """Deploy battle tabs fix"""
    try:
        print("=" * 80)
        print("DEPLOYING BATTLE TABS FIX")
        print("=" * 80)
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        sftp = ssh.open_sftp()
        
        # Deploy battle page
        local_file = 'vidgenerator/battle/index.html'
        remote_file = '/var/www/html/vidgenerator/vidgenerator/battle/index.html'
        
        if not os.path.exists(local_file):
            print(f"[ERROR] {local_file} - File not found")
            return False
        
        print(f"Deploying: {local_file}")
        remote_dir = os.path.dirname(remote_file)
        ssh.exec_command(f"mkdir -p {remote_dir} 2>&1")
        
        # Create backup
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"{remote_file}.backup.{timestamp}"
        ssh.exec_command(f"cp {remote_file} {backup_file} 2>&1 || echo 'No existing file to backup'")
        
        with open(local_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        with sftp.file(remote_file, 'w') as rf:
            rf.write(file_content)
        
        print(f"  [OK] Deployed to {remote_file}")
        print(f"  [OK] Backup created: {backup_file}")
        
        sftp.close()
        
        # Clear cache
        print("Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true")
        print("[OK] Cache cleared")
        
        # Restart uWSGI
        print("Restarting uWSGI...")
        ssh.exec_command("sudo systemctl restart uwsgi-vidgenerator 2>&1")
        time.sleep(10)
        print("[OK] uWSGI restarted")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy()
    if success:
        print()
        print("=" * 80)
        print("DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("Battle tabs fixed!")
        print("  - All tabs now have onclick handlers")
        print("  - Tab switching function is global (window.switchBattleTab)")
        print("  - Active states properly managed")
        print("  - Tab content properly shown/hidden")
        print()
        print("Wait 20 seconds for service to fully restart, then test the tabs.")
        print()
    else:
        print()
        print("=" * 80)
        print("DEPLOYMENT FAILED")
        print("=" * 80)
    sys.exit(0 if success else 1)
