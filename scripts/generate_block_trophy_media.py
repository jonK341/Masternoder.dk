#!/usr/bin/env python3
"""Generate PNG + GIF for block-height trophies (plan 001 BM-U2).

  python scripts/generate_block_trophy_media.py --height 1005
  python scripts/generate_block_trophy_media.py --from-manifest --limit 10
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--height", type=int, help="Single block height")
    ap.add_argument("--from-manifest", action="store_true", help="Process drops in block_mint_manifest.json")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    from backend.services.block_trophy_media_service import ensure_block_media

    heights: list[int] = []
    if args.height:
        heights = [int(args.height)]
    elif args.from_manifest:
        path = os.path.join(_ROOT, "data", "block_mint_manifest.json")
        doc = {}
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        drops = doc.get("drops") or {}
        for key in sorted(drops.keys(), key=lambda x: int(x), reverse=True)[: max(1, args.limit)]:
            heights.append(int(drops[key].get("height") or key))
    else:
        ap.print_help()
        return 1

    ok = 0
    for h in heights:
        result = ensure_block_media(h, force=args.force)
        if result.get("success"):
            ok += 1
            tag = "skip" if result.get("skipped") else "ok"
            print(f"[{tag}] block-{h} {result.get('gif_url') or result.get('image_url')}")
        else:
            print(f"[FAIL] block-{h} {result.get('error')}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
