#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy battle.py to BOTH locations on server
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

LOCAL_FILE = "backend/routes/battle.py"
REMOTE_FILES = [
    "/var/www/html/backend/routes/battle.py",
    "/var/www/html/vidgenerator/backend/routes/battle.py",  # This is the one uWSGI uses!
]

def deploy_both_files():
    """Deploy to both locations"""
    try:
        # Read local file
        print("=" * 80)
        print("DEPLOYING BATTLE.PY TO BOTH LOCATIONS")
        print("=" * 80)
        print()
        
        if not os.path.exists(LOCAL_FILE):
            print(f"[ERROR] Local file not found: {LOCAL_FILE}")
            return False
        
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"[OK] Read local file: {len(file_content)} bytes")
        print()
        
        # Connect to server
        print("[1] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        sftp = ssh.open_sftp()
        
        # Deploy to both locations
        deployed = 0
        for remote_file in REMOTE_FILES:
            print(f"[2] Deploying to: {remote_file}")
            
            # Create backup
            try:
                stdin, stdout, stderr = ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true")
                stdout.read()
                print("  [OK] Backup created")
            except:
                pass
            
            # Create directory if needed
            remote_dir = os.path.dirname(remote_file)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir} 2>&1")
            stdout.read()
            
            # Write file
            try:
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(file_content)
                print(f"  [OK] File deployed")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        sftp.close()
        print()
        print(f"[SUMMARY] Deployed to {deployed}/{len(REMOTE_FILES)} locations")
        print()
        
        # Clear cache
        print("[3] Clearing Python cache...")
        cache_commands = [
            "find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html -type f -name 'battle.pyc' -delete 2>/dev/null || true",
        ]
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.read()
        print("  [OK] Cache cleared")
        print()
        
        # Restart uWSGI
        print("[4] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart uwsgi-vidgenerator 2>&1")
        restart_output = stdout.read().decode()
        restart_error = stderr.read().decode()
        if restart_output or restart_error:
            print(f"  Output: {restart_output[:200]}")
            if restart_error:
                print(f"  Error: {restart_error[:200]}")
        print("  [OK] Restart command sent")
        print()
        
        # Wait
        print("[5] Waiting for services to initialize...")
        time.sleep(10)
        print("  [OK] Wait complete")
        print()
        
        # Verify
        print("[6] Verifying syntax...")
        for remote_file in REMOTE_FILES:
            stdin, stdout, stderr = ssh.exec_command(f"python3 -m py_compile {remote_file} 2>&1")
            compile_error = stderr.read().decode()
            if compile_error:
                print(f"  [FAIL] {remote_file}: {compile_error[:200]}")
            else:
                print(f"  [OK] {remote_file} - No syntax errors")
        print()
        
        print("=" * 80)
        print("DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("Wait 15 seconds, then test:")
        print("  python test_all_battle_tabs.py")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_both_files()
    sys.exit(0 if success else 1)
