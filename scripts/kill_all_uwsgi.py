#!/usr/bin/env python3
"""Kill all uWSGI processes on the server (stop service + pkill any remaining)."""
import os
import sys
import time

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    def run(cmd, timeout=10):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    print("Stopping uWSGI services...")
    run("systemctl stop uwsgi 2>/dev/null || true")
    run("systemctl stop uwsgi-vidgenerator 2>/dev/null || true")
    time.sleep(2)

    print("Killing all uWSGI processes (pkill -9 -f uwsgi)...")
    run("pkill -9 -f uwsgi 2>/dev/null || true")
    time.sleep(1)

    # Force-free port 5000 if something is still bound
    run("fuser -k 5000/tcp 2>/dev/null || true")
    time.sleep(1)

    out, _ = run("ps aux | grep -E '[u]wsgi' 2>/dev/null || true")
    if out.strip():
        print("Remaining uWSGI processes:")
        print(out)
    else:
        print("All uWSGI processes killed. Port 5000 cleared.")
    out, _ = run("ss -tlnp 2>/dev/null | grep 5000 || true")
    if out.strip():
        print("Port 5000 still in use:", out)
    ssh.close()


if __name__ == "__main__":
    main()
