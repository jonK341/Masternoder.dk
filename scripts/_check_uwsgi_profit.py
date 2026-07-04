#!/usr/bin/env python3
"""Check uwsgi worker health on server."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def main() -> int:
    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        for cmd in [
            "systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001",
            "sleep 2",
            "curl -sS -m 15 -o /dev/null -w '5000/profit:%{http_code} %{time_total}s\\n' http://127.0.0.1:5000/profit/",
            "curl -sS -m 15 -o /dev/null -w '5001/profit:%{http_code} %{time_total}s\\n' http://127.0.0.1:5001/profit/",
            "curl -sS -m 15 -w '\\n5000/api stat:%{http_code} time:%{time_total}s\\n' http://127.0.0.1:5000/api/profit-daemon/status 2>&1 | tail -c 300",
            "curl -sS -m 15 -w '\\n5001/api stat:%{http_code} time:%{time_total}s\\n' http://127.0.0.1:5001/api/profit-daemon/status 2>&1 | tail -c 300",
            "ps aux | grep uwsgi | grep -v grep | head -5",
        ]:
            _, o, e = ssh.exec_command(cmd, timeout=40)
            out = (o.read() + e.read()).decode("utf-8", errors="replace").strip()
            if out:
                print(out)
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
