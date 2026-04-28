#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspect which processes listen on key ports on production.
"""
import os
import paramiko

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def _sh(ssh: paramiko.SSHClient, cmd: str, timeout: int = 20) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    try:
        print("=" * 70)
        print("PRODUCTION LISTENER INSPECTION")
        print("=" * 70)
        print("\nss -ltnp (filtered):")
        print(_sh(ssh, "ss -ltnp | grep -E ':(80|443|5000|8080)\\s' || true", timeout=20))
        print("\nps (python-proxy / uwsgi / gunicorn):")
        print(_sh(ssh, "ps aux | grep -E 'python-proxy|python_proxy|uwsgi|gunicorn|flask' | grep -v grep || true", timeout=20))
        print("\nsystemctl status (brief):")
        for svc in ["python-proxy", "python-proxy.service", "uwsgi-vidgenerator", "nginx", "apache2"]:
            print(f"\n-- {svc} --")
            print(_sh(ssh, f"systemctl status {svc} --no-pager -l | sed -n '1,12p' || true", timeout=20))
    finally:
        ssh.close()


if __name__ == "__main__":
    main()

