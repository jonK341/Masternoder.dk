#!/usr/bin/env python3
"""
Kill all app-related processes on the Ubuntu server (uwsgi, gunicorn, python-proxy)
and free port 5000. Optionally reboot the server.

Usage:
  python scripts/kill_all_app_processes.py          # kill processes only
  python scripts/kill_all_app_processes.py --reboot # kill then reboot server
"""
import os
import sys
import time
import argparse
import socket

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def main():
    ap = argparse.ArgumentParser(description="Kill all app processes on server; optional reboot")
    ap.add_argument("--reboot", action="store_true", help="Reboot the server after killing processes")
    args = ap.parse_args()

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        try:
            out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
            err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        except (TimeoutError, OSError, socket.timeout):
            out, err = "", ""
        return out, err

    # Stop all services in background so SSH doesn't block on slow systemctl
    print("=== Stopping services ===")
    stop_cmd = " ".join(
        f"systemctl stop {s} 2>/dev/null;" for s in ["uwsgi", "uwsgi-vidgenerator", "python-proxy", "vidgenerator-gunicorn"]
    ) + " true"
    stdin, stdout, stderr = ssh.exec_command(f"({stop_cmd}) &", timeout=5)
    # Consume channel so it closes (background job returns immediately)
    try:
        stdout.channel.recv_exit_status()
    except (TimeoutError, OSError, socket.timeout):
        pass
    time.sleep(3)

    print("=== Killing remaining processes ===")
    run("pkill -9 -f uwsgi 2>/dev/null || true")
    run("pkill -9 -f gunicorn 2>/dev/null || true")
    run("pkill -9 -f 'python.*proxy' 2>/dev/null || true")
    time.sleep(1)

    print("=== Freeing port 5000 ===")
    run("fuser -k 5000/tcp 2>/dev/null || true")
    time.sleep(1)

    out, _ = run("ps aux | grep -E '[u]wsgi|[g]unicorn|[p]ython.*proxy' 2>/dev/null || true")
    if out.strip():
        print("Remaining app processes:")
        print(out)
    else:
        print("All app processes killed. Port 5000 cleared.")

    out, _ = run("ss -tlnp 2>/dev/null | grep 5000 || echo ''")
    if out.strip():
        print("Port 5000 still in use:", out)

    if args.reboot:
        print("\n=== Rebooting server ===")
        try:
            # Run in background; connection will drop
            ssh.exec_command("nohup reboot &", timeout=2)
        except Exception:
            pass
        time.sleep(1)
        ssh.close()
        print("Reboot sent. SSH will disconnect. Wait 1–2 min then reconnect or run fix_502.py to start uwsgi.")
        sys.exit(0)

    ssh.close()
    print("\nDone. Run python fix_502.py to start uwsgi again.")


if __name__ == "__main__":
    main()
