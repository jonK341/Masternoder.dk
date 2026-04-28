"""Deploy redesigned pages to server"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def deploy_files():
    """Deploy redesigned pages to server"""
    try:
        import paramiko
        from scp import SCPClient
        import getpass
        
        # Server details
        hostname = 'masternoder.dk'
        username = os.getenv('DEPLOY_USER', 'root')
        password = os.getenv('DEPLOY_PASS', '')
        
        if not password:
            print("[ERROR] DEPLOY_PASS environment variable not set")
            return False
        
        print("=" * 70)
        print("Deploying Redesigned Pages")
        print("=" * 70)
        print()
        
        # Files to deploy
        files_to_deploy = [
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/index.html'),
            ('vidgenerator/gallery/index.html', '/var/www/html/vidgenerator/gallery/index.html'),
            ('vidgenerator/stats/index.html', '/var/www/html/vidgenerator/stats/index.html'),
            ('vidgenerator/static/css/modern-design-system.css', '/var/www/html/vidgenerator/static/css/modern-design-system.css'),
        ]
        
        # Connect to server
        print(f"Connecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
        
        print("[OK] Connected to server")
        print()
        
        # Deploy files
        with SCPClient(ssh.get_transport()) as scp:
            for local_path, remote_path in files_to_deploy:
                if os.path.exists(local_path):
                    print(f"Deploying {local_path}...")
                    # Create remote directory if needed
                    remote_dir = os.path.dirname(remote_path)
                    ssh.exec_command(f'mkdir -p {remote_dir}')
                    
                    scp.put(local_path, remote_path)
                    print(f"[OK] Deployed to {remote_path}")
                else:
                    print(f"[WARN] {local_path} not found, skipping")
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("[OK] All files deployed successfully!")
        print("=" * 70)
        return True
        
    except ImportError:
        print("[ERROR] paramiko or scp not installed. Install with: pip install paramiko scp")
        return False
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)

