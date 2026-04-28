#!/usr/bin/env python3
"""Deploy the 502 app-context fix (hunters_game.py) to the server and restart uWSGI."""
import os
import sys
import time
from pathlib import Path

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
FILE_TO_DEPLOY = "backend/routes/hunters_game.py"

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

root = Path(__file__).resolve().parent.parent
local = root / FILE_TO_DEPLOY
if not local.exists():
    print(f"Missing {local}")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    except Exception:
        out, err = "", ""
    return out, err

print("Uploading", FILE_TO_DEPLOY)
remote_path = f"{REMOTE_BASE}/{FILE_TO_DEPLOY}"
sftp = ssh.open_sftp()
sftp.put(str(local), remote_path)
sftp.close()

print("Stopping uWSGI and freeing port 5000...")
run("systemctl stop uwsgi-vidgenerator 2>/dev/null; systemctl stop uwsgi 2>/dev/null; pkill -9 -f uwsgi 2>/dev/null; fuser -k 5000/tcp 2>/dev/null; true")
time.sleep(2)

print("Starting uwsgi-vidgenerator...")
run("systemctl start uwsgi-vidgenerator", timeout=25)
time.sleep(5)

out, _ = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000")
print("Port 5000 HTTP:", out if out else "timeout")
run("systemctl reload nginx 2>/dev/null || true")
ssh.close()
print("Done. If 502 persists, run: python fix_502.py")
