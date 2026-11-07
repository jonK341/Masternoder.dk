#!/usr/bin/env python3
"""Upload fleet bootstrap module and start long-running 500-slot job on the server."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

WEB = "/var/www/html"
FILES = (
    "backend/services/mn2_fleet_inventory_ops.py",
    "backend/services/mn2_hosting_treasury_ops.py",
    "scripts/mn2_bootstrap_fleet_inventory.py",
)


def sh(ssh, cmd: str, timeout: int = 600) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def upload_files(ssh) -> None:
    sftp = ssh.open_sftp()
    try:
        for rel in FILES:
            local = os.path.join(ROOT, rel)
            remote = f"{WEB}/{rel.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                sftp.stat(remote_dir)
            except OSError:
                pass
            sftp.put(local, remote)
    finally:
        sftp.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fund-only", action="store_true")
    parser.add_argument("--status", action="store_true", help="Read progress JSON on server")
    parser.add_argument("--no-start", action="store_true", help="Upload + dry-run only, do not start tmux job")
    args = parser.parse_args()

    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        upload_files(ssh)
        if args.status:
            out = sh(
                ssh,
                f"cat {WEB}/data/mn2_fleet_bootstrap_progress.json 2>/dev/null || echo '{{}}'",
                timeout=60,
            )
            print(out)
            return 0

        flags = f"--target {int(args.target)}"
        if args.dry_run:
            flags += " --dry-run"
        if args.fund_only:
            flags += " --fund-only"

        if args.dry_run or args.no_start:
            out = sh(
                ssh,
                f"cd {WEB} && export PYTHONPATH={WEB} LITE_APP=1 && .venv/bin/python scripts/mn2_bootstrap_fleet_inventory.py {flags}",  # pragma: allowlist secret
                timeout=900,
            )
            print(out)
            return 0

        log = f"{WEB}/logs/mn2_fleet_bootstrap.log"
        prog = f"{WEB}/data/mn2_fleet_bootstrap_progress.json"
        start_cmd = f"""
set -e
mkdir -p {WEB}/logs {WEB}/data
SESSION=mn2-fleet-bootstrap-500
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "ALREADY_RUNNING tmux=$SESSION"
  tail -n 5 {log} 2>/dev/null || true
  exit 0
fi
tmux new-session -d -s "$SESSION" "cd {WEB} && export PYTHONPATH={WEB} LITE_APP=1 && .venv/bin/python scripts/mn2_bootstrap_fleet_inventory.py {flags} --progress {prog} 2>&1 | tee -a {log}"  # pragma: allowlist secret
echo STARTED tmux=$SESSION log={log}
"""
        out = sh(ssh, start_cmd, timeout=60)
        print(out)
        time.sleep(3)
        tail = sh(ssh, f"tail -n 20 {log} 2>/dev/null || true", timeout=30)
        print(tail)
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
