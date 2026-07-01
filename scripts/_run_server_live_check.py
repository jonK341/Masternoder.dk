#!/usr/bin/env python3
"""Upload server live check script and run it on production."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html/scripts/_server_live_check_once.py"
LOCAL = os.path.join(ROOT, "scripts", "_server_live_check_once.py")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        sftp.put(LOCAL, REMOTE)
        sftp.close()
        cmd = (
            "cd /var/www/html && "
            "export DAEMON_QUIET=1 LITE_APP=1 EXCHANGE_ARBITRAGE_LIVE=1 "
            "EXCHANGE_LIVE_PROFIT_MAX=1 BINANCE_QUOTE=USDC && "
            "python3 scripts/remote_vault_import.py 2>&1 | tail -3 && "
            "python3 scripts/_server_live_check_once.py && "
            "grep BINANCE_QUOTE /var/www/html/.env && "
            "head -5 /etc/cron.d/masternoder-exchange-master 2>/dev/null"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if out.strip():
            print(out.strip())
        if err.strip():
            print(err.strip()[-800:])
        return 0 if stdout.channel.recv_exit_status() == 0 else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
