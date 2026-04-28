#!/usr/bin/env python3
"""
Deploy backend generator routes to production server
"""
import os
import sys
import paramiko
from scp import SCPClient

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# Backend files to deploy
BACKEND_FILES = [
    ("backend/routes/generator.py", f"{REMOTE_PATH}/backend/routes/generator.py"),
]

def deploy_backend():
    """Deploy backend files to server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("DEPLOYING BACKEND GENERATOR ROUTES")
        print("=" * 80)
        print(f"Server: {SERVER_HOST}")
        print(f"Target: {REMOTE_PATH}")
        print()
        
        print("Connecting to server...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        scp = SCPClient(ssh_client.get_transport())
        deployed_count = 0
        
        print("Deploying backend files...")
        print("-" * 80)
        
        for local_path, remote_path in BACKEND_FILES:
            if not os.path.exists(local_path):
                print(f"[SKIP] {local_path} - File not found")
                continue
            
            try:
                scp.put(local_path, remote_path)
                file_size = os.path.getsize(local_path)
                print(f"[OK] {local_path} -> {remote_path} ({file_size:,} bytes)")
                deployed_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to deploy {local_path}: {e}")
        
        scp.close()
        
        print()
        print("=" * 80)
        print(f"Deployment Summary: {deployed_count} file(s) deployed")
        print("=" * 80)
        print()
        
        print("Restarting services to apply changes...")
        print("-" * 80)
        
        # Restart uWSGI to reload Python code
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] systemctl restart uwsgi")
        else:
            print(f"[WARN] systemctl restart uwsgi - Exit code: {exit_code}")
        
        # Restart python-proxy service
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart python-proxy.service")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print("[OK] systemctl restart python-proxy.service")
        else:
            print(f"[WARN] systemctl restart python-proxy.service - Exit code: {exit_code}")
        
        print()
        print("=" * 80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("Backend routes updated. Services restarted.")
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh_client.close()

if __name__ == '__main__':
    deploy_backend()

