#!/usr/bin/env python3
"""One-shot prod treasury liquidity + multiping probe (SSH)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_SCRIPT = "/tmp/mn2_treasury_probe_once.py"
LOCAL_SCRIPT = os.path.join(ROOT, "scripts", "_server_treasury_probe_once.py")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_SCRIPT, REMOTE_SCRIPT)
        sftp.put(
            os.path.join(ROOT, "scripts", "mn2_probe_multi_ping.py"),
            "/var/www/html/scripts/mn2_probe_multi_ping.py",
        )
        sftp.close()
        credit = os.environ.get("TREASURY_TEST_CREDIT_MN2", "10000")
        cmd = (
            f"cd /var/www/html && export DAEMON_QUIET=1 LITE_APP=1 TREASURY_TEST_CREDIT_MN2={credit} && "
            f"python3 {REMOTE_SCRIPT} && "
            "python3 scripts/mn2_probe_multi_ping.py 2>&1"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if out.strip():
            print(out.strip())
        if err.strip():
            print(err.strip()[-1500:], file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
