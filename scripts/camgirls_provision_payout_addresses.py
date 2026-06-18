#!/usr/bin/env python3
"""Provision camgirls performer payout addresses via MN2 daemon getnewaddress.

Usage:
  python scripts/camgirls_provision_payout_addresses.py
  python scripts/camgirls_provision_payout_addresses.py --performer performer_nova
  python scripts/camgirls_provision_payout_addresses.py --remote --ask-pass
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)


def provision_local(performer_id: str | None) -> int:
    from backend.services.camgirls_payout_service import list_payout_addresses, provision_payout_addresses

    ids = [performer_id] if performer_id else None
    result = provision_payout_addresses(performer_ids=ids)
    print(json.dumps(result, indent=2))
    if result.get("results"):
        for row in result["results"]:
            if row.get("success"):
                flag = " (new)" if row.get("created") else ""
                print(f"  {row.get('performer_id')}: {row.get('payout_address')}{flag}")
    listing = list_payout_addresses()
    print(f"\nTotal payout addresses: {listing.get('count', 0)}")
    return 0 if result.get("success") else 1


def provision_remote(*, force_prompt: bool) -> int:
    try:
        import paramiko
    except ImportError:
        print("paramiko required for --remote", file=sys.stderr)
        return 1
    try:
        import dotenv
        dotenv.load_dotenv(os.path.join(BASE, ".env"))
    except Exception:
        pass
    sys.path.insert(0, os.path.join(BASE, "scripts"))
    from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

    pw = require_deploy_pass(force_prompt=force_prompt)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    web = "/var/www/html"
    py = f"cd {web} && (test -x .venv/bin/python && .venv/bin/python || python3)"
    cmd = f"{py} scripts/camgirls_provision_payout_addresses.py"
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision camgirls daemon payout addresses")
    parser.add_argument("--performer", help="Single performer id (default: all active)")
    parser.add_argument("--remote", action="store_true", help="Run on production server via SSH")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt SSH password for --remote")
    args = parser.parse_args()
    if args.remote:
        return provision_remote(force_prompt=args.ask_pass)
    return provision_local(args.performer)


if __name__ == "__main__":
    raise SystemExit(main())
