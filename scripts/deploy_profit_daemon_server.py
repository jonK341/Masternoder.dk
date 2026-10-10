#!/usr/bin/env python3
"""Deploy profit daemon stack to masternoder.dk and install systemd 24/7 service."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

REMOTE_ROOT = "/var/www/html"

UPLOAD = [
    "scripts/all_profit_daemons.py",
    "scripts/run_profit_daemon_server.sh",
    "scripts/install_profit_daemon_server.sh",
    "scripts/exchange_master_daemon.py",
    "scripts/daemon_env.py",
    "scripts/_daemon_env.cmd",
    "systemd/masternoder-profit-daemon.service",
    "backend/services/profit_daemon_monitor_service.py",
    "backend/services/profit_daemon_news_service.py",
    "backend/routes/profit_daemon_routes.py",
    "backend/register_blueprints.py",
    "backend/routes/all_page_routes.py",
    "profit/index.html",
    "static/js/profit-daemon-monitor.js",
    "static/css/profit-daemon-monitor.css",
    "static/js/frontpage-home.js",
    "static/js/navigation-toolbar.js",
    "data/exchange_shop_catalog.json",
    "data/crypto_exchange/payout_config.json",
    "cron/exchange_master_tick.sh",
]


def main() -> int:
    from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        for rel in UPLOAD:
            local = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.isfile(local):
                print(f"SKIP missing {rel}")
                continue
            remote = f"{REMOTE_ROOT}/{rel.replace(chr(92), '/')}"
            rdir = os.path.dirname(remote)
            parts = rdir.split("/")
            cur = ""
            for part in parts:
                if not part:
                    continue
                cur += "/" + part
                try:
                    sftp.stat(cur)
                except OSError:
                    try:
                        sftp.mkdir(cur)
                    except OSError:
                        pass
            sftp.put(local, remote)
            print(f"  uploaded {rel}")
        sftp.close()

        cmd = (
            f"cd {REMOTE_ROOT} && "
            "chmod +x scripts/run_profit_daemon_server.sh scripts/install_profit_daemon_server.sh && "
            "bash scripts/install_profit_daemon_server.sh && "
            "grep -E '^EXCHANGE_(PAYOUT_PAYPAL_LIVE|AUTO_PAYPAL_SWEEP)=' .env | head -5 && "
            "systemctl is-active masternoder-profit-daemon.service"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if out.strip():
            print(out.strip())
        if err.strip():
            print(err.strip()[-1200:])

        verify = (
            f"cd {REMOTE_ROOT} && set -a && . ./.env && set +a && "
            "LITE_APP=1 DAEMON_QUIET=1 .venv/bin/python -c "
            "\"from backend.services.profit_daemon_monitor_service import monitor_status; "
            "import json; print(json.dumps(monitor_status(), indent=2)[:2000])\""
        )
        _, vout, _ = ssh.exec_command(verify, timeout=90)
        print("--- monitor ---")
        print(vout.read().decode(errors="replace")[:2000])
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
