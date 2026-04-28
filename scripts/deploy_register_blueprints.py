#!/usr/bin/env python3
"""Deploy updated register_blueprints.py to vidgenerator/backend/."""
import os
import time
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
LOCAL_BASE = r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk"


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
    sftp = ssh.open_sftp()

    print("=" * 60)
    print("DEPLOY REGISTER_BLUEPRINTS.PY")
    print("=" * 60)

    # Backup existing file
    print("\n[1] Backup existing file:")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    sh(ssh, f"cp /var/www/html/vidgenerator/backend/register_blueprints.py /var/www/html/vidgenerator/backend/register_blueprints.py.backup.{timestamp}")
    print(f"  Backed up to register_blueprints.py.backup.{timestamp}")

    # Deploy updated file
    print("\n[2] Deploy updated register_blueprints.py:")
    local = os.path.join(LOCAL_BASE, "backend/register_blueprints.py")
    remote = "/var/www/html/vidgenerator/backend/register_blueprints.py"
    sftp.put(local, remote)
    print(f"  {local} -> {remote}")

    sftp.close()

    # Clear pycache
    print("\n[3] Clear pycache:")
    sh(ssh, "find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
    print("  Cleared")

    # Restart uwsgi
    print("\n[4] Restart uwsgi-vidgenerator:")
    ssh.exec_command("systemctl restart uwsgi-vidgenerator &", timeout=10)
    print("  Restart command sent, waiting 25s...")
    time.sleep(25)

    # Check status
    status = sh(ssh, "systemctl is-active uwsgi-vidgenerator", timeout=10)
    print(f"  Status: {status}")

    # Test routes
    print("\n[5] Test routes:")
    for r in ["/api/gallery/list", "/api/shop-v3/items", "/api/categories/list"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null", timeout=10)
        print(f"  {r}: {code}")

    # Test public URLs
    print("\n[6] Test public URLs:")
    for r in ["/vidgenerator/api/gallery/list", "/vidgenerator/api/shop-v3/items"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{r}' 2>/dev/null", timeout=10)
        print(f"  https://masternoder.dk{r}: {code}")

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
