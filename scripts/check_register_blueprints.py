#!/usr/bin/env python3
"""Check register_blueprints.py on server for gallery/shop registration."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=30):
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
    print("CHECK REGISTER_BLUEPRINTS.PY ON SERVER")
    print("=" * 60)

    print("\n[1] Check for gallery_routes registration:")
    print(sh(ssh, "grep -n 'gallery_routes\\|gallery_bp' /var/www/html/backend/register_blueprints.py 2>&1"))

    print("\n[2] Check for shop_routes registration:")
    print(sh(ssh, "grep -n 'shop_routes\\|shop_bp\\|shop-v3' /var/www/html/backend/register_blueprints.py 2>&1"))

    print("\n[3] Check for all_page_routes with lab:")
    print(sh(ssh, "grep -n 'all_page\\|lab' /var/www/html/backend/register_blueprints.py 2>&1"))

    print("\n[4] Check gallery_routes.py exists and has correct routes:")
    print(sh(ssh, "head -40 /var/www/html/backend/routes/gallery_routes.py 2>&1"))

    print("\n[5] Check shop_routes.py has shop-v3 route:")
    print(sh(ssh, "grep -n 'shop-v3\\|game/shop' /var/www/html/backend/routes/shop_routes.py 2>&1"))

    print("\n[6] Test importing gallery_routes on server:")
    print(sh(ssh, "cd /var/www/html && python3 -c 'from backend.routes.gallery_routes import gallery_bp; print(\"OK:\", [r.rule for r in gallery_bp.iter_rules()])' 2>&1"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
