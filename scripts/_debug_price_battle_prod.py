#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    cmd = r"""
cd /var/www/html
echo '=== env ==='
grep -E '^(EXCHANGE_PRICE_BATTLE_LIVE|EXCHANGE_ARBITRAGE_LIVE)=' .env | sed 's/=.*/=***/'
echo '=== once ==='
.venv/bin/python scripts/exchange_price_battle_daemon.py --once 2>&1 | tail -c 4000
echo
echo '=== pgrep ==='
pgrep -af exchange_price_battle || echo none
echo '=== log ==='
tail -n 40 logs/price_battle_daemon.log 2>/dev/null || echo no_log
echo '=== restart daemon ==='
pkill -f 'scripts/exchange_price_battle_daemon.py' 2>/dev/null || true
sleep 1
nohup .venv/bin/python -u scripts/exchange_price_battle_daemon.py --interval 120 >> logs/price_battle_daemon.log 2>&1 &
echo started_pid=$!
sleep 3
pgrep -af exchange_price_battle || echo none
tail -n 30 logs/price_battle_daemon.log 2>/dev/null || true
"""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    print((stdout.read() or b"").decode(errors="replace"))
    err = (stderr.read() or b"").decode(errors="replace").strip()
    if err:
        print("STDERR", err[-1000:])
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
