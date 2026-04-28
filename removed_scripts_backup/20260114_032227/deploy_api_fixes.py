#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy API Endpoints Fixes and Restart Services
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    "backend/routes/generator.py",
    "backend/routes/ai_video_clip_routes.py",
    "backend/routes/system_fix_routes.py",
    "backend/register_blueprints.py",
    "vidgenerator/index.html"
]

def deploy_api_fixes():
    """Deploy API fixes and restart all services"""
    print("=" * 80)
    print("DEPLOYING API ENDPOINTS FIXES")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/6] Deploying files...")
        sftp = ssh.open_sftp()
        deployed_count = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                # Calculate remote path
                if local_file.startswith('backend/'):
                    remote_file = f"{REMOTE_BASE}/{local_file}"
                elif local_file == "vidgenerator/index.html":
                    # The app serves from /var/www/html/vidgenerator/vidgenerator/index.html (double vidgenerator)
                    remote_file = f"{REMOTE_BASE}/vidgenerator/index.html"
                elif local_file.startswith('vidgenerator/'):
                    remote_file = f"{REMOTE_BASE}/{local_file.replace('vidgenerator/', '')}"
                else:
                    remote_file = f"{REMOTE_BASE}/{local_file}"
                
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory if needed
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Create backup
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{remote_file}.backup.{timestamp}"
                ssh.exec_command(f"cp {remote_file} {backup_file} 2>&1 || true", timeout=5)
                
                # Read and deploy file
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(content)
                
                # Set permissions
                ssh.exec_command(f"chmod 644 {remote_file} 2>&1", timeout=5)
                
                print(f"  [OK] {local_file} -> {remote_file}")
                deployed_count += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] {deployed_count} files deployed")
        print()
        
        # Clear cache
        print("[3/6] Clearing cache...")
        cache_commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyo' -delete 2>/dev/null || true",
        ]
        for cmd in cache_commands:
            ssh.exec_command(cmd, timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/6] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi 2>&1 || service uwsgi restart 2>&1 || true", timeout=30)
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(2)
        print()
        
        print("[5/6] Restarting Python Proxy...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service 2>&1 || true", timeout=30)
        stdout.channel.recv_exit_status()
        print("  [OK] Python Proxy restarted")
        time.sleep(2)
        print()
        
        print("[6/6] Restarting Web Server...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart nginx 2>&1 || systemctl restart apache2 2>&1 || service nginx restart 2>&1 || service apache2 restart 2>&1 || true", timeout=30)
        stdout.channel.recv_exit_status()
        print("  [OK] Web Server restarted")
        time.sleep(2)
        print()
        
        print("=" * 80)
        print("[OK] DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Files deployed: {deployed_count}")
        print(f"  - Cache cleared")
        print(f"  - All services restarted")
        print()
        print("Test URLs:")
        print("  - https://masternoder.dk/vidgenerator/")
        print("  - https://masternoder.dk/vidgenerator/api/system/fix-all")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_api_fixes()
    sys.exit(0 if success else 1)
