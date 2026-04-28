#!/usr/bin/env python3
"""Test routes after pythonpath fix."""
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
    print("TEST AFTER PYTHONPATH FIX")
    print("=" * 60)

    # Check service status
    print("\n[1] Check service status:")
    status = sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=10)
    print(f"  uwsgi-vidgenerator: {status}")

    if status != "active":
        print("\n[2] Service not active, restarting...")
        sh(ssh, "systemctl stop uwsgi-vidgenerator 2>&1 || true", timeout=30)
        time.sleep(5)
        sh(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", timeout=30)
        time.sleep(15)
        status = sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=10)
        print(f"  uwsgi-vidgenerator after restart: {status}")

    # Test routes
    print("\n[3] Test routes:")
    for r in ["/vidgenerator/api/health", "/vidgenerator/api/gallery/list", "/vidgenerator/api/shop-v3/items", "/vidgenerator/lab"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null", timeout=10)
        print(f"  {r}: {code}")

    # Check uwsgi log for errors
    print("\n[4] Recent uwsgi log (looking for gallery):")
    print(sh(ssh, "tail -50 /var/www/html/vidgenerator/uwsgi.log 2>&1 | grep -i 'gallery\\|shop\\|error\\|import' | tail -20"))

    # Test via public URL
    print("\n[5] Test via public https:")
    for r in ["/vidgenerator/", "/vidgenerator/api/gallery/list"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{r}' 2>/dev/null", timeout=10)
        print(f"  https://masternoder.dk{r}: {code}")

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
