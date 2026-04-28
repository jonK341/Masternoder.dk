#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic check: run server checks by subcommand (no deploy).
Usage:
  python scripts/check.py server   # df + key dirs
  python scripts/check.py routes   # curl :5000 + nginx
  python scripts/check.py uwsgi   # systemctl + socket
  python scripts/check.py disk    # same as server_cleanup_scan report (quick)
"""
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"


def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def cmd_server(ssh):
    print("--- disk (df) ---")
    out, _ = run_cmd(ssh, "df -h / /var 2>/dev/null | tail -5")
    print(out or "(no output)")
    print("--- /var usage ---")
    out, _ = run_cmd(ssh, "du -sh /var/cache /var/log /var/www 2>/dev/null")
    print(out or "(no output)")


def cmd_routes(ssh):
    print("--- upstream :5000 ---")
    out, _ = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null || echo 000")
    print("HTTP", out or "000")
    print("--- nginx test ---")
    out, _ = run_cmd(ssh, "nginx -t 2>&1")
    print(out or "(no output)")


def cmd_uwsgi(ssh):
    print("--- uwsgi-vidgenerator ---")
    out, _ = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null; systemctl status uwsgi-vidgenerator --no-pager 2>/dev/null | head -5")
    print(out or "(no output)")
    print("--- socket ---")
    out, _ = run_cmd(ssh, "ls -la /var/www/html/vidgenerator/*.sock /run/uwsgi/*/*.sock 2>/dev/null || echo 'no sockets'")
    print(out or "no sockets")


def cmd_disk(ssh):
    print("--- disk ---")
    out, _ = run_cmd(ssh, "df -h / 2>/dev/null; du -sh /var/cache/nginx /var/cache/apt/archives /var/www/html/vidgenerator/videos 2>/dev/null")
    print(out or "(no output)")


def main():
    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)

    sub = (sys.argv[1:] or ["server"])[0].lower()
    handlers = {"server": cmd_server, "routes": cmd_routes, "uwsgi": cmd_uwsgi, "disk": cmd_disk}
    if sub not in handlers:
        print("Usage: python scripts/check.py [server|routes|uwsgi|disk]")
        sys.exit(1)

    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
        handlers[sub](ssh)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
