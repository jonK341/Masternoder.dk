#!/usr/bin/env python3
"""Time monitor_status on server (no Flask HTTP)."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        sftp.put(
            os.path.join(ROOT, "backend/services/profit_daemon_monitor_service.py"),
            f"{REMOTE}/backend/services/profit_daemon_monitor_service.py",
        )
        sftp.put(
            os.path.join(ROOT, "backend/services/exchange_profit_path_service.py"),
            f"{REMOTE}/backend/services/exchange_profit_path_service.py",
        )
        sftp.close()
        cmd = (
            "cd /var/www/html && set -a && . ./.env 2>/dev/null; set +a && "
            "python3 - <<'PY'\n"
            "import os, sys, time\n"
            "os.chdir('/var/www/html')\n"
            "sys.path.insert(0, '/var/www/html')\n"
            "from backend.services.profit_daemon_monitor_service import monitor_status\n"
            "for i in range(3):\n"
            "    t = time.time()\n"
            "    r = monitor_status()\n"
            "    print('run', i, 'stats', r.get('stat_count'), 'sec', round(time.time()-t, 3))\n"
            "PY"
        )
        _, o, e = ssh.exec_command(cmd, timeout=120)
        out = (o.read() + e.read()).decode("utf-8", errors="replace")
        print(out)
        _, o2, _ = ssh.exec_command(
            "tail -30 /var/log/uwsgi/vidgenerator.log 2>/dev/null || "
            "journalctl -u uwsgi-vidgenerator -n 15 --no-pager 2>/dev/null",
            timeout=30,
        )
        print("--- uwsgi log tail ---")
        print((o2.read()).decode("utf-8", errors="replace")[-2000:])
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
