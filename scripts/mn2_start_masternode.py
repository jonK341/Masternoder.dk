#!/usr/bin/env python3
"""
Start hosted masternode(s) via RPC: local first (ping / activetime), alias broadcast fallback.

Used by purchase auto-provision, cron retries, fleet autostart, and manual ops.

Examples (on server, from /var/www/html):
  python3 scripts/mn2_start_masternode.py --alias platformmn2
  python3 scripts/mn2_start_masternode.py --alias platformmn2 --privkey 6mD73...
  python3 scripts/mn2_start_masternode.py --all-from-conf
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services import mn2_masternode_service as mn  # noqa: E402


def _aliases_from_conf() -> list[str]:
    path = mn._masternode_conf_path()
    aliases: list[str] = []
    if not os.path.isfile(path):
        return aliases
    for row in mn._read_masternode_conf_entries():
        if row.get("kind") == "entry" and row.get("valid"):
            aliases.append(str(row["alias"]))
    return aliases


def start_one(alias: str, privkey: str | None = None) -> int:
    alias = (alias or "").strip()
    if not alias:
        print("ERROR: alias required", file=sys.stderr)
        return 2
    err = mn._start_masternode(alias, privkey)
    if err:
        print(f"ERROR {alias}: {err}", file=sys.stderr)
        return 1
    print(f"OK {alias}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Start MN2 masternode(s): local first, alias fallback")
    p.add_argument("--alias", help="masternode.conf alias (e.g. platformmn2)")
    p.add_argument("--privkey", help="Optional privkey (read from masternode.conf when omitted)")
    p.add_argument(
        "--all-from-conf",
        action="store_true",
        help="Start every alias listed in masternode.conf (one local-first pass each)",
    )
    args = p.parse_args()

    wait_err = mn._wait_for_rpc_ready()
    if wait_err:
        print(f"ERROR: {wait_err}", file=sys.stderr)
        return 1

    if args.all_from_conf:
        aliases = _aliases_from_conf()
        if not aliases:
            print("No aliases in masternode.conf", file=sys.stderr)
            return 2
        rc = 0
        for alias in aliases:
            pk = args.privkey if args.alias == alias else None
            if start_one(alias, pk or mn._privkey_for_alias(alias)) != 0:
                rc = 1
        return rc

    if not args.alias:
        p.error("pass --alias or --all-from-conf")
    return start_one(args.alias, args.privkey or mn._privkey_for_alias(args.alias))


if __name__ == "__main__":
    sys.exit(main())
