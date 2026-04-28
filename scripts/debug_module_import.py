#!/usr/bin/env python3
"""Debug why backend.routes.gallery_routes can't be imported."""
import os
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
    print("DEBUG MODULE IMPORT")
    print("=" * 60)

    print("\n[1] Check uwsgi.ini pythonpath:")
    print(sh(ssh, "grep pythonpath /var/www/html/vidgenerator/uwsgi.ini"))

    print("\n[2] Check if backend/routes/gallery_routes.py exists:")
    print(sh(ssh, "ls -la /var/www/html/backend/routes/gallery_routes.py"))

    print("\n[3] Check if backend/__init__.py exists:")
    print(sh(ssh, "ls -la /var/www/html/backend/__init__.py 2>&1"))

    print("\n[4] Check if backend/routes/__init__.py exists:")
    print(sh(ssh, "ls -la /var/www/html/backend/routes/__init__.py 2>&1"))

    print("\n[5] Check what's in /var/www/html/vidgenerator/backend/:")
    print(sh(ssh, "ls -la /var/www/html/vidgenerator/backend/ 2>&1 | head -10"))

    print("\n[6] Try importing with explicit path:")
    result = sh(ssh, '''cd /var/www/html && python3 -c "
import sys
print('sys.path:', sys.path[:5])
print()
sys.path.insert(0, '/var/www/html')
print('After adding /var/www/html to sys.path:')
print('sys.path:', sys.path[:5])
print()
try:
    import backend
    print('backend module:', backend)
    print('backend.__file__:', backend.__file__)
except Exception as e:
    print('Cannot import backend:', e)
try:
    import backend.routes
    print('backend.routes:', backend.routes)
except Exception as e:
    print('Cannot import backend.routes:', e)
try:
    from backend.routes import gallery_routes
    print('gallery_routes:', gallery_routes)
except Exception as e:
    print('Cannot import gallery_routes:', e)
" 2>&1''')
    print(result)

    print("\n[7] Check if there's a symlink or different backend in vidgenerator:")
    print(sh(ssh, "ls -la /var/www/html/vidgenerator/ | grep backend"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
