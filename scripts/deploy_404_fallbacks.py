#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy only backend/routes/missing_endpoints_routes.py to fix production 404s
(front page init, battle stats, agent-skillset all, profile aggregated, user identity,
account-summary points, gallery recent, trophies list, battle PVP trophies).

Uploads to BOTH /var/www/html/backend/routes/ and /var/www/html/vidgenerator/backend/routes/,
clears __pycache__, restarts python-proxy, uwsgi-vidgenerator, uwsgi, nginx.

Usage:
  python scripts/deploy_404_fallbacks.py

Then run: python scripts/test_url_timing.py (with BASE_URL=https://masternoder.dk)

If 404s persist: the process serving :5000 may be loading cached code. Run a full deploy:
  python scripts/deploy_all_and_restart_uwsgi.py
Or on the server: systemctl stop uwsgi uwsgi-vidgenerator python-proxy; sleep 5; systemctl start uwsgi uwsgi-vidgenerator python-proxy
"""
import os
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
LOCAL_FILE = "backend/routes/missing_endpoints_routes.py"
REMOTE_FILE = f"{REMOTE_BASE}/{LOCAL_FILE.replace(os.sep, '/')}"


def _sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def _sh_bg(ssh, cmd, wait_sec=10):
    ssh.exec_command(f"nohup bash -c '{cmd}' </dev/null >/dev/null 2>&1 &")
    time.sleep(wait_sec)


def main():
    print("=" * 70)
    print("DEPLOY 404 FALLBACKS (missing_endpoints_routes.py)")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File: {LOCAL_FILE}")
    print(f"Remote: {REMOTE_FILE}")
    print()

    if not os.path.exists(LOCAL_FILE):
        print(f"[ERROR] Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = None
    sftp = None
    try:
        print("[1/3] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        print("[2/3] Uploading missing_endpoints_routes.py...")
        remote_dir = os.path.dirname(REMOTE_FILE)
        _sh(ssh, f"mkdir -p '{remote_dir}'", timeout=5)
        time.sleep(0.2)
        _sh(ssh, f"cp {REMOTE_FILE} {REMOTE_FILE}.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true", timeout=5)
        with open(LOCAL_FILE, "rb") as f:
            content = f.read()
        with sftp.file(REMOTE_FILE, "wb") as rf:
            rf.write(content)
        print(f"  [OK] Uploaded -> {REMOTE_FILE}")
        # Also upload to vidgenerator/backend (app may load from there via PYTHONPATH/cwd)
        vidgen_routes = f"{REMOTE_BASE}/vidgenerator/backend/routes"
        vidgen_file = f"{vidgen_routes}/missing_endpoints_routes.py"
        _sh(ssh, f"mkdir -p '{vidgen_routes}'", timeout=5)
        try:
            with sftp.file(vidgen_file, "wb") as rf:
                rf.write(content)
            print(f"  [OK] Uploaded -> {vidgen_file}")
        except Exception as e:
            print(f"  [WARN] vidgenerator copy: {e}")
        sftp.close()
        # Verify at least one file has frontpage_init
        out, _ = _sh(ssh, f"grep -l 'def frontpage_init' {REMOTE_FILE} {vidgen_file} 2>/dev/null || echo ''", timeout=5)
        if not out.strip():
            print("  [WARN] Verify: frontpage_init not found in remote file(s)")
        else:
            print("  [OK] Verified: frontpage_init present on server")
        # Clear pycache so new code is loaded
        _sh(ssh, f"find {REMOTE_BASE}/backend/routes -name '*.pyc' -delete 2>/dev/null; find {REMOTE_BASE}/backend/routes -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; true", timeout=15)
        _sh(ssh, f"find {REMOTE_BASE}/vidgenerator/backend/routes -name '*.pyc' -delete 2>/dev/null; find {REMOTE_BASE}/vidgenerator/backend/routes -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; true", timeout=15)
        print("  [OK] Cleared __pycache__")
        print()

        print("[3/3] Restarting app (python-proxy, uwsgi, nginx)...")
        _sh_bg(ssh, "systemctl restart python-proxy 2>/dev/null || true", wait_sec=8)
        _sh_bg(ssh, "systemctl restart uwsgi-vidgenerator 2>/dev/null || true", wait_sec=8)
        _sh_bg(ssh, "systemctl restart uwsgi 2>/dev/null || true", wait_sec=8)
        time.sleep(2)
        _sh(ssh, "systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true", timeout=10)
        print("  [OK] Restarted")
        print()
        print("=" * 70)
        print("DONE. Run: python scripts/test_url_timing.py")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
