"""
Deploy Enhanced Trophy Hunter System
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import paramiko
from scp import SCPClient
import getpass

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PORT = 22
REMOTE_BASE = '/var/www/masternoder.dk'

# Files to deploy
files_to_deploy = [
    'backend/services/trophy_system.py',
    'backend/routes/trophy_hunter_enhanced.py',
    'backend/register_blueprints.py'
]

def deploy_files():
    """Deploy files to server"""
    print("🚀 Deploying Enhanced Trophy Hunter System...")
    print(f"📦 Deploying {len(files_to_deploy)} files...")
    
    # Get password
    password = getpass.getpass(f"Enter password for {SERVER_USER}@{SERVER_HOST}: ")
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"🔐 Connecting to {SERVER_HOST}...")
        ssh.connect(SERVER_HOST, port=SERVER_PORT, username=SERVER_USER, password=password)
        
        # Create SCP client
        scp = SCPClient(ssh.get_transport())
        
        # Deploy files
        for file_path in files_to_deploy:
            local_path = os.path.join(project_root, file_path)
            remote_path = os.path.join(REMOTE_BASE, file_path)
            
            if os.path.exists(local_path):
                print(f"  📤 Deploying {file_path}...")
                # Create remote directory if needed
                remote_dir = os.path.dirname(remote_path)
                ssh.exec_command(f"mkdir -p {remote_dir}")
                
                scp.put(local_path, remote_path)
                print(f"  ✅ Deployed {file_path}")
            else:
                print(f"  ⚠️  File not found: {local_path}")
        
        # Restart uWSGI
        print("\n🔄 Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("✅ uWSGI restarted successfully")
        else:
            error = stderr.read().decode()
            print(f"⚠️  uWSGI restart warning: {error}")
        
        scp.close()
        ssh.close()
        
        print("\n✅ Deployment complete!")
        print("📋 Enhanced Trophy Hunter features:")
        print("   - Intelligence storage and functions")
        print("   - Reaction counter with stats linking")
        print("   - Rewards system")
        print("   - UnEmotional World acceptance")
        print("   - 3D glasses functionality")
        print("   - CounterSpells and Interrupt Spells")
        print("   - Magic system integration")
        
    except paramiko.AuthenticationException:
        print("❌ Authentication failed. Please check your credentials.")
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_files()


