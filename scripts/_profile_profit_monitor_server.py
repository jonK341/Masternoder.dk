#!/usr/bin/env python3
"""Profile profit monitor_status steps on server."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"
PY = (
    "cd /var/www/html && set -a && . ./.env 2>/dev/null; set +a && "
    "python3 -c \""
    "import time, json\\n"
    "def t(label, fn):\\n"
    "    s=time.time(); r=fn(); print(label, round(time.time()-s,2), 's', type(r).__name__); return r\\n"
    "from backend.services import crypto_exchange_service as ex\\n"
    "t('read_hb', lambda: ex._read_json('logs/daemon_all_profit_heartbeat.json', {}))\\n"
    "t('payout', lambda: __import__('backend.services.exchange_payout_service', fromlist=['payout_status']).payout_status())\\n"
    "t('treasury', lambda: __import__('backend.services.exchange_treasury_service', fromlist=['treasury_status']).treasury_status())\\n"
    "t('ppp', lambda: __import__('backend.services.exchange_profit_path_service', fromlist=['profit_path_summary']).profit_path_summary(hours=24))\\n"
    "t('critical', lambda: __import__('backend.services.exchange_profit_agent_skills_service', fromlist=['critical_problems_top25']).critical_problems_top25(refresh=False))\\n"
    "t('venue_binance', lambda: __import__('backend.services.exchange_venue_api_service', fromlist=['parse_spot_balances']).parse_spot_balances('binance', dry_run=False))\\n"
    "t('monitor', lambda: __import__('backend.services.profit_daemon_monitor_service', fromlist=['monitor_status']).monitor_status())\\n"
    "\""
)


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        _, o, e = ssh.exec_command(PY, timeout=120)
        out = (o.read() or b"") + (e.read() or b"")
        print(out.decode("utf-8", errors="replace"))
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
