#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy generator index.html and restart services for browser UI testing.
This is the script to use whenever you need to test browser UI changes.

Usage:
  python scripts/deploy_generator_ui_and_test.py
"""
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
LOCAL_FILE = "vidgenerator/generator/index.html"
REMOTE_FILE = f"{REMOTE_BASE}/{LOCAL_FILE.replace(os.sep, '/')}"


def _sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def _sh_bg(ssh, cmd, wait_sec=10):
    """Run command in background on server so SSH read does not block."""
    ssh.exec_command(f"nohup bash -c '{cmd}' </dev/null >/dev/null 2>&1 &")
    time.sleep(wait_sec)


def main():
    print("=" * 70)
    print("DEPLOY GENERATOR UI & RESTART SERVICES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File: {LOCAL_FILE}")
    print(f"Remote: {REMOTE_FILE}")
    print()

    # Check local file exists
    if not os.path.exists(LOCAL_FILE):
        print(f"[ERROR] Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    # Check file modification date
    import stat
    mtime = os.path.getmtime(LOCAL_FILE)
    mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Local file modified: {mtime_str}")
    print()

    import paramiko
    ssh = None
    sftp = None
    try:
        # Connect
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        # Upload file
        print("[2/3] Uploading index.html...")
        remote_dir = os.path.dirname(REMOTE_FILE)
        _sh(ssh, f"mkdir -p '{remote_dir}'", timeout=5)
        time.sleep(0.2)

        # Backup existing file
        _sh(ssh, f"cp {REMOTE_FILE} {REMOTE_FILE}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)

        # Read and upload
        with open(LOCAL_FILE, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        with sftp.file(REMOTE_FILE, "w") as rf:
            rf.write(content)

        sftp.close()
        print(f"  [OK] Uploaded {LOCAL_FILE} -> {REMOTE_FILE}")
        print()

        # Restart services (using fix_gateways approach)
        print("[3/3] Restarting services (fix_gateways)...")
        print("  Restarting python-proxy...")
        _sh_bg(ssh, "systemctl restart python-proxy 2>&1 || systemctl restart python-proxy.service 2>&1 || true", wait_sec=13)
        out, _ = _sh(ssh, "systemctl is-active python-proxy 2>&1 || systemctl is-active python-proxy.service 2>&1", timeout=5)
        print(f"    python-proxy: {out.strip() or 'unknown'}")

        print("  Restarting uwsgi-vidgenerator...")
        _sh_bg(ssh, "systemctl restart uwsgi-vidgenerator 2>&1 || true", wait_sec=13)
        out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        print(f"    uwsgi-vidgenerator: {out.strip() or 'unknown'}")

        print("  Restarting uwsgi (main)...")
        _sh_bg(ssh, "systemctl restart uwsgi 2>&1 || true", wait_sec=10)
        out, _ = _sh(ssh, "systemctl is-active uwsgi 2>&1", timeout=5)
        print(f"    uwsgi: {out.strip() or 'unknown'}")

        # Wait for upstream :5000
        print("  Waiting for upstream :5000...")
        for _ in range(6):
            out, _ = _sh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000", timeout=10)
            if out and out != "000":
                try:
                    c = int(out)
                    if 200 <= c < 600 or c in (301, 302):
                        print("    [OK] Upstream :5000 responding")
                        break
                except Exception:
                    pass
            time.sleep(3)
        else:
            print("    [WARN] Upstream :5000 not ready; continuing.")

        # Reload nginx
        print("  Reloading nginx...")
        _sh(ssh, "nginx -t 2>&1 || true", timeout=10)
        _sh_bg(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", wait_sec=8)
        out, _ = _sh(ssh, "systemctl is-active nginx 2>&1", timeout=5)
        print(f"    nginx: {out.strip() or 'unknown'}")

        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print("Next steps:")
        print("  1. Hard refresh browser: https://masternoder.dk/vidgenerator/generator/ (Ctrl+F5)")
        print("  2. Run hard test: python scripts/hard_test_generator_urls.py")
        print()
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
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
    ok = main()
    sys.exit(0 if ok else 1)
