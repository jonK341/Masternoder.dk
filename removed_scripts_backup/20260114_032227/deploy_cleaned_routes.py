#!/usr/bin/env python3
"""
Deploy Cleaned Battle Routes File
"""
import paramiko
from scp import SCPClient
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

def deploy_cleaned_routes():
    """Deploy cleaned battle routes file"""
    print("="*80)
    print("DEPLOYING CLEANED BATTLE ROUTES FILE")
    print("="*80)
    print()
    
    file_path = 'backend/routes/battle.py'
    
    if not os.path.exists(file_path):
        print(f"[FAIL] File not found: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    print(f"[OK] File size: {file_size:,} bytes")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"[OK] Connected to {SERVER_HOST}")
        
        scp = SCPClient(ssh.get_transport())
        
        # Create backup on server
        remote_path = f"{REMOTE_BASE}/{file_path}"
        print(f"\n1. Creating server backup...")
        ssh.exec_command(f"cp {remote_path} {remote_path}.backup.$(date +%Y%m%d_%H%M%S)")
        
        # Deploy cleaned file
        print(f"2. Deploying cleaned file...")
        scp.put(file_path, remote_path)
        print(f"[OK] Deployed: {file_path} -> {remote_path}")
        
        # Set permissions
        ssh.exec_command(f"chmod 644 {remote_path}")
        
        # Restart uWSGI
        print("\n3. Restarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("[OK] uWSGI service restarted")
        else:
            error_output = stderr.read().decode('utf-8', errors='ignore')
            print(f"[WARN] uWSGI restart returned exit code {exit_status}")
            if error_output:
                print(f"Error: {error_output}")
        
        print("\n" + "="*80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("="*80)
        print("\nNext steps:")
        print("  1. Wait 5 seconds for server to restart")
        print("  2. Test route import")
        print("  3. Test API endpoints")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_cleaned_routes()
    sys.exit(0 if success else 1)

