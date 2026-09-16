#!/usr/bin/env python3
"""Fix CRLF on server shell scripts and start profit daemon systemd."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        for rel in ("scripts/run_profit_daemon_server.sh", "scripts/install_profit_daemon_server.sh"):
            sftp.put(os.path.join(ROOT, rel.replace("/", os.sep)), f"{REMOTE}/{rel}")
        sftp.close()
        steps = [
            f"sed -i 's/\\r$//' {REMOTE}/scripts/run_profit_daemon_server.sh {REMOTE}/scripts/install_profit_daemon_server.sh",
            f"chmod +x {REMOTE}/scripts/run_profit_daemon_server.sh {REMOTE}/scripts/install_profit_daemon_server.sh",
            f"bash {REMOTE}/scripts/install_profit_daemon_server.sh",
            "sleep 6",
            "systemctl is-active masternoder-profit-daemon.service",
            f"tail -n 12 {REMOTE}/logs/profit_daemon_stdout.log 2>/dev/null || echo no_log",
        ]
        for cmd in steps:
            print(f"\n$ {cmd}")
            _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            if out.strip():
                print(out.strip())
            if err.strip():
                print(err.strip()[-600:])
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
