#!/usr/bin/env python3
"""Pause-scale ops: audit camgirl MN2 payout addresses, assign agents, reward on-chain.

Usage:
  python scripts/camgirls_assign_and_reward.py --audit
  python scripts/camgirls_assign_and_reward.py --provision --assign --reward --dry-run
  python scripts/camgirls_assign_and_reward.py --assign --reward --amount 0.0001
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

from project_env import load_project_dotenv


def main() -> int:
    load_project_dotenv()
    parser = argparse.ArgumentParser(description="Camgirls wallet audit, assignments, and MN2 chain rewards")
    parser.add_argument("--audit", action="store_true", help="Audit payout address coverage (+ optional RPC validate)")
    parser.add_argument("--no-rpc", action="store_true", help="Skip validateaddress during audit")
    parser.add_argument("--provision", action="store_true", help="Provision missing daemon payout addresses")
    parser.add_argument("--assign", action="store_true", help="Assign studio agents for all performers")
    parser.add_argument("--reward", action="store_true", help="Send assignment MN2 reward on-chain")
    parser.add_argument("--dry-run", action="store_true", help="Do not broadcast chain txs")
    parser.add_argument("--amount", type=float, default=0.0001, help="MN2 per performer reward")
    parser.add_argument("--performer", help="Single performer id")
    args = parser.parse_args()

    if not any((args.audit, args.provision, args.assign, args.reward)):
        parser.error("Pick at least one of --audit, --provision, --assign, --reward")

    ids = [args.performer] if args.performer else None
    exit_code = 0

    if args.provision:
        from backend.services.camgirls_payout_service import provision_payout_addresses

        prov = provision_payout_addresses(performer_ids=ids)
        print(json.dumps(prov, indent=2))
        if not prov.get("success"):
            exit_code = 1

    if args.audit:
        from backend.services.camgirls_payout_service import audit_performer_wallets

        audit = audit_performer_wallets(ids, check_rpc=not args.no_rpc)
        print(json.dumps({k: audit[k] for k in audit if k != "performers"}, indent=2))
        for row in audit.get("performers") or []:
            addr = row.get("payout_address") or "—"
            print(f"  {row.get('performer_id')}: {addr}")
        if audit.get("missing_address"):
            exit_code = 1

    if args.assign or args.reward:
        from backend.services.camgirls_assignments_service import assign_all_performers, assign_performer

        if args.performer:
            if args.provision and not args.audit:
                from backend.services.camgirls_payout_service import provision_payout_addresses

                provision_payout_addresses(performer_ids=[args.performer])
            out = assign_performer(
                args.performer,
                reward_on_chain=args.reward,
                reward_amount_mn2=args.amount,
                dry_run=args.dry_run,
            )
        else:
            out = assign_all_performers(
                provision_missing_addresses=args.provision,
                reward_on_chain=args.reward,
                reward_amount_mn2=args.amount,
                dry_run=args.dry_run,
            )
        print(json.dumps(out, indent=2))
        if not out.get("success"):
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
