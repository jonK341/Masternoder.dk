#!/usr/bin/env python3
"""
Add a 1GB swap file on the server if none exists. Use when uWSGI is "Killed" (OOM).
Run from your PC:  python scripts/server_add_swap.py
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def main():
    print("=" * 50)
    print("Add swap on server (if missing)")
    print("=" * 50)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    out, _ = run(ssh, "cat /proc/swaps 2>/dev/null; free -h 2>/dev/null")
    if "swap" in out and "/swapfile" in out:
        print("[OK] Swap already present (e.g. /swapfile)")
        print(out)
        ssh.close()
        return

    print("[1] Creating 1GB swap file...")
    run(ssh, "sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 2>/dev/null", timeout=60)
    run(ssh, "sudo chmod 600 /swapfile")
    run(ssh, "sudo mkswap /swapfile")
    run(ssh, "sudo swapon /swapfile")
    run(ssh, "grep -q '/swapfile' /etc/fstab 2>/dev/null || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")
    print("  [OK] Swap enabled")
    out, _ = run(ssh, "free -h")
    print(out)
    ssh.close()
    print("=" * 50)
    print("Done. Start uWSGI: sudo systemctl start uwsgi-vidgenerator")
    print("=" * 50)


if __name__ == "__main__":
    main()
