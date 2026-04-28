#!/usr/bin/env python3
"""Debug why gallery_routes fails while shop_routes works."""
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
    print("DEBUG GALLERY IMPORT")
    print("=" * 60)

    print("\n[1] Check if gallery_routes.py was deployed:")
    print(sh(ssh, "ls -la /var/www/html/vidgenerator/backend/routes/gallery_routes.py"))

    print("\n[2] Try importing gallery_routes directly:")
    print(sh(ssh, '''cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 -c "
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
sys.path.insert(0, '/var/www/html')
from backend.routes.gallery_routes import gallery_bp
print('gallery_bp:', gallery_bp)
print('gallery_bp.name:', gallery_bp.name)
# Try to see what routes it has
from flask import Flask
app = Flask(__name__)
app.register_blueprint(gallery_bp)
for r in app.url_map.iter_rules():
    if 'gallery' in r.rule or 'categories' in r.rule:
        print(f'  {r.rule}')
" 2>&1'''))

    print("\n[3] Check uwsgi log for gallery errors:")
    print(sh(ssh, "tail -50 /var/www/html/vidgenerator/uwsgi.log 2>&1 | grep -i 'gallery\\|error.*import' | tail -15"))

    print("\n[4] Check register_blueprints.py for gallery_bp registration:")
    print(sh(ssh, "grep -A5 'gallery_routes' /var/www/html/vidgenerator/backend/register_blueprints.py 2>&1 | head -15"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
