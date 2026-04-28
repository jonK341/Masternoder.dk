#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Loading Optimizations (P1–P5) — upload files and restart Flask.
"""
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

FILES = [
    "vidgenerator/static/js/load-time-measurement.js",
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/stats/index.html",
    "vidgenerator/generator/index.html",
    "vidgenerator/battle/index.html",
    "vidgenerator/shop/index.html",
    "backend/routes/missing_endpoints_routes.py",
    "docs/LOADING_AND_VIDGENERATOR_STATE.md",
]


def run():
    ssh = None
    sftp = None
    try:
        print("=" * 70)
        print("DEPLOY LOADING OPTIMIZATIONS (P1–P5)")
        print("=" * 70)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)

        print("[1/4] Connecting...")
        ssh = __import__("paramiko").SSHClient()
        ssh.set_missing_host_key_policy(__import__("paramiko").AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        print("[2/4] Uploading files...")
        deployed = 0
        for local in FILES:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.1)
            except Exception:
                pass
            try:
                with open(local, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                with sftp.file(remote, "w") as rf:
                    rf.write(content)
                print(f"  [OK] {local}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local}: {e}")
        sftp.close()
        print(f"  [SUMMARY] {deployed} files uploaded")
        print()

        print("[3/4] Clearing cache...")
        ssh.exec_command(f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        print("[4/4] Restarting Flask services...")
        for svc in ["python-proxy", "uwsgi-vidgenerator", "uwsgi"]:
            ssh.exec_command(f"systemctl restart {svc} 2>&1 || true", timeout=15)
            time.sleep(3)
        time.sleep(5)
        for svc in ["python-proxy", "uwsgi-vidgenerator", "uwsgi"]:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {svc} 2>&1", timeout=5)
            status = (stdout.read() or b"").decode().strip()
            print(f"  {svc}: {status or 'unknown'}")
        print("  [OK] Restart complete")
        print()

        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print("Verify: https://masternoder.dk/vidgenerator/")
        print("Console: [LoadTime] metrics on key pages")
        print()
        ssh.close()
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        return False


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
