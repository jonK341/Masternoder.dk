#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose 404 - check uwsgi config and test routes."""
import os
import paramiko
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out + ("\n" + err if err else "")


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("DIAGNOSE 404 - UWSGI CONFIG AND ROUTES")
    print("=" * 60)

    print("\n[1] uwsgi-vidgenerator config:")
    print(sh(ssh, "cat /etc/uwsgi/apps-enabled/vidgenerator.ini 2>/dev/null || cat /etc/uwsgi/vidgenerator.ini 2>/dev/null || echo 'checking apps-available...'"))
    print(sh(ssh, "cat /etc/uwsgi/apps-available/vidgenerator.ini 2>/dev/null | head -30 || echo 'not in apps-available'"))

    print("\n[2] Test known working routes via :5000:")
    routes_to_test = [
        "/",
        "/api/health",
        "/vidgenerator/",
        "/vidgenerator/api/health",
        "/vidgenerator/api/debug/all-systems",
    ]
    for r in routes_to_test:
        code = sh(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:5000{r}' 2>/dev/null")
        print(f"  {r}: {code}")

    print("\n[3] Check what WSGI module uwsgi loads:")
    print(sh(ssh, "grep -i 'module\\|wsgi\\|chdir\\|pythonpath' /etc/uwsgi/apps-enabled/vidgenerator.ini 2>/dev/null || echo 'not found'"))

    print("\n[4] Check src/app structure on server:")
    print(sh(ssh, "ls -la /var/www/html/src/ 2>/dev/null"))
    print(sh(ssh, "ls -la /var/www/html/src/app/ 2>/dev/null"))
    print(sh(ssh, "ls -la /var/www/html/src/db/ 2>/dev/null"))

    print("\n[5] Test gallery route both ways:")
    print("  Direct /vidgenerator/api/gallery/list:", sh(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/gallery/list' 2>/dev/null | head -c 300"))
    print("  Stripped /api/gallery/list:", sh(ssh, "curl -s 'http://127.0.0.1:5000/api/gallery/list' 2>/dev/null | head -c 300"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
