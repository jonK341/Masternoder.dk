#!/usr/bin/env python3
"""
SSH Check: Agent Behavior Widget Static File
Verifies where static JS files exist on the production server.
"""
import os
import paramiko

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

PATHS = [
    "/var/www/html/vidgenerator/static/js",
    "/var/www/html/vidgenerator/vidgenerator/static/js",
]


def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    for p in PATHS:
        cmd = f"echo '--- {p}'; ls -la {p} | head -n 25; ls -la {p} | grep agent-behavior || true"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        print(out)
        if err.strip():
            print(err)

    ssh.close()


if __name__ == "__main__":
    run()

