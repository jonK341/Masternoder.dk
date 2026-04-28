#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full restart Flask services - stop completely, wait, then start fresh.
This ensures routes are fully reloaded.
"""
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def _sh_bg(ssh, cmd, wait_sec=10):
    ssh.exec_command(f"nohup bash -c '{cmd}' </dev/null >/dev/null 2>&1 &")
    time.sleep(wait_sec)


def main():
    print("=" * 70)
    print("FULL RESTART FLASK SERVICES (STOP -> WAIT -> START)")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    import paramiko
    ssh = None
    try:
        print("[1/5] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        # Stop all services
        print("[2/5] Stopping all Flask services...")
        services = ['python-proxy', 'uwsgi-vidgenerator', 'uwsgi']
        for svc in services:
            _sh_bg(ssh, f"systemctl stop {svc} 2>&1 || systemctl stop {svc}.service 2>&1 || true", wait_sec=5)
            out, _ = _sh(ssh, f"systemctl is-active {svc} 2>&1 || systemctl is-active {svc}.service 2>&1 || echo inactive", timeout=5)
            print(f"  {svc}: {out.strip() or 'stopped'}")
        print()

        # Wait for complete stop
        print("[3/5] Waiting for services to fully stop (10 seconds)...")
        time.sleep(10)
        print("  [OK] Wait complete")
        print()

        # Clear Python cache
        print("[4/5] Clearing Python cache...")
        _sh(ssh, "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        _sh(ssh, "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()

        # Start services
        print("[5/5] Starting services fresh...")
        _sh_bg(ssh, "systemctl start python-proxy 2>&1 || systemctl start python-proxy.service 2>&1 || true", wait_sec=15)
        out, _ = _sh(ssh, "systemctl is-active python-proxy 2>&1 || systemctl is-active python-proxy.service 2>&1", timeout=5)
        print(f"  python-proxy: {out.strip() or 'unknown'}")

        _sh_bg(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", wait_sec=15)
        out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        print(f"  uwsgi-vidgenerator: {out.strip() or 'unknown'}")

        _sh_bg(ssh, "systemctl start uwsgi 2>&1 || true", wait_sec=12)
        out, _ = _sh(ssh, "systemctl is-active uwsgi 2>&1", timeout=5)
        print(f"  uwsgi: {out.strip() or 'unknown'}")

        # Wait for upstream
        print("  Waiting for upstream :5000...")
        for _ in range(8):
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
            print("    [WARN] Upstream :5000 not ready")

        # Reload nginx
        print("  Reloading nginx...")
        _sh(ssh, "nginx -t 2>&1 || true", timeout=10)
        _sh_bg(ssh, "systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", wait_sec=8)
        out, _ = _sh(ssh, "systemctl is-active nginx 2>&1", timeout=5)
        print(f"  nginx: {out.strip() or 'unknown'}")

        print()
        print("=" * 70)
        print("FULL RESTART COMPLETE")
        print("=" * 70)
        print("Next step: Run hard test: python scripts/hard_test_generator_urls.py")
        print()
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
