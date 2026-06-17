#!/usr/bin/env python3
"""Provision camgirls performer payout addresses via MN2 daemon getnewaddress.

Usage:
  python scripts/camgirls_provision_payout_addresses.py
  python scripts/camgirls_provision_payout_addresses.py --performer performer_nova
  python scripts/camgirls_provision_payout_addresses.py --check-rpc
  python scripts/camgirls_provision_payout_addresses.py --remote --ask-pass

On server (loads /var/www/html/.env automatically):
  cd /var/www/html && bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py
  cd /var/www/html && python3 scripts/camgirls_provision_payout_addresses.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

from project_env import load_project_dotenv, probe_rpc, rpc_env_status


def _ensure_env(*, require_rpc: bool = False) -> int:
    load_project_dotenv()
    st = rpc_env_status()
    if not st["env_loaded"]:
        print(f"WARN: no .env at {st['env_file']}", file=sys.stderr)
    elif not st["rpc_user_set"] or not st["rpc_password_set"]:
        print(
            "WARN: MN2_RPC_USER or MN2_RPC_PASSWORD missing in .env — "
            "new getnewaddress calls will fail (cached addresses still work).",
            file=sys.stderr,
        )
    if require_rpc:
        ok, msg = probe_rpc()
        print(f"RPC probe: {msg}")
        if not ok:
            print(
                "\nFix: set MN2_RPC_USER and MN2_RPC_PASSWORD in /var/www/html/.env "
                "to match masternoder2.conf (rpcuser/rpcpassword), then retry.\n"
                "  python scripts/verify_mn2_production_ready.py --no-rpc  # file match only\n"
                "  python scripts/verify_mn2_production_ready.py           # + live RPC",
                file=sys.stderr,
            )
            return 1
    return 0


def provision_local(performer_id: str | None) -> int:
    if _ensure_env(require_rpc=False):
        pass  # warn only unless --check-rpc handled in main
    from backend.services.camgirls_payout_service import list_payout_addresses, provision_payout_addresses

    ids = [performer_id] if performer_id else None
    result = provision_payout_addresses(performer_ids=ids)
    print(json.dumps(result, indent=2))
    auth_fail = False
    if result.get("results"):
        for row in result["results"]:
            if row.get("success"):
                flag = " (cached)" if not row.get("created") else " (new)"
                print(f"  {row.get('performer_id')}: {row.get('payout_address')}{flag}")
            else:
                err = row.get("error") or "failed"
                print(f"  FAIL {row.get('performer_id')}: {err}", file=sys.stderr)
                if "authentication" in str(err).lower() or "401" in str(err):
                    auth_fail = True
    listing = list_payout_addresses()
    print(f"\nTotal payout addresses: {listing.get('count', 0)}")
    if auth_fail:
        print(
            "\nNew performers need getnewaddress (RPC). Cached performers skip RPC.\n"
            "Load .env: scripts now auto-load /var/www/html/.env.\n"
            "Verify: python3 scripts/camgirls_provision_payout_addresses.py --check-rpc",
            file=sys.stderr,
        )
    return 0 if result.get("success") else 1


def provision_remote(*, force_prompt: bool) -> int:
    try:
        import paramiko
    except ImportError:
        print("paramiko required for --remote", file=sys.stderr)
        return 1
    load_project_dotenv()
    from deploy_ssh_env import deploy_host, deploy_user, remote_py_prefix, require_deploy_pass

    pw = require_deploy_pass(force_prompt=force_prompt)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)
    web = "/var/www/html"
    cmd = (
        f"{remote_py_prefix(web)}"
        f"$PY scripts/camgirls_provision_payout_addresses.py"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision camgirls daemon payout addresses")
    parser.add_argument("--performer", help="Single performer id (default: all active)")
    parser.add_argument("--check-rpc", action="store_true", help="Probe MN2 RPC auth then exit")
    parser.add_argument("--remote", action="store_true", help="Run on production server via SSH")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt SSH password for --remote")
    args = parser.parse_args()
    if args.check_rpc:
        return _ensure_env(require_rpc=True)
    if args.remote:
        return provision_remote(force_prompt=args.ask_pass)
    return provision_local(args.performer)


if __name__ == "__main__":
    raise SystemExit(main())
