#!/usr/bin/env python3
"""
Deploy Agent Behavior Widget
Deploys the new agent behavior widget JS and updated dashboard HTML files.
"""
import os
import sys
import time
from datetime import datetime

import paramiko

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "vidgenerator/static/js/agent-behavior-widget.js",
    "vidgenerator/dashboard/index.html",
    "vidgenerator/unified_dashboard/index.html",
]


def deploy():
    print("=" * 70)
    print("DEPLOY AGENT BEHAVIOR WIDGET")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    print("  [OK] Connected")

    sftp = ssh.open_sftp()
    deployed = 0

    for local_file in FILES_TO_DEPLOY:
        if not os.path.exists(local_file):
            print(f"  [SKIP] {local_file} (not found)")
            continue

        remote_file = f"/var/www/html/vidgenerator/{local_file}"
        remote_dir = os.path.dirname(remote_file)

        ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
        ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true", timeout=5)
        sftp.put(local_file, remote_file)
        print(f"  [OK] Deployed {local_file}")
        deployed += 1

    sftp.close()

    print()
    print("[cache] clearing pycache/js touch...")
    ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
    ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
    ssh.exec_command("find /var/www/html/vidgenerator/static -name '*.js' -exec touch {} \\; 2>/dev/null || true", timeout=30)
    print("  [OK] Cache cleared")

    print()
    print("[restart] restarting uwsgi-vidgenerator ...")
    ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
    time.sleep(5)
    ssh.exec_command("systemctl restart python-proxy", timeout=5)
    time.sleep(3)
    print("  [OK] Restart commands sent")

    ssh.close()

    print()
    print("=" * 70)
    print("DEPLOYMENT COMPLETE")
    print("=" * 70)
    print(f"Deployed: {deployed}/{len(FILES_TO_DEPLOY)}")


if __name__ == "__main__":
    try:
        deploy()
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

