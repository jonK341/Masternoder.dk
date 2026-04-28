#!/usr/bin/env python3
"""Fix PYTHONPATH in uwsgi.ini to include /var/www/html so backend module is found."""
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
    print("FIX PYTHONPATH IN UWSGI.INI")
    print("=" * 60)

    # Check current uwsgi.ini
    print("\n[1] Current uwsgi.ini pythonpath:")
    print(sh(ssh, "grep -n 'pythonpath' /var/www/html/vidgenerator/uwsgi.ini 2>&1"))

    # Add /var/www/html to pythonpath if not already there
    print("\n[2] Add /var/www/html to pythonpath:")
    result = sh(ssh, '''
# Check if /var/www/html is already in pythonpath
if grep -q "pythonpath = /var/www/html$" /var/www/html/vidgenerator/uwsgi.ini; then
    echo "Already has /var/www/html in pythonpath"
else
    # Add after existing pythonpath line
    sed -i '/^pythonpath = \\/var\\/www\\/html\\/vidgenerator$/a pythonpath = /var/www/html' /var/www/html/vidgenerator/uwsgi.ini
    echo "Added /var/www/html to pythonpath"
fi
''')
    print(result)

    # Verify the change
    print("\n[3] Verify uwsgi.ini pythonpath:")
    print(sh(ssh, "grep -n 'pythonpath' /var/www/html/vidgenerator/uwsgi.ini 2>&1"))

    # Restart uwsgi
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
    for r in ["/vidgenerator/api/gallery/list", "/vidgenerator/api/shop-v3/items", "/vidgenerator/lab"]:
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
