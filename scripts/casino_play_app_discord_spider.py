#!/usr/bin/env python3
"""Post Spider bot Discord message when Casino Social Play App is live on Google Play."""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Casino Play App Discord spider bot announce")
    parser.add_argument("--play-store-url", default="", help="Google Play listing URL")
    parser.add_argument("--dry-run", action="store_true", help="Print message only, do not post")
    args = parser.parse_args()

    from backend.services.discord_m8_streams import run_casino_play_app_spider_bot

    if args.dry_run:
        os.environ.setdefault("DISCORD_WEBHOOK_URL", "")
        preview = (
            "🕷️ **Spider bot — Casino Social is LIVE on Google Play**\n\n"
            "🎰 MasterNoder Casino Social is now on Google Play!\n"
            "• Virtual-coin lounge · friends · crews · 25 earn features\n"
            "• Daily chest from Play App · gaming hunt · shop & trophies\n"
            f"📱 {args.play_store_url or 'https://play.google.com/store/apps/details?id=dk.masternoder.casino'}"
        )
        print(preview)
        return 0

    out = run_casino_play_app_spider_bot(play_store_url=args.play_store_url or None)
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
