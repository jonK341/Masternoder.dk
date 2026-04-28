#!/usr/bin/env python3
"""
Deploy and start the second uWSGI backend on port 5001 (same app, load spreading).
Run from your PC:  python scripts/enable_second_backend.py

Writes systemd/uwsgi-vidgenerator-5001.service to /etc/systemd/system/,
daemon-reloads, enables and starts uwsgi-vidgenerator-5001. Run enable_nginx_upstream.py
first so nginx sends traffic to both 5000 and 5001.
"""
import base64
import os
import sys

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def main():
    unit_path = os.path.join(PROJECT_ROOT, "systemd", "uwsgi-vidgenerator-5001.service")
    if not os.path.isfile(unit_path):
        print(f"[ERROR] Not found: {unit_path}")
        return 1

    with open(unit_path, "r", encoding="utf-8") as f:
        unit_content = f.read()

    print("=" * 60)
    print("Enable second backend (uWSGI on port 5001)")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        return 1

    b64 = base64.b64encode(unit_content.encode()).decode()
    run(ssh, f"echo '{b64}' | base64 -d > /etc/systemd/system/uwsgi-vidgenerator-5001.service", timeout=10)
    run(ssh, "systemctl daemon-reload", timeout=10)
    run(ssh, "systemctl enable uwsgi-vidgenerator-5001 2>/dev/null || true", timeout=5)
    run(ssh, "systemctl start uwsgi-vidgenerator-5001", timeout=15)

    status, _ = run(ssh, "systemctl is-active uwsgi-vidgenerator-5001 2>/dev/null || true")
    if status == "active":
        print("[OK] uwsgi-vidgenerator-5001 is active. Port 5001 is now a second backend.")
    else:
        print(f"[WARN] uwsgi-vidgenerator-5001 status: {status}. Check: journalctl -u uwsgi-vidgenerator-5001 -n 30")

    ssh.close()
    print("Ensure nginx uses both backends: python scripts/enable_nginx_upstream.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
