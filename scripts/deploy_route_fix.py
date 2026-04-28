#!/usr/bin/env python3
"""Deploy updated gallery_routes.py and shop_routes.py with route prefix fixes."""
import os
import time
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
LOCAL_BASE = r"c:\Users\jonkh\UsecaseSampler\Masternoder.dk"


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()

    print("=" * 60)
    print("DEPLOY ROUTE FIX")
    print("=" * 60)

    files = [
        ("backend/routes/gallery_routes.py", "/var/www/html/backend/routes/gallery_routes.py"),
        ("backend/routes/shop_routes.py", "/var/www/html/backend/routes/shop_routes.py"),
    ]

    for local_rel, remote in files:
        local = os.path.join(LOCAL_BASE, local_rel)
        print(f"Uploading {local_rel}...")
        sftp.put(local, remote)
        print(f"  -> {remote}")

    sftp.close()

    # Clear pycache
    print("\n[1] Clear pycache:")
    stdin, stdout, stderr = ssh.exec_command("find /var/www/html -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo done", timeout=30)
    stdout.read()
    print("  Cleared")

    # Restart uwsgi
    print("\n[2] Restart uwsgi-vidgenerator:")
    ssh.exec_command("systemctl restart uwsgi-vidgenerator &", timeout=10)
    print("  Restart command sent, waiting 15s...")
    time.sleep(15)

    # Check status
    print("\n[3] Check status:")
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=10)
    status = stdout.read().decode().strip()
    print(f"  uwsgi-vidgenerator: {status}")

    # Test routes
    print("\n[4] Test routes:")
    for r in ["/api/gallery/list", "/api/shop-v3/items", "/lab"]:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null", timeout=10)
        code = stdout.read().decode().strip()
        print(f"  {r}: {code}")

    # Test public URL
    print("\n[5] Test public URLs:")
    for r in ["/vidgenerator/api/gallery/list", "/vidgenerator/api/shop-v3/items", "/vidgenerator/lab"]:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{r}' 2>/dev/null", timeout=10)
        code = stdout.read().decode().strip()
        print(f"  https://masternoder.dk{r}: {code}")

    ssh.close()
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
