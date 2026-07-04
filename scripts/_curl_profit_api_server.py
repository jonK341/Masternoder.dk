#!/usr/bin/env python3
"""Debug profit API via uwsgi on server."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def main() -> int:
    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        cmds = [
            "curl -sS -m 5 -o /dev/null -w 'health:%{http_code} time:%{time_total}\\n' http://127.0.0.1:5000/api/health 2>&1 || true",
            "curl -sS -m 8 -w '\\nHTTP:%{http_code} TIME:%{time_total}\\n' http://127.0.0.1:5000/api/profit-daemon/status 2>&1 | tail -c 500",
            "grep -r profit_daemon /var/www/html/backend/register_blueprints.py 2>/dev/null | head -3",
            "curl -sS -m 8 -w '\\nHTTP:%{http_code} TIME:%{time_total}\\n' https://masternoder.dk/vidgenerator/api/profit-daemon/status 2>&1 | tail -c 500",
        ]
        for cmd in cmds:
            print(f"\n$ {cmd[:80]}...")
            _, o, e = ssh.exec_command(cmd, timeout=30)
            print((o.read() + e.read()).decode("utf-8", errors="replace"))
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
