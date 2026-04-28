#!/usr/bin/env python3
"""Deploy game HTML file"""
import paramiko
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def deploy_game_html():
    """Deploy vidgenerator/game/index.html"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Deploying Game HTML")
        print("=" * 70)
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        
        sftp = ssh_client.open_sftp()
        
        local_file = "vidgenerator/game/index.html"
        remote_file = f"{REMOTE_PATH}/vidgenerator/game/index.html"
        
        # Ensure directory exists
        remote_dir = os.path.dirname(remote_file)
        stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
        stdout.channel.recv_exit_status()
        
        print(f"Uploading {local_file}...")
        sftp.put(local_file, remote_file)
        print(f"[OK] Uploaded {local_file}")
        
        sftp.close()
        ssh_client.close()
        
        print("=" * 70)
        print("[OK] Game HTML Deployed!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == '__main__':
    deploy_game_html()

