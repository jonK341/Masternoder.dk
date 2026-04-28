#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose why /vidgenerator/lab and new APIs return 404."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out + ("\n" + err if err else "")


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("DIAGNOSE 404 ON NEW ROUTES")
    print("=" * 60)

    print("\n[1] Nginx vidgenerator locations:")
    print(sh(ssh, "nginx -T 2>/dev/null | grep -A5 'location.*vidgenerator' | head -80"))

    print("\n[2] Test app directly on :5000:")
    print("  /vidgenerator/lab:", sh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/vidgenerator/lab 2>/dev/null || echo failed"))
    print("  /vidgenerator/api/gallery/list:", sh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/vidgenerator/api/gallery/list 2>/dev/null || echo failed"))
    print("  /vidgenerator/api/shop-v3/items:", sh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/vidgenerator/api/shop-v3/items 2>/dev/null || echo failed"))

    print("\n[3] Check if files exist on server:")
    print(sh(ssh, "ls -la /var/www/html/backend/routes/gallery_routes.py /var/www/html/backend/routes/shop_routes.py /var/www/html/vidgenerator/lab/index.html 2>&1"))

    print("\n[4] Check blueprint import on server:")
    print(sh(ssh, "cd /var/www/html && python3 -c 'from backend.routes.gallery_routes import gallery_bp; print(\"gallery_bp OK\")' 2>&1"))
    print(sh(ssh, "cd /var/www/html && python3 -c 'from backend.routes.shop_routes import shop_bp; print(\"shop_bp OK\")' 2>&1"))

    print("\n[5] Check all_page_routes has lab:")
    print(sh(ssh, "grep -n 'lab' /var/www/html/backend/routes/all_page_routes.py 2>&1 | head -10"))

    print("\n[6] Check register_blueprints has gallery:")
    print(sh(ssh, "grep -n 'gallery' /var/www/html/backend/register_blueprints.py 2>&1 | head -10"))

    print("\n[7] Service status:")
    print("  python-proxy:", sh(ssh, "systemctl is-active python-proxy 2>&1"))
    print("  uwsgi-vidgenerator:", sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
