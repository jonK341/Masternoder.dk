#!/usr/bin/env python3
"""One-shot server diagnostic: profit daemon heartbeat vs monitor API."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 45) -> str:
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return ((o.read() or b"") + (e.read() or b"")).decode("utf-8", errors="replace")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        print("\n--- systemd ---")
        print(sh(ssh, "systemctl is-active masternoder-profit-daemon.service; pgrep -af all_profit_daemons | head -3"))

        print("\n--- heartbeat file ---")
        print(sh(ssh, "ls -la /var/www/html/logs/daemon_all_profit_heartbeat.json 2>&1"))
        print(sh(ssh, "sudo -u www-data test -r /var/www/html/logs/daemon_all_profit_heartbeat.json && echo www-data:READABLE || echo www-data:NOT_READABLE"))

        print("\n--- heartbeat content (head) ---")
        print(sh(ssh, "python3 -c \"import json; p='/var/www/html/logs/daemon_all_profit_heartbeat.json'; d=json.load(open(p)); print(json.dumps({k:d.get(k) for k in ['updated_at','mode','profile','loops']}, indent=2)[:1200])\" 2>&1"))

        print("\n--- monitor API (5000) ---")
        raw = sh(ssh, "curl -sS -m 20 http://127.0.0.1:5000/api/profit-daemon/status")
        try:
            data = json.loads(raw)
            slim = {k: data.get(k) for k in (
                "running", "mode", "profile", "stale_threshold_sec",
                "heartbeat_updated_at", "loops", "checked_at",
            )}
            print(json.dumps(slim, indent=2)[:2500])
        except json.JSONDecodeError:
            print(raw[:1500])

        print("\n--- monitor import as www-data ---")
        print(sh(
            ssh,
            "sudo -u www-data bash -c 'cd /var/www/html && LITE_APP=1 python3 -c "
            "\"from backend.services.profit_daemon_monitor_service import monitor_status; "
            "import json; d=monitor_status(); print(json.dumps({k:d.get(k) for k in "
            "[\\\"running\\\",\\\"heartbeat_updated_at\\\",\\\"loops\\\"]}, indent=2))\"' 2>&1",
        ))

        print("\n--- public HTTPS ---")
        print(sh(ssh, "curl -sS -m 25 https://masternoder.dk/api/profit-daemon/status | python3 -c \"import json,sys; d=json.load(sys.stdin); print('running=',d.get('running'),'loops=',[(x.get('loop'),x.get('age_sec'),x.get('stale')) for x in d.get('loops',[])])\" 2>&1"))

        print("\n--- daemon stdout (tail) ---")
        print(sh(ssh, "tail -n 35 /var/www/html/logs/profit_daemon_stdout.log"))

        print("\n--- daemon stderr (tail) ---")
        print(sh(ssh, "tail -n 15 /var/www/html/logs/profit_daemon_stderr.log 2>/dev/null || echo no stderr"))
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
