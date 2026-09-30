#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return ((o.read() or b"") + (e.read() or b"")).decode(errors="replace").strip()


def main() -> int:
    ssh, _, _ = connect_deploy_ssh()
    print(sh(ssh, "curl -sS -m 20 -w '\\nHTTP:%{http_code}' 'http://127.0.0.1:5000/api/monetization/streams/hub?metrics=0' | tail -c 600"))
    print(sh(ssh, "grep -r 'streams/hub' /var/www/html/logs/*.log 2>/dev/null | tail -5; journalctl -u uwsgi-vidgenerator -n 20 --no-pager 2>/dev/null | tail -15"))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
