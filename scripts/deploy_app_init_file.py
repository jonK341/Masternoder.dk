#!/usr/bin/env python3
"""
Deploy App Init File
Creates the src/app directory and deploys __init__.py to the server
"""
import paramiko
import os
from scp import SCPClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html"
APP_INIT_PATH = f"{SERVER_BASE}/src/app/__init__.py"
APP_DIR = f"{SERVER_BASE}/src/app"

def deploy_app_init():
    """Deploy app/__init__.py to server"""
    print("=" * 70)
    print("DEPLOYING APP INIT FILE")
    print("=" * 70)
    print()
    
    local_file = os.path.join(BASE_DIR, 'src/app/__init__.py')
    
    if not os.path.exists(local_file):
        print(f"  [ERROR] Local file not found: {local_file}")
        return
    
    print(f"Local file: {local_file}")
    print(f"Remote path: {APP_INIT_PATH}")
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Create directory structure
        print("[1/3] Creating directory structure...")
        commands = [
            f"mkdir -p {APP_DIR}",
            f"chmod 755 {SERVER_BASE}/src",
            f"chmod 755 {APP_DIR}",
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            stdout.read()
            print(f"  [OK] {cmd}")
        
        print()
        
        # Deploy file
        print("[2/3] Deploying __init__.py file...")
        sftp = ssh.open_sftp()
        
        try:
            sftp.put(local_file, APP_INIT_PATH)
            sftp.chmod(APP_INIT_PATH, 0o644)
            print(f"  [OK] File deployed to: {APP_INIT_PATH}")
        except Exception as e:
            print(f"  [ERROR] Could not deploy file: {e}")
            sftp.close()
            ssh.close()
            return
        
        sftp.close()
        print()
        
        # Verify file exists
        print("[3/3] Verifying deployment...")
        cmd = f"test -f {APP_INIT_PATH} && echo 'EXISTS' || echo 'NOT FOUND'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        result = stdout.read().decode('utf-8').strip()
        
        if result == 'EXISTS':
            print(f"  [OK] File verified: {APP_INIT_PATH}")
            
            # Check file size
            cmd2 = f"wc -l {APP_INIT_PATH} | awk '{{print $1}}'"
            stdin, stdout, stderr = ssh.exec_command(cmd2, timeout=10)
            line_count = stdout.read().decode('utf-8').strip()
            print(f"  [OK] File has {line_count} lines")
            
            # Check for key content
            cmd3 = f"grep -q 'register_auto_fix_middleware' {APP_INIT_PATH} && echo 'FOUND' || echo 'NOT FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd3, timeout=10)
            middleware_check = stdout.read().decode('utf-8').strip()
            
            if middleware_check == 'FOUND':
                print(f"  [OK] Auto-fix middleware registration found in file")
            else:
                print(f"  [WARN] Auto-fix middleware registration not found")
        else:
            print(f"  [ERROR] File not found after deployment!")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Restart uwsgi-vidgenerator service")
        print("  2. Restart python-proxy service")
        print("  3. Test auto-fix system")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_app_init()
