#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy game.py to server
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

LOCAL_FILE = "backend/routes/game.py"
REMOTE_FILES = [
    "/var/www/html/backend/routes/game.py",
    "/var/www/html/vidgenerator/backend/routes/game.py",
]

def deploy():
    """Deploy game.py"""
    try:
        print("=" * 80)
        print("DEPLOYING GAME.PY")
        print("=" * 80)
        print()
        
        if not os.path.exists(LOCAL_FILE):
            print(f"[ERROR] Local file not found: {LOCAL_FILE}")
            return False
        
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"[OK] Read local file: {len(file_content)} bytes")
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected")
        print()
        
        sftp = ssh.open_sftp()
        deployed = 0
        
        for remote_file in REMOTE_FILES:
            print(f"Deploying to: {remote_file}")
            remote_dir = os.path.dirname(remote_file)
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1")
            ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true")
            
            with sftp.file(remote_file, 'w') as rf:
                rf.write(file_content)
            
            print(f"  [OK] Deployed")
            deployed += 1
        
        sftp.close()
        print()
        print(f"Deployed to {deployed}/{len(REMOTE_FILES)} locations")
        print()
        
        # Clear cache and restart
        print("Clearing cache and restarting...")
        ssh.exec_command("find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        ssh.exec_command("find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true")
        ssh.exec_command("sudo systemctl restart uwsgi-vidgenerator 2>&1")
        time.sleep(10)
        print("[OK] Done")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
