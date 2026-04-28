#!/usr/bin/env python3
"""Stop uwsgi-vidgenerator then start it again (full reset)."""
import os
import sys
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
    err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    return out, err


def _sh_bg(ssh, cmd, wait_sec=10):
    ssh.exec_command(f"nohup bash -c '{cmd}' </dev/null >/dev/null 2>&1 &")
    time.sleep(wait_sec)


def main():
    import paramiko
    print("Connecting to", SERVER_HOST, "...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    try:
        print("Stopping uwsgi-vidgenerator...")
        _sh_bg(ssh, "systemctl stop uwsgi-vidgenerator 2>&1 || true", wait_sec=5)
        # Wait until fully stopped (inactive or failed); stop can take a while
        for i in range(24):
            out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
            out = (out or "").strip()
            print("  Status:", out)
            if out in ("inactive", "failed", ""):
                break
            time.sleep(5)
        else:
            print("  [WARN] Unit still not inactive after 2 min; starting anyway.")
        time.sleep(2)
        print("Starting uwsgi-vidgenerator...")
        _sh_bg(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || true", wait_sec=10)
        for _ in range(8):
            out, _ = _sh(ssh, "systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
            out = (out or "").strip()
            print("  Status:", out)
            if out == "active":
                break
            time.sleep(5)
        print("Done.")
        sys.exit(0 if (out or "").strip() == "active" else 1)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
