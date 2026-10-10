#!/usr/bin/env python3
"""Record agent treasury cold-wallet sign-off (MN2_OPS §8.6).

Usage (on server or locally with data/ + RPC):
  python scripts/treasury_signoff.py --approver "Jon" --cold-wallet MxColdAddr...
  python scripts/treasury_signoff.py --approver "Jon" --cold-wallet MxCold... --require-reconcile
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import dotenv
    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass


def main() -> int:
    p = argparse.ArgumentParser(description="Record treasury cold-wallet sign-off")
    p.add_argument("--approver", required=True, help="Named approver (recorded in audit log)")
    p.add_argument("--cold-wallet", required=True, help="Cold storage MN2 address (not ismine on server)")
    p.add_argument("--hot-cap-mn2", type=float, default=None, help="Optional hot wallet cap")
    p.add_argument("--max-batch-mn2", type=float, default=600000, help="Max batch distribute MN2")
    p.add_argument("--notes", default="", help="Optional runbook/ticket reference")
    p.add_argument("--require-reconcile", action="store_true", help="Fail if reconcile not green")
    args = p.parse_args()

    from backend.services.treasury_signoff_service import record_signoff, get_signoff

    result = record_signoff(
        approver=args.approver,
        cold_wallet_address=args.cold_wallet,
        hot_cap_mn2=args.hot_cap_mn2,
        max_batch_mn2=args.max_batch_mn2,
        notes=args.notes,
        require_reconcile_ok=args.require_reconcile,
    )
    print(json.dumps(result, indent=2, default=str))
    if not result.get("success"):
        return 1
    status = get_signoff()
    print("\nSign-off active:", status.get("signed"))
    print("File:", os.path.join(ROOT, "data", "treasury_signoff.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
