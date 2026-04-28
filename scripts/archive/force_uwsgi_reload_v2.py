#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Force uwsgi reload - check config and restart properly."""
import os
import time
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=60):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out + ("\n" + err if err else "")
    except Exception as e:
        return f"ERROR: {e}"


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("FORCE UWSGI RELOAD V2")
    print("=" * 60)

    # Check uwsgi.ini
    print("\n[1] Check uwsgi.ini:")
    print(sh(ssh, "cat /var/www/html/vidgenerator/uwsgi.ini 2>&1"))

    # Clear pycache
    print("\n[2] Clear __pycache__:")
    sh(ssh, "find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
    sh(ssh, "find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
    print("  Cleared")

    # Touch the WSGI module to trigger reload
    print("\n[3] Touch WSGI module:")
    sh(ssh, "touch /var/www/html/vidgenerator/run.py 2>/dev/null || true")
    sh(ssh, "touch /var/www/html/src/app/__init__.py 2>/dev/null || true")
    print("  Touched")

    # Restart uwsgi-vidgenerator with systemctl (no wait for output)
    print("\n[4] Restart uwsgi-vidgenerator:")
    ssh.exec_command("systemctl restart uwsgi-vidgenerator &", timeout=10)
    print("  Restart command sent, waiting 15s...")
    time.sleep(15)

    # Check status
    print("\n[5] Check status:")
    status = sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=10)
    print(f"  uwsgi-vidgenerator: {status}")

    # Test routes
    print("\n[6] Test routes:")
    for r in ["/vidgenerator/api/health", "/vidgenerator/api/gallery/list", "/vidgenerator/lab"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null", timeout=10)
        print(f"  {r}: {code}")

    # Reload nginx
    print("\n[7] Reload nginx:")
    sh(ssh, "systemctl reload nginx 2>&1 || true", timeout=10)
    print("  Done")

    ssh.close()
    print("\n" + "=" * 60)
    print("Test: https://masternoder.dk/vidgenerator/lab")
    print("=" * 60)


if __name__ == "__main__":
    main()
