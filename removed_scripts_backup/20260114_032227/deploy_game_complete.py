"""Deploy game page and all related changes"""
import os
import sys
import paramiko
from scp import SCPClient
from pathlib import Path

# Server configuration
DEPLOY_HOST = 'masternoder.dk'
DEPLOY_USER = os.getenv('DEPLOY_USER', 'root')
DEPLOY_PASS = os.getenv('DEPLOY_PASS', 'your_password_here')

# Files to deploy
FILES_TO_DEPLOY = [
    'vidgenerator/game/index.html',
    'backend/routes/game.py',
    'vidgenerator/static/css/modern-design-system.css',
]

# Remote paths
REMOTE_BASE = '/var/www/html/vidgenerator'
REMOTE_BACKEND = '/var/www/html'

def deploy_files():
    """Deploy files to server"""
    try:
        print("=" * 70)
        print("Deploying Game Changes")
        print("=" * 70)
        print()
        
        # Connect to server
        print(f"Connecting to {DEPLOY_HOST}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(DEPLOY_HOST, username=DEPLOY_USER, password=DEPLOY_PASS)
        
        scp = SCPClient(ssh.get_transport())
        
        deployed_count = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"[SKIP] {local_file} - File not found")
                continue
            
            # Determine remote path
            if local_file.startswith('vidgenerator/'):
                remote_file = os.path.join(REMOTE_BASE, local_file.replace('vidgenerator/', ''))
            elif local_file.startswith('backend/'):
                remote_file = os.path.join(REMOTE_BACKEND, local_file)
            else:
                remote_file = os.path.join(REMOTE_BASE, local_file)
            
            # Create remote directory if needed
            remote_dir = os.path.dirname(remote_file)
            ssh.exec_command(f'mkdir -p {remote_dir}')
            
            # Deploy file
            print(f"[DEPLOY] {local_file} -> {remote_file}")
            scp.put(local_file, remote_file)
            deployed_count += 1
        
        scp.close()
        ssh.close()
        
        print()
        print("=" * 70)
        print(f"[OK] Deployed {deployed_count} files successfully!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)

