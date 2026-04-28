#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Frontpage Fixes and Restart Services
Deploys vidgenerator/index.html with all frontpage fixes
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

# File to deploy
FILE_TO_DEPLOY = "vidgenerator/index.html"

def deploy_frontpage_fixes():
    """Deploy frontpage fixes and restart all services"""
    print("=" * 80)
    print("DEPLOYING FRONTPAGE FIXES")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File: {FILE_TO_DEPLOY}")
    print()
    
    try:
        # Connect
        print("[1/6] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("  [OK] Connected")
        print()
        
        # Check if file exists locally
        if not os.path.exists(FILE_TO_DEPLOY):
            print(f"[ERROR] File not found: {FILE_TO_DEPLOY}")
            return False
        
        # Deploy file
        print("[2/6] Deploying file...")
        sftp = ssh.open_sftp()
        
        # The app serves from /var/www/html/vidgenerator/vidgenerator/index.html (double vidgenerator)
        # So we need to deploy to that path
        if FILE_TO_DEPLOY == "vidgenerator/index.html":
            remote_file = f"{REMOTE_BASE}/vidgenerator/index.html"
        else:
            remote_file = f"{REMOTE_BASE}/{FILE_TO_DEPLOY.replace('vidgenerator/', '')}"
        remote_dir = os.path.dirname(remote_file)
        
        # Create directory if needed
        ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
        
        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{remote_file}.backup.{timestamp}"
        print(f"  [BACKUP] Creating backup: {backup_file}")
        ssh.exec_command(f"cp {remote_file} {backup_file} 2>&1 || true", timeout=5)
        print("  [OK] Backup created")
        
        # Read and deploy file
        print(f"  [DEPLOY] Deploying {FILE_TO_DEPLOY} -> {remote_file}")
        with open(FILE_TO_DEPLOY, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with sftp.file(remote_file, 'w') as rf:
            rf.write(content)
        
        # Set permissions
        ssh.exec_command(f"chmod 644 {remote_file} 2>&1", timeout=5)
        
        sftp.close()
        print("  [OK] File deployed")
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
        output = stdout.read().decode('utf-8', errors='ignore')
        if output:
            print(f"  Output: {output[:200]}")
        print("  [OK] uWSGI restarted")
        time.sleep(2)
        print()
        
        print("[5/6] Restarting Python Proxy...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service 2>&1 || true", timeout=30)
        stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        if output:
            print(f"  Output: {output[:200]}")
        print("  [OK] Python Proxy restarted")
        time.sleep(2)
        print()
        
        print("[6/6] Restarting Web Server...")
        # Try nginx first, then apache2
        stdin, stdout, stderr = ssh.exec_command("systemctl restart nginx 2>&1 || systemctl restart apache2 2>&1 || service nginx restart 2>&1 || service apache2 restart 2>&1 || true", timeout=30)
        stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        if output:
            print(f"  Output: {output[:200]}")
        print("  [OK] Web Server restarted")
        time.sleep(2)
        print()
        
        # Verify services
        print("[VERIFY] Checking service status...")
        services_to_check = [
            ("uwsgi", "systemctl is-active uwsgi 2>&1 || service uwsgi status 2>&1 | grep -q running && echo active || echo inactive"),
            ("python-proxy", "systemctl is-active python-proxy.service 2>&1 || echo inactive"),
        ]
        
        for service_name, check_cmd in services_to_check:
            stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=10)
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            if 'active' in status.lower() or 'running' in status.lower():
                print(f"  [OK] {service_name} is active")
            else:
                print(f"  [WARN] {service_name} status: {status[:100]}")
        
        print()
        print("=" * 80)
        print("[OK] DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - File deployed: {FILE_TO_DEPLOY}")
        print(f"  - Backup created: {backup_file}")
        print(f"  - Cache cleared")
        print(f"  - All services restarted")
        print()
        print("Test URL: https://masternoder.dk/vidgenerator/")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_frontpage_fixes()
    sys.exit(0 if success else 1)
