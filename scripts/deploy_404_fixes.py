#!/usr/bin/env python3
"""
Deploy 404 Fixes
Deploys fixes for missing shop currency and profile display endpoints
"""
import os
import sys
import paramiko
from pathlib import Path

# Configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
SERVER_BASE_PATH = '/var/www/html/vidgenerator'
LOCAL_BASE_PATH = Path(__file__).parent.parent

# Files to deploy
FILES_TO_DEPLOY = [
    'backend/routes/shop_routes.py',
    'backend/routes/user_profile_routes.py',
    'backend/register_blueprints.py'
]

def deploy_files():
    """Deploy files to server"""
    print("=" * 60)
    print("DEPLOYING 404 FIXES")
    print("=" * 60)
    
    try:
        # SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # SFTP connection
        sftp = ssh.open_sftp()
        
        deployed_count = 0
        for file_path in FILES_TO_DEPLOY:
            local_path = LOCAL_BASE_PATH / file_path
            remote_path = f"{SERVER_BASE_PATH}/{file_path}"
            
            if not local_path.exists():
                print(f"  [SKIP] {file_path} - not found locally")
                continue
            
            # Create remote directory if needed
            remote_dir = os.path.dirname(remote_path)
            ssh.exec_command(f"mkdir -p {remote_dir}")
            
            # Copy file
            sftp.put(str(local_path), remote_path)
            print(f"  [OK] Deployed {file_path}")
            deployed_count += 1
        
        sftp.close()
        
        print(f"\n  [SUMMARY] Deployed {deployed_count} files")
        
        # Restart services
        print("\n  [INFO] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
        ssh.exec_command("systemctl restart python-proxy", timeout=5)
        print("  [OK] Services restarted")
        
        ssh.close()
        
        print("\n  [COMPLETE] Deployment finished")
        print("  [NEXT] Test endpoints:")
        print("    - https://masternoder.dk/vidgenerator/api/shop/currency?user_id=default_user")
        print("    - https://masternoder.dk/vidgenerator/api/user/profile/default_user/display")
        
    except Exception as e:
        print(f"\n  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy_files()
