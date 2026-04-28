#!/usr/bin/env python3
"""
Demo: call POST /api/agent/shop/execute-mn2-purchase with AGENT_MN2_SHOP_SECRET.

Usage (from project root, app running):
  set AGENT_MN2_SHOP_SECRET=yoursecret
  python scripts/agent_mn2_shop_demo.py --base https://masternoder.dk --user USER --item ITEM_ID

Quick checks (no purchase):
  python scripts/agent_mn2_shop_demo.py --check --base https://masternoder.dk
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def _get(url: str, timeout: float = 15.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.read().decode("utf-8", errors="replace")


def run_check(base: str) -> int:
    base = base.rstrip("/")
    ok = 0
    for path, label in (
        ("/api/health", "health"),
        ("/api/mn2/price", "mn2/price"),
        ("/api/health/system", "health/system"),
        ("/api/shop/payment-health", "shop/payment-health"),
    ):
        url = base + path
        print(f"GET {url}")
        try:
            code, body = _get(url, timeout=20.0 if "payment-health" in path else 12.0)
            print(f"  -> HTTP {code} ({len(body)} bytes)")
            if len(body) < 500:
                print(f"  {body}")
            else:
                print(f"  {body[:400]}...")
            ok += 1
        except Exception as e:
            print(f"  -> FAILED: {e}", file=sys.stderr)
    print(f"\nCompleted {ok}/4 checks.")
    return 0 if ok >= 2 else 1


def main() -> int:
    p = argparse.ArgumentParser(
        description="MN2 agent shop purchase demo, or --check for endpoint smoke.",
    )
    p.add_argument("--base", default=os.environ.get("SHOP_TEST_BASE", "http://127.0.0.1:5000"))
    p.add_argument("--check", action="store_true", help="GET health + MN2 + payment-health only (no purchase)")
    p.add_argument("--user", help="game_user_id with MN2 balance")
    p.add_argument("--item", dest="item_id", help="shop item id")
    p.add_argument("--agent", default="mn2_scout")
    p.add_argument("--qty", type=int, default=1)
    args = p.parse_args()

    if args.check:
        return run_check(args.base)

    if not args.user or not args.item_id:
        p.print_help()
        print(
            "\nMissing --user and/or --item. Example:\n"
            "  python scripts/agent_mn2_shop_demo.py --check --base https://masternoder.dk\n"
            "  python scripts/agent_mn2_shop_demo.py --base https://masternoder.dk --user my_id --item some_item_id\n",
            file=sys.stderr,
        )
        return 1

    secret = (os.environ.get("AGENT_MN2_SHOP_SECRET") or "").strip()
    if not secret:
        print("Set AGENT_MN2_SHOP_SECRET", file=sys.stderr)
        return 1
    url = args.base.rstrip("/") + "/api/agent/shop/execute-mn2-purchase"
    body = json.dumps({
        "user_id": args.user,
        "item_id": args.item_id,
        "quantity": args.qty,
        "agent_id": args.agent,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Agent-Shop-Key": secret,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("Request failed:", e, file=sys.stderr)
        return 1
    print(out)
    try:
        d = json.loads(out)
        return 0 if d.get("success") else 2
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
