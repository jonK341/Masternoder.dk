#!/usr/bin/env python3
"""CLI: record agent-treasury cold-wallet sign-off (MN2_OPS §8.6).

Does not distribute funds. Example:
  python scripts/treasury_signoff.py --approver alice --cold-wallet MnColdAddr...
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    p = argparse.ArgumentParser(description="Record treasury cold-wallet sign-off")
    p.add_argument("--approver", required=True)
    p.add_argument("--cold-wallet", required=True, dest="cold_wallet")
    p.add_argument("--hot-cap-mn2", type=float, default=None)
    p.add_argument("--max-batch-mn2", type=float, default=600000)
    p.add_argument("--notes", default="")
    p.add_argument("--require-reconcile-ok", action="store_true")
    p.add_argument("--show", action="store_true", help="Print current sign-off and exit")
    args = p.parse_args()

    from backend.services import treasury_signoff_service as tss

    if args.show:
        print(json.dumps(tss.get_signoff(), indent=2))
        return 0

    r = tss.record_signoff(
        approver=args.approver,
        cold_wallet_address=args.cold_wallet,
        hot_cap_mn2=args.hot_cap_mn2,
        max_batch_mn2=args.max_batch_mn2,
        notes=args.notes,
        require_reconcile_ok=args.require_reconcile_ok,
    )
    print(json.dumps(r, indent=2, default=str))
    return 0 if r.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
