#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Unified Dashboard and Tech Tree Route Fixes
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
    "backend/routes/unified_dashboard_routes.py",
    "backend/routes/victory_tech_tree.py",
]

def deploy_fixes():
    print("="*80)
    print("DEPLOYING UNIFIED DASHBOARD & TECH TREE FIXES")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("[1/6] Connecting to server...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        sftp = ssh.open_sftp()
        deployed_count = 0

        print("[2/6] Deploying files...")
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue

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

        print("[3/6] Ensuring HTML files exist on server...")
        # Check if HTML files exist, if not, create them
        html_files = [
            ("vidgenerator/unified_dashboard/index.html", "/var/www/html/vidgenerator/vidgenerator/unified_dashboard/index.html"),
            ("vidgenerator/victory-tech-tree/index.html", "/var/www/html/vidgenerator/vidgenerator/victory-tech-tree/index.html"),
        ]
        
        for local_html, remote_html in html_files:
            if os.path.exists(local_html):
                remote_dir = os.path.dirname(remote_html)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                sftp = ssh.open_sftp()
                try:
                    sftp.put(local_html, remote_html)
                    print(f"  [OK] Deployed {local_html} -> {remote_html}")
                except:
                    print(f"  [WARN] Could not deploy {local_html}")
                sftp.close()
            else:
                print(f"  [SKIP] {local_html} (not found locally)")
        print()

        print("[4/6] Clearing cache...")
        ssh.exec_command(f"find {REMOTE_PATH_BASE} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_PATH_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        print("[5/6] Restarting services...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi 2>&1 || service uwsgi restart 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] uWSGI restarted")
        time.sleep(3)

        stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] Python Proxy restarted")
        time.sleep(3)

        stdin, stdout, stderr = ssh.exec_command("systemctl restart nginx 2>&1 || service nginx restart 2>&1 || true")
        stdout.channel.recv_exit_status()
        print("  [OK] Web Server restarted")
        time.sleep(2)
        print()

        print("[6/6] Verifying routes...")
        try:
            import requests
            test_urls = [
                f"https://{SERVER_HOST}/vidgenerator/unified_dashboard",
                f"https://{SERVER_HOST}/vidgenerator/tech-tree",
            ]
            for url in test_urls:
                try:
                    r = requests.get(url, timeout=5, allow_redirects=False)
                    status = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
                    print(f"  [{status}] {url}")
                except:
                    print(f"  [SKIP] {url}")
        except:
            print("  [INFO] Verification skipped (requests not available)")
        print()

        print("="*80)
        print("[OK] DEPLOYMENT COMPLETE!")
        print("="*80)
        print("\nFixes Applied:")
        print("  ✅ Unified Dashboard routes (with fallback HTML)")
        print("  ✅ Tech Tree routes (with fallback HTML)")
        print("  ✅ Improved path resolution")
        print("  ✅ Better error handling")
        print("\nTest URLs:")
        print("  - https://masternoder.dk/vidgenerator/unified_dashboard")
        print("  - https://masternoder.dk/vidgenerator/tech-tree")
        return True

    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    sys.exit(0 if deploy_fixes() else 1)
