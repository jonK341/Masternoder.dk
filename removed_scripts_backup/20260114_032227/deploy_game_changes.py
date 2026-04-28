#!/usr/bin/env python3
"""
Deploy only game.py changes to server
"""
import paramiko
import os
from pathlib import Path

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def deploy_game_file():
    """Deploy backend/routes/game.py to server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Deploying Game Changes")
        print("=" * 60)
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        print()
        
        # Create SFTP client
        sftp = ssh_client.open_sftp()
        
        # Files to deploy
        files_to_deploy = [
            ("backend/routes/game.py", f"{REMOTE_PATH}/backend/routes/game.py"),
            ("vidgenerator/game/index.html", f"{REMOTE_PATH}/vidgenerator/game/index.html"),
            ("vidgenerator/static/css/modern-design-system.css", f"{REMOTE_PATH}/vidgenerator/static/css/modern-design-system.css"),
        ]
        
        for local_file, remote_file in files_to_deploy:
            if not os.path.exists(local_file):
                print(f"[SKIP] {local_file} - File not found")
                continue
                
            print(f"Uploading {local_file}...")
            
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_file)
            stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
            stdout.channel.recv_exit_status()
            
            # Upload file
            sftp.put(local_file, remote_file)
            print(f"[OK] Uploaded {local_file} -> {remote_file}")
        
        sftp.close()
        
        print()
        print("=" * 60)
        print("[OK] Deployment Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()
    
    return True

if __name__ == '__main__':
    success = deploy_game_file()
    exit(0 if success else 1)

