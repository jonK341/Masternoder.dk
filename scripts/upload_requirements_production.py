#!/usr/bin/env python3
"""
Upload requirements-production.txt to the server and show what to do next.

Usage:
  python scripts/upload_requirements_production.py

After upload, run the install script to create/use venv and install the slim deps:
  python scripts/install_requirements_on_server.py --production -y
"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
REMOTE_BASE = "/var/www/html"
LOCAL_FILE = "requirements-production.txt"
REMOTE_FILE = f"{REMOTE_BASE}/requirements-production.txt"


def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)

    local_path = PROJECT_ROOT / LOCAL_FILE
    if not local_path.is_file():
        print(f"Missing {local_path}")
        sys.exit(1)

    host = os.environ.get("DEPLOY_HOST", "masternoder.dk")
    user = os.environ.get("DEPLOY_USER", "root")
    password = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

    print("=" * 60)
    print("Upload requirements-production.txt")
    print("=" * 60)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=30)
    except Exception as e:
        print("SSH failed:", e)
        sys.exit(1)
    sftp = ssh.open_sftp()
    sftp.put(str(local_path), REMOTE_FILE)
    sftp.close()
    ssh.close()
    print(f"  Uploaded: {LOCAL_FILE} -> {REMOTE_FILE}")
    print()
    print("What to do next:")
    print("  1. Install the slim production deps (creates/uses .venv, pip install, restarts uwsgi):")
    print("     python scripts/install_requirements_on_server.py --production -y")
    print()
    print("  2. Or on the server manually:")
    print("     cd /var/www/html")
    print("     python3 -m venv .venv  # if missing")
    print("     .venv/bin/pip install -r requirements-production.txt")
    print("     # Then set virtualenv = /var/www/html/.venv in uwsgi.ini and restart uwsgi-vidgenerator")
    print("=" * 60)


if __name__ == "__main__":
    main()
