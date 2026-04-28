#!/usr/bin/env python3
"""Check wsgi.py on server."""
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
    print("CHECK WSGI.PY ON SERVER")
    print("=" * 60)

    print("\n[1] wsgi.py content:")
    print(sh(ssh, "cat /var/www/html/vidgenerator/wsgi.py 2>&1"))

    print("\n[2] Check if wsgi.py uses src.app or different app:")
    print(sh(ssh, "grep -n 'create_app\\|from src\\|import app\\|Flask' /var/www/html/vidgenerator/wsgi.py 2>&1"))

    print("\n[3] Check run.py:")
    print(sh(ssh, "head -50 /var/www/html/vidgenerator/run.py 2>&1"))

    ssh.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
