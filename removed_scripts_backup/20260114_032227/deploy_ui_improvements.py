#!/usr/bin/env python3
"""
Deploy UI/UX Improvements
Deploys loading states CSS, toast notifications JS, and updated HTML pages
"""
import os
import sys
import paramiko
from scp import SCPClient
from pathlib import Path

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = os.getenv('DEPLOY_USER', 'root')
SERVER_PASS = os.getenv('DEPLOY_PASS', '')
SERVER_BASE = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    'vidgenerator/static/css/loading-states.css',
    'vidgenerator/static/js/toast-notifications.js',
    'vidgenerator/gallery/index.html',
    'vidgenerator/index.html',
    'vidgenerator/game/index.html',
    'vidgenerator/stats/index.html',
    'src/utils/loading_states.py'
]

def deploy():
    """Deploy UI improvements to server"""
    print("=" * 70)
    print("Deploying UI/UX Improvements")
    print("=" * 70)
    
    if not SERVER_PASS:
        print("[ERROR] DEPLOY_PASS environment variable not set!")
        return False
    
    try:
        # Connect to server
        print(f"Connecting to {SERVER_HOST}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS)
        print("[OK] Connected!")
        
        # Deploy files
        scp = SCPClient(ssh.get_transport())
        
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                print(f"[SKIP] {file_path} (not found)")
                continue
            
            # Determine server path
            if file_path.startswith('vidgenerator/'):
                server_path = f"{SERVER_BASE}/{file_path.replace('vidgenerator/', '')}"
            elif file_path.startswith('src/'):
                server_path = f"{SERVER_BASE}/{file_path}"
            else:
                server_path = f"{SERVER_BASE}/{file_path}"
            
            # Create directory if needed
            server_dir = os.path.dirname(server_path)
            ssh.exec_command(f"mkdir -p {server_dir}")
            
            print(f"Uploading {file_path}...")
            scp.put(file_path, server_path)
            print(f"[OK] Uploaded -> {server_path}")
        
        scp.close()
        ssh.close()
        
        print("\n" + "=" * 70)
        print("[OK] Deployment Complete!")
        print(f"    Deployed: {len([f for f in FILES_TO_DEPLOY if os.path.exists(f)])} files")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy()
    sys.exit(0 if success else 1)

