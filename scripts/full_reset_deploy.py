#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full reset deploy — deploy latest changes, clear all caches, restart services, optional reboot.

Use this when you want to see new changes in action and ensure nothing is cached.

Steps:
  1. Upload: trophies page + points route (and any other files you add below)
  2. Clear Python + nginx caches on server
  3. Restart: python-proxy → uwsgi-vidgenerator → uwsgi → reload nginx
  4. Optional: reboot the Ubuntu server (--reboot)

Usage:
  python scripts/full_reset_deploy.py
  python scripts/full_reset_deploy.py --reboot
  DEPLOY_PASS=xxx python scripts/full_reset_deploy.py --reboot

After run: wait ~10 s (or ~2 min if you used --reboot), then open
  https://masternoder.dk/vidgenerator/trophies
and press Ctrl+F5.
"""
import os
import sys
import time
import argparse

# Files to deploy (trophies page, profile trophies, API routes, service worker)
FILES_TO_DEPLOY = [
    "vidgenerator/trophies/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/service-worker.js",
    "backend/routes/points_routes.py",
    "backend/routes/trophies_routes.py",
]

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = os.getenv("REMOTE_BASE", "/var/www/html")


def sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def run():
    parser = argparse.ArgumentParser(description="Full reset deploy: upload files, apply updates, optional reboot")
    parser.add_argument("--reboot", action="store_true", help="Reboot the Ubuntu server after apply_updates")
    args = parser.parse_args()

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        return 1

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ssh = None

    try:
        print("=" * 60)
        print("FULL RESET DEPLOY")
        print("=" * 60)
        print("Host:", SERVER_HOST)
        print("Files:", FILES_TO_DEPLOY)
        print("Reboot after:", "YES" if args.reboot else "NO")
        print()

        # --- 1. Connect and upload files ---
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

        sftp = ssh.open_sftp()
        deployed = 0
        for rel_path in FILES_TO_DEPLOY:
            local_path = os.path.join(base, rel_path.replace("/", os.sep))
            if not os.path.exists(local_path):
                print("[SKIP]", rel_path, "(not found)")
                continue
            remote_path = os.path.join(REMOTE_BASE, rel_path.replace("\\", "/")).replace("\\", "/")
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=10)
            stdout.channel.recv_exit_status()
            try:
                sftp.put(local_path, remote_path)
                print("[OK]", rel_path)
                deployed += 1
            except Exception as e:
                print("[ERROR]", rel_path, e)
        sftp.close()
        print("Deployed", deployed, "file(s).")
        print()

        # --- 2. Full cache clear and service restarts (on server) ---
        print("[1/4] Clearing Python cache...")
        sh(ssh, f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=45)
        sh(ssh, f"find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null || true", timeout=45)
        print("  done")

        print("[2/4] Purging nginx cache...")
        sh(ssh, "rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  done")

        print("[3/4] Restarting services (python-proxy -> uwsgi-vidgenerator -> uwsgi)...")
        ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=20)
        time.sleep(6)
        ssh.exec_command("systemctl stop uwsgi-vidgenerator 2>&1 || true", timeout=15)
        time.sleep(4)
        ssh.exec_command("systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=15)
        time.sleep(8)
        ssh.exec_command("systemctl restart uwsgi 2>&1 || true", timeout=15)
        time.sleep(4)
        print("  done")

        print("[4/4] Reloading nginx...")
        out, err = sh(ssh, "nginx -t 2>&1", timeout=10)
        if "syntax is ok" in (out + err).lower():
            sh(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
            print("  nginx reloaded")
        else:
            print("  [WARN] nginx -t failed:", (out + err)[:150])
        print()

        # --- Optional: reboot ---
        if args.reboot:
            print("Rebooting server in 5 seconds... (Ctrl+C to cancel)")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                print("\nReboot cancelled.")
                return 0
            sh(ssh, "reboot 2>&1 || true", timeout=5)
            print("Reboot sent. Wait 1-2 minutes, then open https://" + SERVER_HOST.split(":")[0] + "/vidgenerator/trophies and press Ctrl+F5")
        else:
            print("Quick check:")
            for path in ["/api/version", "/vidgenerator/api/version"]:
                code, _ = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000{path} 2>/dev/null || echo '---'", timeout=5)
                print(" ", path, ":", code)
            print()
            print("Done. Open https://" + SERVER_HOST.split(":")[0] + "/vidgenerator/trophies and press Ctrl+F5")

        print("=" * 60)
        ssh.close()
        return 0

    except Exception as e:
        print("[ERROR]", e)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(run())
