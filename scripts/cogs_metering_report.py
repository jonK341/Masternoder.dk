#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Print p50/p90 COGS aggregates from logs/cogs/metering.jsonl (same logic as API).

Usage:
  python scripts/cogs_metering_report.py
  python scripts/cogs_metering_report.py --path /var/www/html/logs/cogs/metering.jsonl
  python scripts/cogs_metering_report.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Project root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="COGS metering.jsonl summary (p50/p90, line items)")
    parser.add_argument("--path", help="Override path to metering.jsonl")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    os.chdir(_ROOT)
    from backend.services.cogs_metering_service import summarize_metering_jsonl

    data = summarize_metering_jsonl(path=args.path)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0 if data.get("success") else 1

    if not data.get("success"):
        print("Error:", data.get("error", data), file=sys.stderr)
        return 1

    print("COGS metering report")
    print("  path:", data.get("path"))
    print("  rows: ", data.get("count"))
    t = data.get("total_usd") or {}
    print("  total_usd mean/p50/p90:", t.get("mean"), t.get("p50"), t.get("p90"), "(min/max)", t.get("min"), t.get("max"))
    r = data.get("ratio_vs_reference_job") or {}
    print("  ratio_vs_reference mean/p50/p90:", r.get("mean"), r.get("p50"), r.get("p90"))
    print("  line items (mean / p50 / p90 USD):")
    for li in data.get("line_items") or []:
        print(
            f"    {li.get('name')}: sum={li.get('sum_usd')} mean={li.get('mean_usd')} "
            f"p50={li.get('p50_usd')} p90={li.get('p90_usd')}"
        )
    print()
    print("Use p90 for subscription caps (not the mean). See docs/MONETIZATION_PAYPAL.md §8.1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
