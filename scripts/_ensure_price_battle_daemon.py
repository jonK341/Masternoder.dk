#!/usr/bin/env python3
"""Ensure price-battle loop daemon is running on prod."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 45) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    # Avoid hanging forever on backgrounded shells.
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    try:
        out = (stdout.read() or b"").decode(errors="replace")
    except Exception as exc:
        out = f"[stdout_timeout:{exc}]"
    try:
        err = (stderr.read() or b"").decode(errors="replace")
    except Exception as exc:
        err = f"[stderr_timeout:{exc}]"
    return (out + (("\nERR:\n" + err) if err.strip() else "")).strip()


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("auth", auth)

    print("--- list ---")
    print(sh(ssh, "ps -ef | grep '[e]xchange_price_battle_daemon.py' || echo none"))

    # Fully detach: stdin closed, stdout/err to log, shell exits immediately.
    print("--- start ---")
    start_cmd = (
        "cd /var/www/html && mkdir -p logs && "
        "( nohup .venv/bin/python -u scripts/exchange_price_battle_daemon.py --interval 120 "
        ">> logs/price_battle_daemon.log 2>&1 < /dev/null & echo $! > logs/price_battle_daemon.pid ) ; "
        "echo started ; cat logs/price_battle_daemon.pid"
    )
    print(sh(ssh, start_cmd, timeout=20))
    time.sleep(3)

    print("--- list2 ---")
    print(sh(ssh, "ps -ef | grep '[e]xchange_price_battle_daemon.py' || echo none"))
    print(sh(ssh, "cat /var/www/html/logs/price_battle_daemon.pid 2>/dev/null || echo no_pid"))

    print("--- log ---")
    print(sh(ssh, "tail -n 25 /var/www/html/logs/price_battle_daemon.log || echo no_log"))

    print("--- positions ---")
    pos_cmd = r"""cd /var/www/html && .venv/bin/python - <<'PY'
import os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_price_battle_service import status, live_enabled
s = status()
print('live', live_enabled())
print('open', s.get('open_count'), 'last', s.get('last_tick'), 'tick', s.get('tick_count'))
for p in s.get('open') or []:
    print('POS', p.get('symbol'), 'entry', p.get('entry_price'), 'qty', p.get('qty'),
          'cost', p.get('cost_usd'), 'mode', p.get('mode'), 'id', p.get('id'))
print('buys_log', s.get('buys_log'))
print('sells_log', s.get('sells_log'))
PY"""
    print(sh(ssh, pos_cmd, timeout=90))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
