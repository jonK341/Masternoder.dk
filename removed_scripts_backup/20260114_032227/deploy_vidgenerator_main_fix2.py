#!/usr/bin/env python3
"""
Deploy vidgenerator_main.py fix with better error handling and logging
"""
import paramiko
from scp import SCPClient
import os
import sys

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    'backend/routes/vidgenerator_main.py'
]

def deploy_files():
    """Deploy files to production server"""
    print("="*80)
    print("DEPLOYING VIDGENERATOR_MAIN FIX (v2)")
    print("="*80)
    
    # Connect to server
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"Connected to {SERVER_HOST}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return False
    
    try:
        # Deploy files
        scp = SCPClient(ssh.get_transport())
        
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                print(f"Warning: File not found: {file_path}")
                continue
            
            # Normalize path separators for Linux
            normalized_file_path = file_path.replace('\\', '/')
            remote_path = f"{REMOTE_BASE}/{normalized_file_path}"
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            
            # Create remote directory if needed
            ssh.exec_command(f"mkdir -p {remote_dir}")
            
            # Copy file
            scp.put(file_path, remote_path)
            print(f"Deployed: {file_path} -> {remote_path}")
            
            # Set permissions
            ssh.exec_command(f"chmod 644 {remote_path}")
        
        # Verify file exists on server
        print("\nVerifying file exists on server...")
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {REMOTE_BASE}/vidgenerator/index.html")
        output = stdout.read().decode('utf-8')
        if output:
            print(f"File check: {output.strip()}")
        else:
            print("WARNING: Could not verify file exists")
        
        # Restart uWSGI to load changes
        print("\nRestarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("uWSGI service restarted successfully")
        else:
            print(f"Warning: uWSGI restart returned exit code {exit_status}")
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("\nCheck server logs for file path debugging:")
        print("  journalctl -u uwsgi -n 50 --no-pager | grep VidGenerator")
        return True
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_files()
    exit(0 if success else 1)

