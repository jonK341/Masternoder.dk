#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply Updates After Upgrade — NO SERVER REBOOT REQUIRED

Single command to make the browser see new UI and backend after a deploy.
Does: clear caches → restart app services (graceful order) → purge nginx cache →
reload nginx → ensure no-cache headers for HTML. No Ubuntu reboot, no hard reset.

Usage:
  python scripts/apply_updates.py
  python scripts/apply_updates.py --host masternoder.dk
  DEPLOY_PASS=xxx python scripts/apply_updates.py

After deploy, run this instead of rebooting the server. Users should refresh (Ctrl+F5)
or wait for /api/version check to trigger reload.
"""
import os
import sys
import time
import re
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = os.getenv("REMOTE_BASE", "/var/www/html")
WAIT_AFTER_PROXY = 6
WAIT_AFTER_UWSGI_STOP = 4
WAIT_AFTER_UWSGI_START = 8
WAIT_AFTER_UWSGI_MAIN = 4


def sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def run():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        return 1

    ssh = None
    try:
        print("=" * 60)
        print("APPLY UPDATES (no reboot)")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("Host:", SERVER_HOST)
        print()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

        # 1. Clear Python cache
        print("[1/6] Clearing Python cache...")
        sh(ssh, f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=45)
        sh(ssh, f"find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null || true", timeout=45)
        print("  done")

        # 2. Purge nginx cache (if any)
        print("[2/6] Purging nginx cache...")
        sh(ssh, "rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  done")

        # 3. Restart application services (correct order to avoid 502)
        print("[3/6] Restarting python-proxy (Flask :5000)...")
        ssh.exec_command(
            "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true",
            timeout=20
        )
        time.sleep(WAIT_AFTER_PROXY)
        out, _ = sh(ssh, "systemctl is-active python-proxy 2>&1 || systemctl is-active python-proxy.service 2>&1", timeout=5)
        print(f"  python-proxy: {out or 'unknown'}")

        print("[4/6] Restarting uwsgi-vidgenerator (stop then start)...")
        ssh.exec_command("systemctl stop uwsgi-vidgenerator 2>&1 || true", timeout=15)
        time.sleep(WAIT_AFTER_UWSGI_STOP)
        ssh.exec_command("systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=15)
        time.sleep(WAIT_AFTER_UWSGI_START)
        out, _ = sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        print(f"  uwsgi-vidgenerator: {out or 'unknown'}")

        print("  Restarting uwsgi (main)...")
        ssh.exec_command("systemctl restart uwsgi 2>&1 || true", timeout=15)
        time.sleep(WAIT_AFTER_UWSGI_MAIN)
        out, _ = sh(ssh, "systemctl is-active uwsgi 2>&1", timeout=5)
        print(f"  uwsgi: {out or 'unknown'}")

        # 4. Reload nginx (no full restart; reload is enough)
        print("[5/6] Reloading nginx...")
        out, err = sh(ssh, "nginx -t 2>&1", timeout=10)
        if "syntax is ok" in (out + err).lower():
            sh(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
            print("  nginx reloaded")
        else:
            print("  [WARN] nginx -t failed; skipping reload:", (out + err)[:200])

        # 5. Run no-cache setup so HTML pages are not cached
        print("[6/6] Ensuring no-cache for HTML (generator, trophies)...")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        setup_script = os.path.join(base, "scripts", "setup_generator_no_cache.py")
        if os.path.isfile(setup_script):
            import subprocess
            r = subprocess.run(
                [sys.executable, setup_script],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=base,
                env={**os.environ, "DEPLOY_HOST": SERVER_HOST, "DEPLOY_PASS": SERVER_PASS}
            )
            if r.returncode == 0:
                print("  no-cache rules OK")
            else:
                print("  [WARN] no-cache setup skipped:", (r.stderr or r.stdout or "")[:150])
        else:
            print("  [SKIP] setup_generator_no_cache.py not found")

        # Quick sanity check
        print()
        print("Quick check (backend :5000):")
        for path in ["/api/version", "/vidgenerator/api/version"]:
            out, _ = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000{path} 2>/dev/null || echo '---'", timeout=5)
            print(f"  {path}: {out}")

        print()
        print("=" * 60)
        print("APPLY UPDATES COMPLETE")
        print("=" * 60)
        print("Browser: open https://" + SERVER_HOST.split(":")[0] + "/vidgenerator/ and press Ctrl+F5")
        print("No server reboot was performed.")
        return 0

    except Exception as e:
        print("[ERROR]", e)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()


if __name__ == "__main__":
    sys.exit(run())
