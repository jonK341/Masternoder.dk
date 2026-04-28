#!/usr/bin/env python3
"""
On the server: show what is using port 5000 and 5003, stop it, then restart uWSGI.

Usage: python scripts/stop_ports_5000_5003_restart_uwsgi.py
"""
import os
import sys
import time

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)


def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    except Exception:
        out, err = "", ""
    return out, err


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    print("=" * 60)
    print("Port 5000 and 5003: what is listening")
    print("=" * 60)
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5003 ' || true")
    if out:
        for line in out.splitlines():
            print(" ", line)
    else:
        print("  (nothing on 5000 or 5003)")
    out, _ = run(ssh, "ps aux | grep -E '[u]wsgi|[g]unicorn|[p]ython.*5000|[p]ython.*5003' 2>/dev/null || true")
    if out:
        print("\nRelevant processes:")
        for line in out.splitlines()[:15]:
            print(" ", line[:100])
    print()

    print("=== Stopping services and killing processes ===")
    run(ssh, "systemctl stop uwsgi 2>/dev/null; systemctl stop uwsgi-vidgenerator 2>/dev/null; systemctl stop python-proxy 2>/dev/null; true")
    time.sleep(2)
    run(ssh, "pkill -9 -f uwsgi 2>/dev/null || true")
    run(ssh, "pkill -9 -f gunicorn 2>/dev/null || true")
    time.sleep(2)
    run(ssh, "fuser -k 5000/tcp 2>/dev/null || true")
    run(ssh, "fuser -k 5003/tcp 2>/dev/null || true")
    time.sleep(2)

    print("=== Verify ports are free ===")
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep -E ':5000 |:5003 ' || true")
    if out:
        print("  WARN: Still in use:", out)
    else:
        print("  Port 5000 and 5003 are free.")
    print()

    print("=== Ensure symlink and start uWSGI ===")
    run(ssh, "systemctl start uwsgi-vidgenerator", timeout=25)
    time.sleep(5)

    print("=== Verify ===")
    out, _ = run(ssh, "ss -tlnp 2>/dev/null | grep 5000 || true")
    print("  Port 5000:", out.strip() if out else "(nothing)")
    out, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null || true")
    print("  uwsgi-vidgenerator service:", out.strip())
    code_out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:5000/ 2>/dev/null || echo 000")
    print("  HTTP GET :5000:", code_out if code_out else "timeout/fail")

    ssh.close()
    print("\nDone. If site still 502, run: python fix_502.py")


if __name__ == "__main__":
    main()
