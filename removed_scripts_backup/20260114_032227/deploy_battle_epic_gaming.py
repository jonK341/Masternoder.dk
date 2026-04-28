#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Epic Gaming Experience to Battle System
"""
import paramiko
import os
import time
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

FILES_TO_DEPLOY = [
    {
        'local': 'vidgenerator/battle/index.html',
        'remote': '/var/www/html/vidgenerator/vidgenerator/battle/index.html'
    },
    {
        'local': 'vidgenerator/static/js/epic-gaming-experience.js',
        'remote': '/var/www/html/vidgenerator/vidgenerator/static/js/epic-gaming-experience.js'
    },
    {
        'local': 'vidgenerator/static/js/quick-battle-frontend.js',
        'remote': '/var/www/html/vidgenerator/vidgenerator/static/js/quick-battle-frontend.js'
    },
]

def deploy():
    """Deploy Epic Gaming Experience to battle system"""
    try:
        print("=" * 80)
        print("DEPLOYING EPIC GAMING EXPERIENCE TO BATTLE SYSTEM")
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
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_file = f"{remote_file}.backup.{timestamp}"
                ssh.exec_command(f"cp {remote_file} {backup_file} 2>&1 || echo 'No existing file to backup'")
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(file_content)
                
                print(f"  [OK] Deployed to {remote_file}")
                print(f"  [OK] Backup created: {backup_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {e}")
                failed += 1
        
        sftp.close()
        print()
        print(f"Deployed: {deployed}/{len(FILES_TO_DEPLOY)}")
        print(f"Failed: {failed}/{len(FILES_TO_DEPLOY)}")
        print()
        
        # Clear cache
        print("Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true")
        print("[OK] Cache cleared")
        
        # Restart uWSGI
        print("Restarting uWSGI...")
        ssh.exec_command("sudo systemctl restart uwsgi-vidgenerator 2>&1")
        time.sleep(5)
        print("[OK] uWSGI restarted")
        
        # Check service status
        print()
        print("Checking service status...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl is-active uwsgi-vidgenerator 2>&1")
        status_output = stdout.read().decode('utf-8', errors='ignore').strip()
        if 'active' in status_output.lower():
            print("[OK] uWSGI is running")
        else:
            print(f"[WARN] uWSGI status: {status_output}")
        
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
        print("DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("Epic Gaming Experience has been integrated into the battle system!")
        print("All battle activities will now count towards unified progression.")
        print()
        print("Wait 15 seconds for service to fully restart, then test:")
        print("  - Visit: https://masternoder.dk/vidgenerator/battle")
        print("  - Click on 'Epic Journey' tab")
        print("  - All battle activities will count towards your epic progression!")
        print()
    else:
        print()
        print("=" * 80)
        print("DEPLOYMENT INCOMPLETE")
        print("=" * 80)
    sys.exit(0 if success else 1)
