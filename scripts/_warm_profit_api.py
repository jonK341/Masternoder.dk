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
    try:
        for i in range(5):
            cmd = (
                f"curl -sS -m 12 -w 'run={i} http=%{{http_code}} time=%{{time_total}}\\n' "
                "-o /dev/null http://127.0.0.1:5000/api/profit-daemon/status"
            )
            _, o, e = ssh.exec_command(cmd, timeout=20)
            print((o.read() + e.read()).decode("utf-8", errors="replace").strip())
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
