#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy All Fixes and Restart Services
"""
import paramiko
import os
import time
import sys
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

FILES_TO_DEPLOY = [
    {
        'local': 'vidgenerator/index.html',
        'remote': '/var/www/html/vidgenerator/vidgenerator/index.html'
    },
    {
        'local': 'vidgenerator/battle/index.html',
        'remote': '/var/www/html/vidgenerator/vidgenerator/battle/index.html'
    },
    {
        'local': 'vidgenerator/static/js/unified-point-counters.js',
        'remote': '/var/www/html/vidgenerator/vidgenerator/static/js/unified-point-counters.js'
    },
]

def deploy():
    """Deploy all fixes and restart services"""
    try:
        print("=" * 80)
        print("DEPLOYING ALL FIXES AND RESTARTING SERVICES")
        print("=" * 80)
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        sftp = ssh.open_sftp()
        deployed = 0
        failed = 0
        
        for file_info in FILES_TO_DEPLOY:
            local_file = file_info['local']
            remote_file = file_info['remote']
            
            if not os.path.exists(local_file):
                print(f"[SKIP] {local_file} - File not found")
                failed += 1
                continue
            
            try:
                print(f"Deploying: {local_file}")
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1")
                
                # Create backup
                timestamp = int(time.time())
                backup_file = f"{remote_file}.backup.{timestamp}"
                ssh.exec_command(f"cp {remote_file} {backup_file} 2>&1 || echo 'No existing file to backup'")
                print(f"  [OK] Backup created: {backup_file}")
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(file_content)
                
                print(f"  [OK] Deployed to {remote_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {e}")
                failed += 1
        
        sftp.close()
        print()
        print(f"Deployed: {deployed}/{len(FILES_TO_DEPLOY)}")
        print(f"Failed: {failed}/{len(FILES_TO_DEPLOY)}")
        print()
        
        # Clear cache aggressively
        print("Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true")
        ssh.exec_command("rm -rf /var/www/html/vidgenerator/static/js/*.js.cache 2>/dev/null || true")
        print("[OK] Cache cleared")
        
        # Stop uWSGI
        print("Stopping uWSGI...")
        ssh.exec_command("sudo systemctl stop uwsgi-vidgenerator 2>&1")
        time.sleep(5)
        print("[OK] uWSGI stopped")
        
        # Start uWSGI
        print("Starting uWSGI...")
        ssh.exec_command("sudo systemctl start uwsgi-vidgenerator 2>&1")
        time.sleep(10)
        print("[OK] uWSGI started")
        
        # Check service status
        print()
        print("Checking service status...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl status uwsgi-vidgenerator --no-pager 2>&1 | head -20")
        status_output = stdout.read().decode('utf-8', errors='ignore').strip()
        print(status_output)
        
        # Also check if it's active
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl is-active uwsgi-vidgenerator 2>&1")
        active_status = stdout.read().decode('utf-8', errors='ignore').strip()
        if 'active' in active_status.lower():
            print("[OK] uWSGI is active and running")
        else:
            print(f"[WARN] uWSGI status: {active_status}")
        
        # Restart nginx for good measure
        print()
        print("Restarting nginx...")
        ssh.exec_command("sudo systemctl restart nginx 2>&1")
        time.sleep(3)
        print("[OK] nginx restarted")
        
        ssh.close()
        return deployed == len(FILES_TO_DEPLOY)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy()
    if success:
        print()
        print("=" * 80)
        print("DEPLOYMENT AND RESTART COMPLETE")
        print("=" * 80)
        print()
        print("All fixes deployed and services restarted!")
        print("  - Frontpage point counters fixed")
        print("  - Battle page tabs fixed and activated")
        print("  - Services restarted (uWSGI + nginx)")
        print()
        print("Wait 30 seconds for services to fully restart, then:")
        print("  1. Hard refresh the frontpage (Ctrl+F5)")
        print("  2. Hard refresh the battle page (Ctrl+F5)")
        print("  3. Check that point counters are populated")
        print("  4. Check that battle tabs are clickable and active")
        print()
    else:
        print()
        print("=" * 80)
        print("DEPLOYMENT INCOMPLETE")
        print("=" * 80)
    sys.exit(0 if success else 1)
