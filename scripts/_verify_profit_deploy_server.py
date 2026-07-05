#!/usr/bin/env python3
"""Restart uwsgi + wait for exchange heartbeat after deploy."""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 60) -> str:
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return ((o.read() or b"") + (e.read() or b"")).decode("utf-8", errors="replace")


def main() -> int:
    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        print("Restarting uwsgi...")
        print(sh(ssh, "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001; sleep 4; systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001"))
        print("Waiting 130s for first exchange tick...")
        time.sleep(130)
        raw = sh(ssh, "curl -sS -m 25 http://127.0.0.1:5000/api/profit-daemon/status")
        data = json.loads(raw)
        slim = {k: data.get(k) for k in ("running", "health", "exchange_alive", "heartbeat_updated_at", "loops")}
        print(json.dumps(slim, indent=2))
        print("\n--- stdout tail ---")
        print(sh(ssh, "tail -n 12 /var/www/html/logs/profit_daemon_stdout.log"))
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
