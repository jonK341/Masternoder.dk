#!/usr/bin/env python3
"""
Quick deployment script for game.py changes
Deploys only the game route file to server
"""
import paramiko
import os
from scp import SCPClient
from pathlib import Path

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    "backend/routes/game.py",
]

def deploy():
    """Deploy game.py to server"""
    print("=" * 70)
    print("DEPLOYING GAME ROUTES TO SERVER")
    print("=" * 70)
    print(f"Server: {SERVER_HOST}")
    print(f"Remote Path: {REMOTE_PATH}")
    print()
    
    # Connect to server
    print("Connecting to server...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=30)
        print("[OK] Connected to server")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return False
    
    # Deploy files
    success_count = 0
    fail_count = 0
    
    try:
        with SCPClient(ssh.get_transport(), socket_timeout=300) as scp:
            for file_path in FILES_TO_DEPLOY:
                local_file = Path(file_path)
                if not local_file.exists():
                    print(f"[SKIP] {file_path} (not found)")
                    continue
                
                remote_file = f"{REMOTE_PATH}/{file_path}".replace("\\", "/")
                remote_dir = os.path.dirname(remote_file)
                
                # Create remote directory
                try:
                    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p '{remote_dir}'")
                    stdout.channel.recv_exit_status()
                except:
                    pass
                
                # Upload file
                try:
                    print(f"Uploading {file_path}...")
                    scp.put(str(local_file.resolve()), remote_file)
                    print(f"[OK] {file_path} -> {remote_file}")
                    success_count += 1
                except Exception as e:
                    print(f"[ERROR] {file_path}: {e}")
                    fail_count += 1
        
        # Restart service
        print("\nRestarting python-proxy service...")
        try:
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart python-proxy.service")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("[OK] Service restarted")
            else:
                error = stderr.read().decode()
                print(f"[WARN] Service restart: {error.strip()}")
        except Exception as e:
            print(f"[WARN] Could not restart service: {e}")
        
        ssh.close()
        
        print("\n" + "=" * 70)
        print(f"DEPLOYMENT COMPLETE")
        print(f"Success: {success_count}, Failed: {fail_count}")
        print("=" * 70)
        
        return fail_count == 0
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        ssh.close()
        return False

if __name__ == "__main__":
    success = deploy()
    exit(0 if success else 1)

