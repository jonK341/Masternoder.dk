#!/usr/bin/env python3
"""
Deploy all reusable components integration (battle, social, chat)
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
SERVER_KEY_PATH = os.path.expanduser('~/.ssh/id_rsa')
REMOTE_BASE = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    'backend/routes/battle.py',
    'backend/routes/social.py',
    'backend/routes/chat_enhanced.py'
]

def deploy_files():
    """Deploy files to production server"""
    print("="*80)
    print("DEPLOYING REUSABLE COMPONENTS INTEGRATION")
    print("="*80)
    
    # Read SSH key
    try:
        private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
    except Exception as e:
        print(f"Error reading SSH key: {e}")
        print("Note: Deployment requires SSH key authentication")
        print("Files are ready for manual deployment")
        return False
    
    # Connect to server
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, pkey=private_key)
        print(f"Connected to {SERVER_HOST}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Note: Deployment requires SSH key authentication")
        print("Files are ready for manual deployment")
        print("\nManual deployment instructions:")
        print("1. Copy files to server using scp")
        print("2. Set permissions: chmod 644 <file>")
        print("3. Restart uWSGI: systemctl restart uwsgi")
        return False
    
    try:
        # Deploy files
        scp = SCPClient(ssh.get_transport())
        
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                print(f"Warning: File not found: {file_path}")
                continue
            
            remote_path = os.path.join(REMOTE_BASE, file_path)
            remote_dir = os.path.dirname(remote_path)
            
            # Create remote directory if needed
            ssh.exec_command(f"mkdir -p {remote_dir}")
            
            # Copy file
            scp.put(file_path, remote_path)
            print(f"Deployed: {file_path} -> {remote_path}")
            
            # Set permissions
            ssh.exec_command(f"chmod 644 {remote_path}")
        
        # Restart uWSGI service
        print("\nRestarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("uWSGI service restarted successfully")
        else:
            error = stderr.read().decode()
            print(f"uWSGI restart warning: {error}")
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_files()
    exit(0 if success else 1)

