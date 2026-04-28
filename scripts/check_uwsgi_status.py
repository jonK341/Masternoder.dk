#!/usr/bin/env python3
"""Check uwsgi status and logs."""
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
        return out
    except Exception as e:
        return f"ERROR: {e}"


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("CHECK UWSGI STATUS")
    print("=" * 60)

    # Wait for service to fully start
    print("\n[1] Wait and check service status:")
    for i in range(5):
        status = sh(ssh, "systemctl is-active uwsgi-vidgenerator", timeout=10)
        print(f"  Attempt {i+1}: {status}")
        if status == "active":
            break
        time.sleep(5)

    # If still not active, try restarting
    if status != "active":
        print("\n[2] Service not active, forcing restart...")
        sh(ssh, "systemctl stop uwsgi-vidgenerator || true", timeout=30)
        time.sleep(3)
        sh(ssh, "systemctl start uwsgi-vidgenerator", timeout=30)
        time.sleep(10)
        status = sh(ssh, "systemctl is-active uwsgi-vidgenerator", timeout=10)
        print(f"  After restart: {status}")

    # Check uwsgi log for errors
    print("\n[3] Recent uwsgi log (last 30 lines):")
    print(sh(ssh, "tail -30 /var/www/html/vidgenerator/uwsgi.log 2>&1"))

    # Test routes
    print("\n[4] Test routes:")
    for r in ["/api/gallery/list", "/api/shop-v3/items", "/lab"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null", timeout=10)
        print(f"  {r}: {code}")

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
