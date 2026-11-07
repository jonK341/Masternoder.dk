#!/usr/bin/env python3
"""Cancel open MN2→COINS sells on the liquidity bot to unlock ledger MN2."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

WEB = "/var/www/html"


def parse_last_json(text: str) -> dict:
    dec = json.JSONDecoder()
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return {}


def sh(ssh, cmd: str, timeout: int = 600) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max orders to cancel (0=all)")
    args = parser.parse_args()

    remote = f"""
set -e
cd {WEB}
export PYTHONPATH={WEB}
LITE_APP=1 .venv/bin/python - <<'PY'
import json, os, sys
os.chdir({WEB!r})
sys.path.insert(0, {WEB!r})
from backend.services.mn2_collateral_liquidity_ops import free_liquidity_from_open_sells
out = free_liquidity_from_open_sells(dry_run={str(args.dry_run)}, limit={int(args.limit)})
print(json.dumps(out, indent=2))
PY
"""
    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        out = sh(ssh, remote, timeout=900)
        print(out)
        payload = parse_last_json(out)
        return 0 if payload.get("success") or args.dry_run else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
