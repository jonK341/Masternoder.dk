#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy profile page + Google/GitHub auth: upload, apply, restart.
Uploads: profile page, social_auth_routes, missing_endpoints (auth).
Then clears cache and restarts uwsgi/python-proxy/nginx.
"""
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

FILES_TO_DEPLOY = [
    "vidgenerator/profile/index.html",
    "vidgenerator/static/js/backend-connector.js",
    "backend/routes/social_auth_routes.py",
    "backend/routes/user_profile_routes.py",
    "backend/routes/missing_endpoints_routes.py",
]


def run():
    ssh = None
    sftp = None
    try:
        print("=" * 60)
        print("DEPLOY: Profile page + Auth (upload, apply, restart)")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        # Connect
        print("[1/4] Connecting...")
        ssh = __import__("paramiko").SSHClient()
        ssh.set_missing_host_key_policy(__import__("paramiko").AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        # Upload
        print("[2/4] Uploading files...")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)
        deployed = 0
        for local in FILES_TO_DEPLOY:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.2)
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

        # Clear cache
        print("[3/4] Clearing cache...")
        ssh.exec_command(
            f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command(
            f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  [OK] Cache cleared")
        print()

        # Restart services
        print("[4/4] Restarting services...")
        wait_s = 8
        ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=20)
        time.sleep(wait_s)
        ssh.exec_command("systemctl restart uwsgi 2>&1 || true", timeout=20)
        time.sleep(3)
        for _ in range(6):
            stdin, stdout, stderr = ssh.exec_command(
                "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000",
                timeout=10,
            )
            out = (stdout.read() or b"").decode().strip()
            if out and out != "000":
                try:
                    c = int(out)
                    if 200 <= c < 600 or c in (301, 302):
                        print("  [OK] Upstream :5000 responding")
                        break
                except Exception:
                    pass
            time.sleep(3)
        else:
            print("  [WARN] Upstream :5000 not ready")
        ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("  [OK] Services restarted")
        print()
        print("=" * 60)
        print("DEPLOY COMPLETE")
        print("=" * 60)
        print("Verify: https://masternoder.dk/vidgenerator/profile (Ctrl+F5)")
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
