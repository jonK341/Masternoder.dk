#!/usr/bin/env python3
"""Test blueprint registration manually on server."""
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
    print("TEST BLUEPRINT REGISTRATION ON SERVER")
    print("=" * 60)

    # Test manual blueprint registration
    print("\n[1] Test manual registration with verbose output:")
    result = sh(ssh, '''cd /var/www/html/vidgenerator && /var/www/html/vidgenerator/.venv/bin/python3 << 'PYCODE'
import sys
sys.path.insert(0, "/var/www/html")
sys.path.insert(0, "/var/www/html/vidgenerator")
import os
os.chdir("/var/www/html/vidgenerator")

from flask import Flask
app = Flask(__name__)

# Test importing gallery_bp
print("[TEST] Importing gallery_routes...")
try:
    from backend.routes.gallery_routes import gallery_bp
    print(f"  gallery_bp name: {gallery_bp.name}")
    print(f"  gallery_bp deferred_functions count: {len(gallery_bp.deferred_functions)}")
    app.register_blueprint(gallery_bp)
    print("  [OK] gallery_bp registered")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test importing shop_bp
print("[TEST] Importing shop_routes...")
try:
    from backend.routes.shop_routes import shop_bp
    print(f"  shop_bp name: {shop_bp.name}")
    print(f"  shop_bp deferred_functions count: {len(shop_bp.deferred_functions)}")
    app.register_blueprint(shop_bp)
    print("  [OK] shop_bp registered")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test importing all_page_bp
print("[TEST] Importing all_page_routes...")
try:
    from backend.routes.all_page_routes import all_page_bp
    print(f"  all_page_bp name: {all_page_bp.name}")
    app.register_blueprint(all_page_bp)
    print("  [OK] all_page_bp registered")
except Exception as e:
    print(f"  [ERROR] {e}")

# List routes
print("[RESULT] Routes in test app:")
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if "gallery" in r.rule or "shop-v3" in r.rule or "/lab" in r.rule:
        print(f"  {r.rule}")
PYCODE
''', timeout=180)
    print(result)

    print("\n[2] Check uwsgi startup logs:")
    print(sh(ssh, "tail -100 /var/www/html/vidgenerator/uwsgi.log 2>&1 | grep -i 'gallery\\|shop\\|all_page\\|error registering' | tail -30"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
