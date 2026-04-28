#!/usr/bin/env python3
"""
Deploy Missing Trophy Trading System Service
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

def deploy_service():
    """Deploy missing service file"""
    print("="*80)
    print("DEPLOYING MISSING TROPHY TRADING SYSTEM SERVICE")
    print("="*80)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"[OK] Connected to {SERVER_HOST}")
        
        scp = SCPClient(ssh.get_transport())
        
        # Deploy trophy_trading_system.py
        file_path = 'backend/services/trophy_trading_system.py'
        if not os.path.exists(file_path):
            print(f"[FAIL] File not found: {file_path}")
            return False
        
        remote_path = f"{REMOTE_BASE}/{file_path}"
        remote_dir = os.path.dirname(remote_path).replace('\\', '/')
        
        # Create remote directory if needed
        ssh.exec_command(f"mkdir -p {remote_dir}")
        
        # Copy file
        scp.put(file_path, remote_path)
        print(f"[OK] Deployed: {file_path} -> {remote_path}")
        
        # Set permissions
        ssh.exec_command(f"chmod 644 {remote_path}")
        
        # Restart uWSGI
        print("\nRestarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("[OK] uWSGI service restarted")
        else:
            print(f"[WARN] uWSGI restart returned exit code {exit_status}")
        
        print("\n" + "="*80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_service()
    sys.exit(0 if success else 1)

