"""Finish APPROVED PayPal checkout orders so merchant capture completes."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture pending PayPal Orders v2 checkouts (APPROVED → COMPLETED) and fulfill rails.",
    )
    parser.add_argument("--limit", type=int, default=400, help="Max orders to finish (default 400)")
    parser.add_argument("--dry-run", action="store_true", help="List pending jobs without capturing")
    parser.add_argument(
        "--order-ids",
        default="",
        help="Comma-separated PayPal order IDs (for dashboard-exported pending checkouts)",
    )
    parser.add_argument(
        "--order-ids-file",
        default="",
        help="File with one PayPal order ID per line",
    )
    args = parser.parse_args()

    extra = [part.strip() for part in (args.order_ids or "").split(",") if part.strip()]
    if args.order_ids_file:
        with open(args.order_ids_file, "r", encoding="utf-8") as f:
            extra.extend(line.strip() for line in f if line.strip() and not line.strip().startswith("#"))

    from backend.services.paypal_order_events import finish_pending_paypal_orders

    result = finish_pending_paypal_orders(
        limit=args.limit,
        extra_order_ids=extra,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, default=str))
    counts = result.get("counts") or {}
    failed = int(counts.get("failed") or 0)
    return 1 if failed and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
