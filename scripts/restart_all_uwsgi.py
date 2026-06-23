#!/usr/bin/env python3
"""Restart both uWSGI backends (5000 + 5001) so nginx load-balancing stays in sync."""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

import paramiko


def main() -> int:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=require_deploy_pass(), timeout=30)
    print("Restarting uWSGI backends (5000 + 5001)...")
    for unit in ("uwsgi-vidgenerator", "uwsgi-vidgenerator-5001", "uwsgi"):
        ssh.exec_command(f"systemctl restart {unit} 2>&1 || true", timeout=20)
        time.sleep(8)
    for port in (5000, 5001):
        stdin, stdout, stderr = ssh.exec_command(
            f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/casino/ 2>/dev/null || echo 000",
            timeout=15,
        )
        code = (stdout.read() or b"").decode().strip()
        print(f"  :{port}/casino/ -> HTTP {code}")
    ssh.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
