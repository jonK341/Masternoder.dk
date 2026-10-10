#!/usr/bin/env python3
"""Run Binance withdraw preflight on production via SSH (read-only)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_CMD = (
    "cd /var/www/html && "
    "set -a && [ -f .env ] && . ./.env && set +a; "
    "python3 -c "
    "\"import json, os, sys; sys.path.insert(0, '/var/www/html'); os.chdir('/var/www/html'); "
    "from backend.services.exchange_payout_service import binance_preflight_status; "
    "print(json.dumps(binance_preflight_status(150.0), indent=2))\""
)


def main() -> int:
    pw = require_deploy_pass()
    ssh, auth, _ = connect_deploy_ssh(pw)
    print(f"Connected ({auth})")
    stdin, stdout, stderr = ssh.exec_command(REMOTE_CMD, timeout=90)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out)
    if err.strip():
        print("STDERR:", err, file=sys.stderr)
    ssh.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
