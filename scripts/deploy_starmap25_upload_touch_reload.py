#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload Star Map 25 manifest + trigger uWSGI graceful reload (no systemctl restart).

Does:
  1. SFTP: `python scripts/deploy.py starmap25 --upload-only`
  2. SSH:  `touch /var/www/html/.uwsgi_touch_reload`

Requires `touch-reload = /var/www/html/.uwsgi_touch_reload` in uwsgi.ini (repo root).
**First time** you add that line to production uwsgi.ini, run **one** full restart:
  sudo systemctl restart uwsgi-vidgenerator
After that, use this script for routine code/data deploys.

Usage:
  python scripts/deploy_starmap25_upload_touch_reload.py
  python scripts/deploy_starmap25_upload_touch_reload.py --dry-run

Env: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS (same as deploy.py / deploy_all_and_restart_uwsgi.py).
"""
from __future__ import annotations

import os
import sys
import subprocess

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
TOUCH_FILE = f"{REMOTE_BASE}/.uwsgi_touch_reload"


def main() -> int:
    dry = "--dry-run" in sys.argv
    os.chdir(_ROOT)
    deploy = os.path.join(_ROOT, "scripts", "deploy.py")
    if dry:
        print("[DRY-RUN] Would run: deploy.py starmap25 --upload-only")
        print(f"[DRY-RUN] Would SSH touch {TOUCH_FILE}")
        return 0
    print("Uploading starmap25 manifest (no systemctl restart)…")
    r = subprocess.run(
        [sys.executable, deploy, "starmap25", "--upload-only"],
        cwd=_ROOT,
    )
    if r.returncode != 0:
        print("[ERROR] deploy.py failed with code", r.returncode)
        return r.returncode
    print("Triggering uWSGI graceful reload via touch-reload…")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not SERVER_PASS:
            print("[WARN] DEPLOY_PASS empty; set env if SSH password auth needed.")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS or None, timeout=30)
        # Ensure file exists (touch creates if missing)
        stdin, stdout, stderr = ssh.exec_command(f"touch '{TOUCH_FILE}' && echo OK", timeout=15)
        out = (stdout.read() or b"").decode().strip()
        err = (stderr.read() or b"").decode().strip()
        ssh.close()
        if "OK" in out:
            print(f"  [OK] {TOUCH_FILE} touched — workers should reload (check uwsgi.log).")
        else:
            print("  [WARN] touch output:", out or "(empty)", err or "")
        return 0
    except Exception as e:
        print(f"[ERROR] SSH touch failed: {e}")
        print("  Files may have uploaded; run on server: touch", TOUCH_FILE)
        return 1


if __name__ == "__main__":
    sys.exit(main())
