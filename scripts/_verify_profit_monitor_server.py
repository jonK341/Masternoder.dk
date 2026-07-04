#!/usr/bin/env python3
"""Profile + verify profit monitor API on server."""
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
        for rel in (
            "scripts/_profile_profit_monitor.py",
            "backend/services/profit_daemon_monitor_service.py",
            "backend/services/exchange_payout_service.py",
        ):
            sftp.put(os.path.join(ROOT, rel), f"{REMOTE}/{rel}")
        sftp.close()

        def sh(cmd: str, timeout: int = 180) -> str:
            _, o, e = ssh.exec_command(cmd, timeout=timeout)
            return ((o.read() or b"") + (e.read() or b"")).decode("utf-8", errors="replace")

        print("\n--- profile ---")
        prof = sh(
            "cd /var/www/html && set -a && . ./.env 2>/dev/null; set +a && "
            "python3 scripts/_profile_profit_monitor.py 2>/dev/null | "
            "grep -E '^(read_hb|payout|treasury|ppp|critical|venue|monitor)' || true"
        )
        print(prof or "(no timing lines)")

        print("\n--- curl ---")
        curl = sh(
            "systemctl restart uwsgi-vidgenerator 2>/dev/null; sleep 3; "
            "curl -sS -m 20 http://127.0.0.1:5000/api/profit-daemon/status "
            "-w '\\nHTTP:%{http_code} TIME:%{time_total}s SIZE:%{size_download}' | tail -c 900"
        )
        print(curl)
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
