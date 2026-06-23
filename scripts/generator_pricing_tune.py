#!/usr/bin/env python3
"""Apply COGS-based generation pack pricing suggestion."""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="COGS pricing tune for generation packs")
    ap.add_argument("--sku", default="generation_pack_ref")
    ap.add_argument("--apply", action="store_true", help="Write price_usd to monetization_config.json")
    args = ap.parse_args()

    from backend.services.generator_pricing_service import pricing_suggestion, apply_suggested_pack_price

    sug = pricing_suggestion()
    print(json.dumps(sug, indent=2))
    if not sug.get("success"):
        return 1

    applied = apply_suggested_pack_price(sku_key=args.sku, dry_run=not args.apply)
    print(json.dumps(applied, indent=2))
    return 0 if applied.get("success") or applied.get("dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
