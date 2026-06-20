#!/usr/bin/env python3
"""Remote ops smoke test: trader staking join-pool, health, daemon status, explorer checks."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv
    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--join-pool", action="store_true", help="POST trader-staking/join-pool")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ask-pass", action="store_true")
    args = p.parse_args()

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"Connected {user}@{host}\n")

    web = "/var/www/html"
    secret_cmd = (
        f"SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET|DISCORD_OPS_SECRET|ADMIN_OPS_SECRET)=' "
        f"{web}/.env | head -1 | cut -d= -f2- | tr -d '\\r\"')"
    )

    checks = [
        ("health", f"{secret_cmd}; curl -s http://127.0.0.1:5000/api/mn2/health"),
        ("trader status", f"{secret_cmd}; curl -s 'http://127.0.0.1:5000/api/agents/trader-staking/status?user_id=default_user'"),
        ("staking status RPC", f"cd {web} && ./venv/bin/python -c \"import json; from backend.services.mn2_rpc_client import getstakingstatus; print(json.dumps(getstakingstatus(), indent=2))\""),
    ]
    for label, cmd in checks:
        print(f"=== {label} ===")
        print(sh(ssh, cmd, timeout=180))
        print()

    if args.join_pool:
        body = '{"dry_run":true}' if args.dry_run else "{}"
        print("=== join-pool ===")
        cmd = (
            f"{secret_cmd}; curl -s -X POST -H \"X-Ops-Secret: $SECRET\" "
            f"-H \"Content-Type: application/json\" -d '{body}' "
            f"http://127.0.0.1:5000/api/agents/trader-staking/join-pool"
        )
        print(sh(ssh, cmd, timeout=300))
        print()

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
