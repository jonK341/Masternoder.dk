#!/usr/bin/env python3
"""Batch-generate block trophy media (lazy genesis backfill worker)."""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_h", type=int, default=1)
    parser.add_argument("--to", dest="to_h", type=int, default=0)
    parser.add_argument("--batch", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    from backend.services.block_mint_service import _read_json, _MANIFEST_PATH, sync_block_height
    from backend.services.block_trophy_media_service import ensure_block_media

    sync_block_height()
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    drops = doc.get("drops") or {}
    heights = sorted(int(k) for k in drops.keys())
    if args.to_h:
        heights = [h for h in heights if args.from_h <= h <= args.to_h]
    else:
        heights = [h for h in heights if h >= args.from_h]

    done = 0
    errors = 0
    for h in heights[: max(1, args.batch)]:
        result = ensure_block_media(h, force=args.force)
        if result.get("success"):
            done += 1
        else:
            errors += 1
    print({"processed": done + errors, "success": done, "errors": errors, "remaining": max(0, len(heights) - done - errors)})
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
