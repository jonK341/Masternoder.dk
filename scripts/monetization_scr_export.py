#!/usr/bin/env python3
"""
Rough revenue vs COGS snapshot: payment_ledger.jsonl + cogs/metering.jsonl.

Implementation: backend.services.monetization_scr_blend_service (unit-tested).
For per-job CSV rollups, see scripts/scr_usage_export.py.

Usage:
  python scripts/monetization_scr_export.py
  python scripts/monetization_scr_export.py --since-days 30 --json
  python scripts/monetization_scr_export.py --ledger-path logs/monetization/payment_ledger.jsonl --scr-only

See docs/MONETIZATION_PAYPAL.md (Studio Cash Rail, phase C margin).
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
    from backend.services.monetization_scr_blend_service import run_ledger_metering_blend

    p = argparse.ArgumentParser(description="Monetization ledger + metering COGS export (rough blend)")
    p.add_argument("--ledger-path", help="Override payment_ledger.jsonl path")
    p.add_argument("--metering-path", help="Override metering.jsonl path")
    p.add_argument("--since-days", type=float, default=None, help="Only rows with ts on or after now - N days (default: all time)")
    p.add_argument(
        "--scr-only",
        action="store_true",
        help="Only ledger rows that look like SCR/B2B (provider b2b_scr or deal/studio fields)",
    )
    p.add_argument("--json", action="store_true", help="Print JSON only")
    args = p.parse_args()

    try:
        out = run_ledger_metering_blend(
            ledger_path=args.ledger_path,
            metering_path=args.metering_path,
            since_days=args.since_days,
            scr_only=args.scr_only,
        )
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print("Monetization export (ledger + metering)")
    print("  ledger:", out["ledger_path"])
    print("  metering:", out["metering_path"])
    if out.get("since_cutoff_iso"):
        print("  since:", out["since_cutoff_iso"])
    if args.scr_only:
        print("  filter: SCR-like ledger rows only")
    print("  ledger rows:", out["ledger_rows_read"], "  metering rows:", out["metering_rows_read"])
    print("  revenue_usd (ledger):", out["revenue_usd_total"])
    print("  cogs_usd (metering): ", out["cogs_usd_total"])
    mg = out.get("blended_gross_margin_vs_metering")
    print("  blended gross margin (rough):", mg if mg is not None else "n/a")
    print("  ", out.get("note", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
