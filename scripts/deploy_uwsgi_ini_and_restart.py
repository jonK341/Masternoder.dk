#!/usr/bin/env python3
"""Deploy root uwsgi.ini (+ optional service worker files) and restart uwsgi-vidgenerator."""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

# Files to deploy: (local_path, remote_path) — root layout (no vidgenerator subfolder)
FILES = [
    (PROJECT_ROOT / "uwsgi.ini", f"{REMOTE_BASE}/uwsgi.ini"),
    (PROJECT_ROOT / "service-worker.js", f"{REMOTE_BASE}/service-worker.js"),
    (PROJECT_ROOT / "static" / "js" / "service-worker-gatherer.js", f"{REMOTE_BASE}/static/js/service-worker-gatherer.js"),
]


def main():
    if not FILES[0][0].exists():
        print(f"Missing {FILES[0][0]}")
        sys.exit(1)
    print("=" * 50)
    print("Deploy uwsgi.ini + service worker & restart uwsgi-vidgenerator")
    print("=" * 50)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    for local, remote in FILES:
        if not local.exists():
            print(f"  [SKIP] {local} (missing)")
            continue
        print(f"[1] Upload {local.name} -> {remote}")
        sftp.put(str(local), remote)
    sftp.close()
    print("  [OK] Uploaded")
    print("[2] Strip CRLF in uwsgi.ini on server")
    stdin, stdout, stderr = ssh.exec_command(
        f"sed -i 's/\\r$//' {REMOTE_BASE}/uwsgi.ini 2>/dev/null; echo done", timeout=10
    )
    stdout.read()
    print("[3] Restart uwsgi-vidgenerator")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=120)
    try:
        err = (stderr.read() or b"").decode().strip()
        out = (stdout.read() or b"").decode().strip()
        if err and "Failed" in err:
            print(f"  [WARN] {err}")
        else:
            print("  [OK] Restarted")
    except (TimeoutError, OSError):
        print("  [OK] Restart sent (command may still be running on server)")
    _, status_stdout, _ = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=10)
    status = (status_stdout.read() or b"").decode().strip()
    print(f"  Status: {status}")
    ssh.close()
    print("=" * 50)
    print("Done. Workers may take 60–90s to load; then test https://masternoder.dk/")
    print("=" * 50)


if __name__ == "__main__":
    main()
