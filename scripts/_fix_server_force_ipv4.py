#!/usr/bin/env python3
"""Append EXCHANGE_FORCE_IPV4=1 to server .env and refresh cron."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass
from scripts.push_exchange_live_server import upsert_remote_key, REMOTE_ROOT


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        sftp.put(
            os.path.join(ROOT, "cron", "exchange_master_tick.sh"),
            f"{REMOTE_ROOT}/cron/exchange_master_tick.sh",
        )
        sftp.close()
        print(f"EXCHANGE_FORCE_IPV4: {upsert_remote_key(ssh, 'EXCHANGE_FORCE_IPV4', '1')}")
        cmd = (
            f"sed -i 's/\\r$//' {REMOTE_ROOT}/cron/exchange_master_tick.sh && "
            f"cp {REMOTE_ROOT}/cron/masternoder-exchange-master.cron.d "
            f"/etc/cron.d/masternoder-exchange-master && "
            f"chmod 644 /etc/cron.d/masternoder-exchange-master && "
            f"grep EXCHANGE_FORCE_IPV4 {REMOTE_ROOT}/.env"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=45)
        print(stdout.read().decode(errors="replace").strip())
        err = stderr.read().decode(errors="replace").strip()
        if err:
            print(err[-300:])
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
