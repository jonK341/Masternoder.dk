#!/usr/bin/env python3
"""POST minimal payload to configured Discord webhook; print HTTP status only."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from project_env import load_project_dotenv


def _webhook_for_channel(channel: str) -> str:
    key = f"DISCORD_CHANNEL_ID_{channel.upper()}"
    per = (os.environ.get(key) or "").strip()
    if per:
        return per
    return (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()


def probe(*, channel: str = "market", use_service_ua: bool = True) -> int:
    load_project_dotenv()
    url = _webhook_for_channel(channel)
    if not url:
        print("HTTP_STATUS: not_configured")
        return 1
    headers = {"Content-Type": "application/json"}
    if use_service_ua:
        headers["User-Agent"] = "MasternoderBot/1.0 (+https://masternoder.dk)"
    body = json.dumps({"content": "webhook probe (safe to ignore)"}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"HTTP_STATUS: {resp.status}")
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as exc:
        print(f"HTTP_STATUS: {exc.code}")
        return 1 if exc.code >= 400 else 0
    except Exception as exc:
        print(f"HTTP_STATUS: error ({type(exc).__name__})")
        return 1


def main() -> int:
    p = argparse.ArgumentParser(description="Probe Discord webhook (status only, no URL printed)")
    p.add_argument("--channel", default="market", help="Logical channel (market, casino, …)")
    p.add_argument(
        "--no-ua",
        action="store_true",
        help="Omit User-Agent (reproduces Cloudflare 403 from default urllib)",
    )
    args = p.parse_args()
    return probe(channel=args.channel, use_service_ua=not args.no_ua)


if __name__ == "__main__":
    raise SystemExit(main())
