#!/usr/bin/env python3
"""
Deploy Default User Fixes
Deploys all fixes for default_user resurrection and missing endpoints
"""
import paramiko
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

FILES_TO_DEPLOY = [
    {
        'local': 'backend/services/user_identification.py',
        'remote': f'{SERVER_BASE}/backend/services/user_identification.py',
        'description': 'User Identification Service'
    },
    {
        'local': 'backend/routes/missing_endpoints_routes.py',
        'remote': f'{SERVER_BASE}/backend/routes/missing_endpoints_routes.py',
        'description': 'Missing Endpoints Routes (with stats endpoints)'
    },
    {
        'local': 'vidgenerator/static/js/backend-connector.js',
        'remote': f'{SERVER_BASE}/static/js/backend-connector.js',
        'description': 'Backend Connector JS (improved error handling)'
    },
    {
        'local': 'vidgenerator/profile/index.html',
        'remote': f'{SERVER_BASE}/profile/index.html',
        'description': 'Profile Page HTML (fixed loading blocks)'
    },
]

def deploy_files():
    """Deploy all files to server"""
    print("=" * 70)
    print("DEPLOYING DEFAULT_USER FIXES")
    print("=" * 70)
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("[1/3] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        sftp = ssh.open_sftp()
        
        print("[2/3] Deploying files...")
        print()
        
        deployed = []
        failed = []
        
        for item in FILES_TO_DEPLOY:
            local_path = os.path.join(BASE_DIR, item['local'])
            remote_path = item['remote']
            desc = item['description']
            
            print(f"{desc}:")
            print(f"  Local:  {item['local']}")
            print(f"  Remote: {remote_path}")
            
            if not os.path.exists(local_path):
                failed.append(f"{desc}: Local file not found")
                print(f"  [FAIL] Local file not found")
                print()
                continue
            
            try:
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    ssh.exec_command(f"mkdir -p {remote_dir}", timeout=10)
                
                # Upload
                sftp.put(local_path, remote_path)
                sftp.chmod(remote_path, 0o644)
                deployed.append(desc)
                print(f"  [OK] Deployed")
            except Exception as e:
                failed.append(f"{desc}: {e}")
                print(f"  [FAIL] {e}")
            
            print()
        
        sftp.close()
        
        # Summary
        print("=" * 70)
        print("DEPLOYMENT SUMMARY")
        print("=" * 70)
        print(f"Deployed: {len(deployed)}/{len(FILES_TO_DEPLOY)}")
        print(f"Failed: {len(failed)}/{len(FILES_TO_DEPLOY)}")
        print()
        
        if deployed:
            print("Successfully deployed:")
            for desc in deployed:
                print(f"  [OK] {desc}")
            print()
        
        if failed:
            print("Failed:")
            for error in failed:
                print(f"  [FAIL] {error}")
            print()
        
        # Restart services
        print("[3/3] Restarting services...")
        print()
        
        commands = [
            ('systemctl', 'restart uwsgi-vidgenerator'),
            ('systemctl', 'restart python-proxy'),
        ]
        
        for cmd_name, cmd in commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"  [OK] {cmd_name} restarted")
                else:
                    print(f"  [WARN] {cmd_name} restart returned {exit_status}")
            except Exception as e:
                print(f"  [WARN] {cmd_name} restart failed: {e}")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        
        ssh.close()
        return len(failed) == 0
        
    except Exception as e:
        print(f"  [ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)
