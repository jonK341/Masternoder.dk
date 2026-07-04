#!/usr/bin/env python3
"""Verify profit-daemon API timing on server."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return ((o.read() or b"") + (e.read() or b"")).decode("utf-8", errors="replace").strip()


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        for i in range(1, 4):
            out = sh(
                ssh,
                f"curl -sS -m 30 -w '\\nrun={i} http=%{{http_code}} time=%{{time_total}}' "
                f"-o /tmp/profit_status_{i}.json http://127.0.0.1:5000/api/profit-daemon/status",
            )
            print(out)
            meta = sh(
                ssh,
                "python3 -c \"import json; d=json.load(open('/tmp/profit_status_%d.json')); "
                "print('stat_count', d.get('stat_count'), 'blockers', len(d.get('blockers') or []))\""
                % i,
            )
            print(meta)

        prof = sh(ssh, "cd /var/www/html && python3 scripts/_profile_profit_monitor.py 2>/dev/null | tail -10")
        print("\n--- profile ---")
        print(prof)
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
