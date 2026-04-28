#!/usr/bin/env python3
"""
Deploy link and navigation updates to production
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
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    'vidgenerator/index.html',
    'vidgenerator/gallery/index.html',
    'vidgenerator/generator/index.html'
]

def deploy_files():
    """Deploy files to production server"""
    print("="*80)
    print("DEPLOYING LINK AND NAVIGATION UPDATES")
    print("="*80)
    
    # Connect to server - try password authentication first, then SSH key
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected = False
    
    # Try password authentication first
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"Connected to {SERVER_HOST} (password authentication)")
        connected = True
    except Exception as e:
        print(f"Password authentication failed: {e}")
        # Try SSH key authentication as fallback
        try:
            private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
            ssh.connect(SERVER_HOST, username=SERVER_USER, pkey=private_key, timeout=30)
            print(f"Connected to {SERVER_HOST} (SSH key authentication)")
            connected = True
        except Exception as e2:
            print(f"SSH key authentication also failed: {e2}")
            print("Note: Deployment requires SSH authentication")
            print("Files are ready for manual deployment")
            return False
    
    if not connected:
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
        
        print("\n" + "="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print("\nNote: No service restart needed for static HTML files")
        return True
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy_files()
    exit(0 if success else 1)

