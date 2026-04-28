#!/usr/bin/env python3
"""
Deploy Profile Fixes to Server
Uploads fixed backend-connector.js and profile/index.html to production
"""
import paramiko
import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html/vidgenerator"

FILES_TO_DEPLOY = [
    {
        'local': 'vidgenerator/static/js/backend-connector.js',
        'remote': f'{SERVER_BASE}/static/js/backend-connector.js',
        'description': 'Backend Connector (Fixed getStats endpoint)'
    },
    {
        'local': 'vidgenerator/profile/index.html',
        'remote': f'{SERVER_BASE}/profile/index.html',
        'description': 'Profile Page (Fixed initialization and stats loading)'
    }
]

def deploy_files():
    """Deploy files to server via SSH"""
    print("=" * 70)
    print("DEPLOY PROFILE FIXES TO SERVER")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to server
        print("[1/4] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/4] Deploying files...")
        sftp = ssh.open_sftp()
        
        deployed = []
        failed = []
        
        for file_info in FILES_TO_DEPLOY:
            local_path = os.path.join(BASE_DIR, file_info['local'])
            remote_path = file_info['remote']
            desc = file_info['description']
            
            if not os.path.exists(local_path):
                failed.append(f"{desc}: Local file not found")
                print(f"  [FAIL] {desc}: File not found locally")
                continue
            
            try:
                # Upload file
                sftp.put(local_path, remote_path)
                
                # Set permissions
                sftp.chmod(remote_path, 0o644)
                
                deployed.append(desc)
                print(f"  [OK] {desc}")
                
            except Exception as e:
                failed.append(f"{desc}: {str(e)}")
                print(f"  [FAIL] {desc}: {e}")
        
        sftp.close()
        print()
        
        # Clear cache
        print("[3/4] Clearing Python cache...")
        commands = [
            f"find {SERVER_BASE} -type d -name '__pycache__' -exec rm -r {{}} + 2>/dev/null || true",
            f"find {SERVER_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            f"find {SERVER_BASE} -type f -name '*.pyo' -delete 2>/dev/null || true",
        ]
        for cmd in commands:
            ssh.exec_command(cmd, timeout=10)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/4] Restarting services...")
        
        # Stop services
        print("  Stopping uwsgi-vidgenerator...")
        ssh.exec_command("systemctl stop uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        
        print("  Stopping python-proxy...")
        ssh.exec_command("systemctl stop python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(3)
        
        # Wait a moment
        time.sleep(2)
        
        # Start services
        print("  Starting uwsgi-vidgenerator...")
        ssh.exec_command("systemctl start uwsgi-vidgenerator > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        
        print("  Starting python-proxy...")
        ssh.exec_command("systemctl start python-proxy > /dev/null 2>&1 &", timeout=5)
        time.sleep(5)
        
        # Verify services
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        
        print(f"  uwsgi-vidgenerator: {uwsgi_status}")
        print(f"  python-proxy: {proxy_status}")
        print()
        
        # Summary
        print("=" * 70)
        print("DEPLOYMENT SUMMARY")
        print("=" * 70)
        print(f"Deployed: {len(deployed)}/{len(FILES_TO_DEPLOY)}")
        for desc in deployed:
            print(f"  [OK] {desc}")
        
        if failed:
            print(f"\nFailed: {len(failed)}")
            for error in failed:
                print(f"  [FAIL] {error}")
        
        print()
        print("Services Status:")
        print(f"  uwsgi-vidgenerator: {uwsgi_status}")
        print(f"  python-proxy: {proxy_status}")
        print()
        print("Next Steps:")
        print("  1. Wait 10-15 seconds for services to fully initialize")
        print("  2. Test profile page: https://masternoder.dk/vidgenerator/profile")
        print("  3. Check browser console for any JavaScript errors")
        print()
        
        ssh.close()
        return len(failed) == 0
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)
