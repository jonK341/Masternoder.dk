#!/usr/bin/env python3
"""
HTML smoke checks for /shop (frontpage-aligned hub).

Usage:
  set PLATFORM_BASE_URL=https://masternoder.dk
  python scripts/smoke_shop_page.py
"""
from __future__ import annotations

import os
import sys
import urllib.request

BASE = os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = float(os.environ.get("PLATFORM_CHECK_TIMEOUT", "25"))


def main() -> int:
    print(f"Shop page smoke against {BASE}")
    req = urllib.request.Request(BASE + "/shop", headers={"Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        html = res.read().decode("utf-8", errors="replace")
        status = res.status

    checks = [
        ("status 200", status == 200),
        ("shop-hub.js", "shop-hub.js" in html),
        ("shop-glance-stats", "shop-glance-stats" in html),
        ("shop-fp-hero", "shop-fp-hero" in html),
        ("frontpage-home.css", "frontpage-home.css" in html),
        ("payment strip", 'id="shop-payment-strip" class="shop-payment-strip"' in html),
        ("shop-tab-btn", "shop-tab-btn" in html),
    ]
    failures = 0
    for name, ok in checks:
        print(f"{'[OK]' if ok else '[FAIL]'} {name}")
        if not ok:
            failures += 1

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1
    print("\nAll shop page smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
