#!/usr/bin/env python3
"""Ping Google/Bing (and IndexNow if INDEXNOW_KEY set) for masternoder.dk sitemap."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "https://masternoder.dk"


def main() -> int:
    url = f"{BASE}/api/seo/ping-sitemap"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as exc:
        print("FAIL", exc)
        return 1
    print(json.dumps(data, indent=2))
    return 0 if data.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
