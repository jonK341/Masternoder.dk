#!/usr/bin/env python3
"""Restart uwsgi on server and verify /profit/ + API routes."""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = (o.read() or b"") + (e.read() or b"")
    return out.decode("ascii", errors="replace").strip()


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")

    upload = [
        "backend/services/profit_daemon_monitor_service.py",
        "backend/services/exchange_payout_service.py",
        "backend/services/exchange_profit_agent_skills_service.py",
        "backend/services/exchange_treasury_service.py",
        "backend/services/exchange_profit_path_service.py",
        "backend/middleware/signal_processor_middleware.py",
        "backend/routes/profit_daemon_routes.py",
        "backend/routes/crypto_exchange_routes.py",
        "profit/index.html",
        "static/js/profit-daemon-monitor.js",
        "static/css/profit-daemon-monitor.css",
        "exchange/index.html",
        "static/js/exchange-hub.js",
        "static/css/crypto-exchange.css",
        "data/crypto_exchange/profit_critical_top25.json",
        "backend/routes/all_page_routes.py",
        "backend/register_blueprints.py",
    ]
    try:
        sftp = ssh.open_sftp()
        for rel in upload:
            local = os.path.join(ROOT, rel.replace("/", os.sep))
            if os.path.isfile(local):
                sftp.put(local, f"{REMOTE}/{rel}")
                print(f"uploaded {rel}")
        sftp.close()

        print("\n--- restarting uwsgi ---")
        print(sh(ssh, "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1"))
        time.sleep(6)
        print(sh(ssh, "systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001"))

        print("\n--- warmup (cold worker import) ---")
        print(sh(ssh, "curl -sS -m 90 -o /dev/null -w 'warmup http=%{http_code} time=%{time_total}' http://127.0.0.1:5000/api/profit-daemon/status"))

        checks = [
            ("profit_page", "curl -sS -m 25 -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/profit/"),
            ("profit_page_5001", "curl -sS -m 25 -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/profit/"),
            ("exchange_page", "curl -sS -m 25 -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/exchange/"),
            ("profit_api", "curl -sS -m 10 -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/api/profit-daemon/status"),
            ("profit_public", "curl -sS -m 25 -o /dev/null -w '%{http_code}' https://masternoder.dk/vidgenerator/profit/"),
        ]
        print("\n--- verify ---")
        ok = True
        for name, cmd in checks:
            code = sh(ssh, cmd)
            print(f"{name}: HTTP {code}")
            if code not in ("200", "301", "302"):
                ok = False

        timing = sh(
            ssh,
            "curl -sS -m 10 -w '\\ntime_total=%{time_total}' "
            "-o /tmp/profit_status.json http://127.0.0.1:5000/api/profit-daemon/status "
            "&& python3 -c \"import json; d=json.load(open('/tmp/profit_status.json')); "
            "print('stat_count', d.get('stat_count'), 'blockers', len(d.get('blockers') or []))\"",
        )
        print(f"\napi timing: {timing}")
        sample = sh(ssh, "head -c 500 /tmp/profit_status.json 2>/dev/null || curl -sS -m 10 http://127.0.0.1:5000/api/profit-daemon/status | head -c 500")
        print(f"\napi sample: {sample[:400]}")
        return 0 if ok else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
