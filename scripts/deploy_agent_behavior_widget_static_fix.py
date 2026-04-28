#!/usr/bin/env python3
"""
Deploy Agent Behavior Widget (Static Path Fix)
The server serves /vidgenerator/static/... from /var/www/html/vidgenerator/static/...
This script ensures agent-behavior-widget.js is deployed to that directory.
"""
import os
import sys
import time
from datetime import datetime

import paramiko

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

LOCAL_FILE = "vidgenerator/static/js/agent-behavior-widget.js"
REMOTE_FILE = "/var/www/html/vidgenerator/static/js/agent-behavior-widget.js"


def main():
    print("=" * 70)
    print("DEPLOY STATIC FIX: agent-behavior-widget.js")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not os.path.exists(LOCAL_FILE):
        print(f"[ERROR] Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    print("  [OK] Connected")

    ssh.exec_command("mkdir -p /var/www/html/vidgenerator/static/js 2>&1", timeout=10)
    ssh.exec_command(f"cp {REMOTE_FILE} {REMOTE_FILE}.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true", timeout=10)

    sftp = ssh.open_sftp()
    sftp.put(LOCAL_FILE, REMOTE_FILE)
    sftp.close()
    print(f"  [OK] Deployed to {REMOTE_FILE}")

    # touch for cache
    ssh.exec_command(f"touch {REMOTE_FILE} 2>&1 || true", timeout=10)

    # restart
    ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=10)
    time.sleep(5)
    ssh.exec_command("systemctl restart python-proxy", timeout=10)
    print("  [OK] Restarted services")

    ssh.close()

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()

