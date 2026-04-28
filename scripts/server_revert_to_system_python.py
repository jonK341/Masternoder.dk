#!/usr/bin/env python3
"""Revert uWSGI to system Python (comment out virtualenv). Use if venv install failed (e.g. no space)."""
import os
import sys
from pathlib import Path
try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
UWSGI_INI = "/var/www/html/uwsgi.ini"

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode().strip()
    err = (stderr.read() or b"").decode().strip()
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
run(ssh, f"sed -i 's|^virtualenv = |# virtualenv = |' {UWSGI_INI}")
print("Reverted uwsgi.ini to system Python (virtualenv commented out)")
run(ssh, "systemctl restart uwsgi-vidgenerator", timeout=30)
print("Restarted uwsgi-vidgenerator")
ssh.close()
print("Done. Site should work with system Python again.")
