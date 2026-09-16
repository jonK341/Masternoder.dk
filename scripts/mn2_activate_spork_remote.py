#!/usr/bin/env python3
"""Activate an MN2 spork on the production server (runs CLI over SSH)."""
from __future__ import annotations

import argparse
import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CLI = "/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config"


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate MN2 spork on production server")
    parser.add_argument("name", nargs="?", default="SPORK_112_EXCHANGE_LIVE_TRADING")
    parser.add_argument("value", nargs="?", type=int, default=1703122560)
    args = parser.parse_args()

    from deploy_ssh_env import connect_deploy_ssh

    remote = f"""set -e
echo "== block height =="
{CLI} getblockcount
echo "== set spork =="
{CLI} spork {args.name} {args.value}
echo "== spork show (target) =="
{CLI} spork show | grep {args.name} || true
echo "== spork active =="
{CLI} spork active | grep {args.name} || true
"""
    ssh = connect_deploy_ssh()[0]
    try:
        _, stdout, stderr = ssh.exec_command(remote, timeout=120)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print(err.rstrip(), file=sys.stderr)
        code = stdout.channel.recv_exit_status()
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
