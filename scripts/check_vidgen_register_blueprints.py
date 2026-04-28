#!/usr/bin/env python3
"""Check the vidgenerator's register_blueprints.py for gallery registration."""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def sh(ssh, cmd, timeout=60):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        return out
    except Exception as e:
        return f"ERROR: {e}"


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("CHECK VIDGENERATOR REGISTER_BLUEPRINTS.PY")
    print("=" * 60)

    print("\n[1] File info:")
    print(sh(ssh, "ls -la /var/www/html/vidgenerator/backend/register_blueprints.py"))

    print("\n[2] Search for gallery or shop registration:")
    print(sh(ssh, "grep -n 'gallery\\|shop_routes' /var/www/html/vidgenerator/backend/register_blueprints.py | head -20"))

    print("\n[3] Also check /var/www/html/backend/register_blueprints.py:")
    print(sh(ssh, "grep -n 'gallery_routes\\|shop_routes' /var/www/html/backend/register_blueprints.py | head -20"))

    print("\n[4] Where is register_blueprints.py imported from in the app?")
    print(sh(ssh, "grep -rn 'register_blueprints' /var/www/html/src/app/__init__.py /var/www/html/vidgenerator/src/app/__init__.py 2>/dev/null | head -10"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
