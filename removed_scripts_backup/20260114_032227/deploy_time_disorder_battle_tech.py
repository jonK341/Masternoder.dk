"""
Deploy Time Disorder Device & Advanced Battle Tech Features
"""
import os
import sys
import paramiko
from scp import SCPClient
from pathlib import Path

# Server configuration
SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PATH = '/var/www/html/vidgenerator'

# Files to deploy
FILES_TO_DEPLOY = [
    # Services
    'backend/services/time_disorder_device.py',
    'backend/services/advanced_battle_tech.py',
    'backend/services/battle_system_enhanced.py',
    
    # Routes
    'backend/routes/time_disorder_battle_routes.py',
    
    # Blueprint registration
    'backend/register_blueprints.py',
    
    # Documentation
    'TIME_DISORDER_DEATH_PORTAL_INTEGRATION.md',
]

def get_ssh_client():
    """Get SSH client connection"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Try to get credentials from environment or use default
    password = os.environ.get('DEPLOY_PASSWORD')
    key_file = os.environ.get('DEPLOY_KEY_FILE')
    
    try:
        if key_file and os.path.exists(key_file):
            ssh.connect(SERVER_HOST, username=SERVER_USER, key_filename=key_file)
        elif password:
            ssh.connect(SERVER_HOST, username=SERVER_USER, password=password)
        else:
            # Try default key locations
            default_keys = [
                os.path.expanduser('~/.ssh/id_rsa'),
                os.path.expanduser('~/.ssh/id_ed25519'),
            ]
            connected = False
            for key_path in default_keys:
                if os.path.exists(key_path):
                    try:
                        ssh.connect(SERVER_HOST, username=SERVER_USER, key_filename=key_path)
                        connected = True
                        break
                    except:
                        continue
            
            if not connected:
                print("ERROR: Could not connect. Please set DEPLOY_PASSWORD or DEPLOY_KEY_FILE environment variable")
                sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to connect to server: {e}")
        sys.exit(1)
    
    return ssh

def deploy_files(ssh_client):
    """Deploy files to server"""
    scp = SCPClient(ssh_client.get_transport())
    
    print("\n📦 Deploying files...")
    deployed_count = 0
    
    for file_path in FILES_TO_DEPLOY:
        if not os.path.exists(file_path):
            print(f"⚠️  WARNING: File not found: {file_path}")
            continue
        
        try:
            # Create remote directory if needed
            remote_dir = os.path.dirname(f"{SERVER_PATH}/{file_path}")
            ssh_client.exec_command(f"mkdir -p {remote_dir}")
            
            # Upload file
            remote_path = f"{SERVER_PATH}/{file_path}"
            scp.put(file_path, remote_path)
            print(f"✅ Deployed: {file_path}")
            deployed_count += 1
        except Exception as e:
            print(f"❌ ERROR deploying {file_path}: {e}")
    
    scp.close()
    print(f"\n✅ Deployed {deployed_count} files")
    return deployed_count

def restart_services(ssh_client):
    """Restart uWSGI service"""
    print("\n🔄 Restarting services...")
    
    commands = [
        'systemctl restart uwsgi-vidgenerator.service',
        'systemctl status uwsgi-vidgenerator.service --no-pager -l',
    ]
    
    for cmd in commands:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            
            if output:
                print(output)
            if error and 'ERROR' in error.upper():
                print(f"⚠️  {error}")
        except Exception as e:
            print(f"⚠️  Warning executing {cmd}: {e}")

def verify_deployment(ssh_client):
    """Verify deployment"""
    print("\n🔍 Verifying deployment...")
    
    check_files = [
        f"{SERVER_PATH}/backend/services/time_disorder_device.py",
        f"{SERVER_PATH}/backend/services/advanced_battle_tech.py",
        f"{SERVER_PATH}/backend/routes/time_disorder_battle_routes.py",
    ]
    
    all_ok = True
    for file_path in check_files:
        stdin, stdout, stderr = ssh_client.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'")
        result = stdout.read().decode().strip()
        
        if result == 'EXISTS':
            print(f"✅ {file_path} - EXISTS")
        else:
            print(f"❌ {file_path} - MISSING")
            all_ok = False
    
    return all_ok

def main():
    """Main deployment function"""
    import sys
    import io
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Time Disorder Device & Advanced Battle Tech Deployment")
    print("=" * 60)
    print()
    
    ssh_client = None
    try:
        # Connect to server
        print("Connecting to server...")
        ssh_client = get_ssh_client()
        print("Connected!")
        
        # Deploy files
        deployed_count = deploy_files(ssh_client)
        
        if deployed_count == 0:
            print("\nWARNING: No files deployed. Exiting.")
            return
        
        # Restart services
        restart_services(ssh_client)
        
        # Verify deployment
        if verify_deployment(ssh_client):
            print("\n" + "=" * 60)
            print("DEPLOYMENT SUCCESSFUL!")
            print("=" * 60)
            print("\nDeployed Features:")
            print("  [OK] Time Disorder Device System")
            print("  [OK] Time-Death Shield Combination")
            print("  [OK] Tech Holes for New Tech")
            print("  [OK] Advanced Battle Technology (6 ultra-impressive tech)")
            print("  [OK] Battle System Integration")
            print("  [OK] Impressiveness Scoring")
            print("\nAPI Endpoints Available:")
            print("  - POST /api/battle/time-disorder/create")
            print("  - POST /api/battle/shield/combine")
            print("  - POST /api/battle/tech-hole/create")
            print("  - POST /api/battle/advanced-tech/unlock")
            print("  - GET /api/battle/impressiveness/<user_id>")
        else:
            print("\nWARNING: Deployment completed but verification found issues.")
        
    except KeyboardInterrupt:
        print("\n\nWARNING: Deployment cancelled by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()
            print("\nDisconnected from server")

if __name__ == '__main__':
    main()

