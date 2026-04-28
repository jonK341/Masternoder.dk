#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose 404 - test with stripped prefix (what nginx sends to Flask)."""
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
    print("DIAGNOSE 404 - NGINX STRIPS /vidgenerator PREFIX")
    print("=" * 60)

    print("\n[1] Test app with STRIPPED prefix (what nginx sends after rewrite):")
    for path in ["/lab", "/api/gallery/list", "/api/shop-v3/items", "/api/game/shop/items"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000{path} 2>/dev/null || echo failed")
        print(f"  {path}: {code}")

    print("\n[2] Test app WITH /vidgenerator prefix (what browser sends):")
    for path in ["/vidgenerator/lab", "/vidgenerator/api/gallery/list", "/vidgenerator/api/shop-v3/items"]:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000{path} 2>/dev/null || echo failed")
        print(f"  {path}: {code}")

    print("\n[3] List Flask routes with 'gallery' or 'lab' or 'shop':")
    print(sh(ssh, """cd /var/www/html && python3 -c "
from src.app import create_app
app = create_app()
routes = [r.rule for r in app.url_map.iter_rules() if 'gallery' in r.rule or 'lab' in r.rule or 'shop-v3' in r.rule]
for r in sorted(set(routes))[:20]:
    print(r)
" 2>&1 | tail -30"""))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
