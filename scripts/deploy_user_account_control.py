#!/usr/bin/env python3
"""
Upload latest user account control files to masternoder.dk, then run fix_502.py.
Does NOT restart Flask via restart_flask_app.py.
"""
import paramiko
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

# Latest user account control, profile, route fixes (404s), and front page
FILES = [
    "vidgenerator/profile/index.html",
    "vidgenerator/index.html",
    "vidgenerator/static/js/trigger-based-actions.js",
    "backend/routes/user_account_routes.py",
    "backend/routes/user_profile_routes.py",
    "backend/routes/agent_automation_routes.py",
    "backend/routes/missing_endpoints_routes.py",
    "backend/services/account_resolution_service.py",
    "backend/services/user_identification.py",
    "backend/services/user_profile.py",
    "backend/services/user_account_summary.py",
]


def upload_files():
    print("=" * 60)
    print("UPLOAD USER ACCOUNT CONTROL FILES")
    print("=" * 60)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    deployed = 0
    for rel in FILES:
        local = os.path.join(BASE_DIR, rel)
        remote = f"{REMOTE_BASE}/{rel}"
        if not os.path.exists(local):
            print(f"  [SKIP] {rel} (not found)")
            continue
        try:
            remote_dir = os.path.dirname(remote)
            ssh.exec_command(f"mkdir -p {remote_dir}")
            sftp.put(local, remote)
            print(f"  [OK] {rel}")
            deployed += 1
        except Exception as e:
            print(f"  [ERROR] {rel}: {e}")
    sftp.close()
    ssh.close()
    print(f"\n  Deployed {deployed} files.")
    return deployed


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    upload_files()
    print("\nRunning fix_502.py...\n")
    import subprocess
    sys.exit(subprocess.run([sys.executable, "fix_502.py"], cwd=BASE_DIR).returncode)
