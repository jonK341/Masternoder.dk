#!/usr/bin/env python3
"""Deploy exchange hub frontend + trust/monitor backend to production."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_ROOT = "/var/www/html"

UPLOAD_FILES = [
    # Exchange hub UI
    "exchange/index.html",
    "static/js/exchange-hub.js",
    "static/js/crypto-exchange.js",
    "static/js/agent-marketplace.js",
    "static/css/crypto-exchange.css",
    # Backend routes + services (monitor/trust/live-watch)
    "backend/routes/crypto_exchange_routes.py",
    "backend/services/exchange_trust_service.py",
    "backend/services/exchange_trading_monitor_service.py",
    "backend/services/exchange_live_watch_service.py",
    "backend/services/exchange_leveling_service.py",
    "backend/services/exchange_agent_learning_service.py",
    "backend/services/agent_marketplace_service.py",
    "backend/services/crypto_exchange_service.py",
    # Profit Path Protocol (research ledger + suggestions)
    "backend/services/exchange_profit_path_service.py",
    "backend/services/exchange_swap_rotation_service.py",
    "backend/services/exchange_profit_baseline_service.py",
    "backend/services/exchange_profit_agent_skills_service.py",
    "backend/services/exchange_ai_trading_service.py",
    "backend/services/exchange_payout_service.py",
    "backend/services/exchange_arbitrage_service.py",
    "backend/services/exchange_live_execution_service.py",
    "backend/services/crypto_exchange_agent_service.py",
    "backend/services/exchange_payout_service.py",
    # Config (safe defaults; does not overwrite runtime state dirs)
    "data/exchange_trust_config.json",
    "data/crypto_exchange/profit_path_protocol.json",
]


def upload_files(ssh) -> int:
    sftp = ssh.open_sftp()
    n = 0
    try:
        for rel in UPLOAD_FILES:
            local = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.isfile(local):
                print(f"  skip missing local {rel}")
                continue
            remote = f"{REMOTE_ROOT}/{rel.replace(chr(92), '/')}"
            remote_dir = os.path.dirname(remote).replace(chr(92), "/")
            parts = remote_dir.replace(REMOTE_ROOT, "").strip("/").split("/")
            cur = REMOTE_ROOT
            for part in parts:
                if not part:
                    continue
                cur = f"{cur}/{part}"
                try:
                    sftp.stat(cur)
                except OSError:
                    sftp.mkdir(cur)
            sftp.put(local, remote)
            print(f"  uploaded {rel}")
            n += 1
    finally:
        sftp.close()
    return n


def main() -> int:
    print(f"Deploying {len(UPLOAD_FILES)} exchange hub file(s) to {REMOTE_ROOT} ...")
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        n = upload_files(ssh)
        print(f"Uploaded {n} file(s). Restarting uwsgi ...")
        cmd = (
            "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1; "
            "sleep 4; "
            "systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
        if out:
            print(out)
        if err:
            print(err)
        verify = (
            "curl -s -o /dev/null -w 'trust:%{http_code} ' http://127.0.0.1:5000/api/exchange/trust/me; "
            "curl -s -o /dev/null -w 'monitor:%{http_code} ' http://127.0.0.1:5000/api/exchange/monitor/live; "
            "curl -s -o /dev/null -w 'watch:%{http_code}\\n' "
            "'http://127.0.0.1:5000/api/exchange/live-watch?limit=3'"
        )
        _, stdout, _ = ssh.exec_command(verify, timeout=30)
        print("Verify:", stdout.read().decode().strip())
        print("Done.")
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
