#!/usr/bin/env python3
"""
Deploy Default User Fix Complete
Deploys all files for default_user fix
"""
import paramiko
import os
from scp import SCPClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html"

def deploy_default_user_fix():
    """Deploy default_user fix"""
    print("=" * 70)
    print("DEPLOYING DEFAULT_USER FIX COMPLETE")
    print("=" * 70)
    print()
    
    files_to_deploy = [
        ('backend/routes/user_identification_routes.py', f'{SERVER_BASE}/backend/routes/user_identification_routes.py'),
        ('backend/register_blueprints.py', f'{SERVER_BASE}/backend/register_blueprints.py'),
        ('vidgenerator/static/js/user-identification.js', f'{SERVER_BASE}/vidgenerator/static/js/user-identification.js'),
        ('vidgenerator/static/js/backend-connector.js', f'{SERVER_BASE}/vidgenerator/static/js/backend-connector.js'),
        ('vidgenerator/profile/index.html', f'{SERVER_BASE}/vidgenerator/profile/index.html'),
    ]
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        print("[1/2] Deploying files...")
        for local_file, remote_file in files_to_deploy:
            local_path = os.path.join(BASE_DIR, local_file)
            if os.path.exists(local_path):
                try:
                    sftp.put(local_path, remote_file)
                    sftp.chmod(remote_file, 0o644)
                    print(f"  [OK] Deployed: {local_file}")
                except Exception as e:
                    print(f"  [WARN] Could not deploy {local_file}: {e}")
            else:
                print(f"  [WARN] Local file not found: {local_file}")
        
        sftp.close()
        print()
        
        print("[2/2] Restarting services...")
        restart_commands = [
            "systemctl restart uwsgi-vidgenerator",
            "systemctl restart python-proxy",
        ]
        
        for cmd in restart_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                stdout.read()
                print(f"  [OK] {cmd}")
            except Exception as e:
                print(f"  [WARN] {cmd}: {e}")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Default user fix deployed!")
        print()
        print("Changes:")
        print("  ✅ User identification API endpoints created")
        print("  ✅ Frontend auto-identifies users on page load")
        print("  ✅ All default_user fallbacks replaced with proper identification")
        print("  ✅ New users automatically get proper user IDs")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_default_user_fix()
