#!/usr/bin/env python3
"""POST treasury sign-off via SSH localhost curl (reads server .env for ops secret).

Usage:
  python scripts/treasury_signoff_post_ssh.py --ask-pass
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import dotenv
    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

DEFAULT_BODY = {
    "approver": "Jon",
    "cold_wallet_address": "JJvVw8MeVevRuziARDxAouAN2EuUCPSnTQ",
    "max_batch_mn2": 600000,
    "notes": "MN2_OPS §8.6 treasury sign-off",
}


def sh(ssh, cmd: str, timeout: int = 120) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="POST treasury sign-off on server via curl")
    p.add_argument("--ask-pass", action="store_true", help="Prompt SSH password (ignores .env DEPLOY_PASS)")
    p.add_argument("--approver", default=DEFAULT_BODY["approver"])
    p.add_argument("--cold-wallet", default=DEFAULT_BODY["cold_wallet_address"])
    args = p.parse_args()

    body = json.dumps({
        **DEFAULT_BODY,
        "approver": args.approver,
        "cold_wallet_address": args.cold_wallet,
    })

    host, user = deploy_host(), deploy_user()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=require_deploy_pass(force_prompt=args.ask_pass), timeout=30)
    print(f"Connected {user}@{host}")

    secret = sh(
        ssh,
        "grep -E '^(DISCORD_OPS_SECRET|ADMIN_OPS_SECRET|MN2_OPS_SECRET)=' /var/www/html/.env "
        "| head -1 | cut -d= -f2- | tr -d '\\r\"'",
    ).strip()

    hdr = f'-H "X-Ops-Secret: {secret}"' if secret else ""
    payload = body.replace("'", "'\\''")
    cmd = (
        f"curl -s -w '\\nHTTP:%{{http_code}}' -X POST "
        f"-H 'Content-Type: application/json' {hdr} "
        f"-d '{payload}' "
        f"http://127.0.0.1:5000/api/agents/treasury/sign-off "
        f"|| curl -s -w '\\nHTTP:%{{http_code}}' -X POST "
        f"-H 'Content-Type: application/json' {hdr} "
        f"-d '{payload}' "
        f"http://127.0.0.1:5001/api/agents/treasury/sign-off"
    )
    print("-- POST /api/agents/treasury/sign-off --")
    out = sh(ssh, cmd, timeout=180)
    print(out)

    print("\n-- verify GET --")
    get_cmd = (
        f"curl -s {hdr} http://127.0.0.1:5000/api/agents/treasury/sign-off "
        f"|| curl -s {hdr} http://127.0.0.1:5001/api/agents/treasury/sign-off"
    )
    verify = sh(ssh, get_cmd)
    print(verify)

    ssh.close()
    ok = '"success": true' in out.replace(" ", "") or '"success":true' in out.replace(" ", "")
    if not ok:
        ok = '"signed": true' in verify.replace(" ", "") or '"signed":true' in verify.replace(" ", "")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
