#!/usr/bin/env python3
"""Fetch last 80 lines of uwsgi.log from server to diagnose Internal Server Error (500)."""
import os
import sys

REMOTE = "/var/www/html"

def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)
    host = os.environ.get("DEPLOY_HOST", "masternoder.dk")
    user = os.environ.get("DEPLOY_USER", "root")
    password = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=30)
    except Exception as e:
        print("SSH failed:", e)
        print("Run on the server instead:  tail -80 /var/www/html/uwsgi.log")
        sys.exit(1)
    stdin, stdout, stderr = ssh.exec_command(f"tail -80 {REMOTE}/uwsgi.log 2>/dev/null", timeout=15)
    out = (stdout.read() or b"").decode(errors="replace")
    print("=== uwsgi.log (last 80 lines) ===\n")
    print(out)
    ssh.close()

if __name__ == "__main__":
    main()
