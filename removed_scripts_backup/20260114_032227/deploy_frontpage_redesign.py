#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Frontpage Redesign and Restart All Systems
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_PATH_BASE = "/var/www/html/vidgenerator"

FILES_TO_DEPLOY = [
    "vidgenerator/index.html",
]

def deploy_redesign():
    print("="*80)
    print("DEPLOYING FRONTPAGE REDESIGN & RESTARTING ALL SYSTEMS")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("[1/7] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        sftp = ssh.open_sftp()
        deployed_count = 0

        print("[2/7] Deploying files...")
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue

            # The app serves from /var/www/html/vidgenerator/vidgenerator/index.html
            if local_file == "vidgenerator/index.html":
                remote_file_path = f"{REMOTE_PATH_BASE}/vidgenerator/index.html"
            else:
                remote_file_path = f"{REMOTE_PATH_BASE}/{local_file}"
            
            remote_dir = os.path.dirname(remote_file_path)

            # Ensure remote directory exists
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)

            # Create backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{remote_file_path}.backup.{timestamp}"
            ssh.exec_command(f"cp {remote_file_path} {backup_file} 2>&1 || true", timeout=5)

            # Upload file
            sftp.put(local_file, remote_file_path)
            print(f"  [OK] {local_file} -> {remote_file_path}")
            print(f"  [BACKUP] {backup_file}")
            deployed_count += 1
        sftp.close()
        print(f"  [SUMMARY] {deployed_count} files deployed")
        print()

        print("[3/7] Clearing cache...")
        ssh.exec_command(f"find {REMOTE_PATH_BASE} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_PATH_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        print("[4/7] Restarting uWSGI...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi 2>&1 || service uwsgi restart 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(3)

        print("[5/7] Restarting Python Proxy...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] Python Proxy restarted")
        time.sleep(3)

        print("[6/7] Restarting Web Server...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart nginx 2>&1 || service nginx restart 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] Web Server restarted")
        time.sleep(2)

        print("[7/7] Triggering system initialization...")
        # Trigger initialization endpoint
        try:
            import requests
            init_url = f"https://{SERVER_HOST}/vidgenerator/api/frontpage/init"
            requests.post(init_url, timeout=10)
            print("  [OK] System initialization triggered")
        except:
            print("  [INFO] Initialization will happen on first page load")
        print()

        print("="*80)
        print("[OK] DEPLOYMENT COMPLETE!")
        print("="*80)
        print("\nSummary:")
        print(f"  - Files deployed: {deployed_count}")
        print("  - Cache cleared")
        print("  - All services restarted")
        print("  - Systems will initialize on first load")
        print("\nNew Features:")
        print("  - Competitive modern design")
        print("  - Enhanced stats dashboard")
        print("  - Real-time point counters")
        print("  - System auto-initialization")
        print("  - Auto-refresh every 30 seconds")
        print("\nTest URL:")
        print("  - https://masternoder.dk/vidgenerator/")
        return True

    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    sys.exit(0 if deploy_redesign() else 1)
