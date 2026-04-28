#!/usr/bin/env python3
"""List all routes containing gallery or shop on the server."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=180):
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
    print("LIST ALL GALLERY/SHOP ROUTES ON SERVER")
    print("=" * 60)

    # List routes via Flask app
    result = sh(ssh, '''cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 << 'PYCODE'
import sys
sys.path.insert(0, "/var/www/html")
sys.path.insert(0, "/var/www/html/vidgenerator")
import os
os.chdir("/var/www/html/vidgenerator")

import contextlib
with open(os.devnull, "w") as devnull:
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        from src.app import create_app
        app = create_app()

print("Routes containing 'gallery' or 'shop' or 'lab':")
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    rule = r.rule
    if "gallery" in rule or "shop" in rule or "/lab" in rule:
        methods = list(r.methods - {"OPTIONS", "HEAD"})
        print(f"  {rule} [{methods}]")

print()
print("Routes ending with '/list':")
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if r.rule.endswith("/list"):
        methods = list(r.methods - {"OPTIONS", "HEAD"})
        print(f"  {r.rule} [{methods}]")
PYCODE
''', timeout=180)
    print(result)

    # Check register_blueprints.py output during import
    print("\n[2] Check if gallery_bp import works:")
    result = sh(ssh, '''cd /var/www/html && python3 -c "
import sys
sys.path.insert(0, '/var/www/html')
sys.path.insert(0, '/var/www/html/vidgenerator')

try:
    from backend.routes.gallery_routes import gallery_bp
    print('gallery_bp imported OK')
    print('Routes in blueprint:')
    for func, rule in gallery_bp.deferred_functions:
        print(f'  {rule}')
except Exception as e:
    print(f'Import error: {e}')
" 2>&1''', timeout=30)
    print(result)

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
