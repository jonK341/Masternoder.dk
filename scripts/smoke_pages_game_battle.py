#!/usr/bin/env python3
"""
Smoke: GET /game and /battle (and optional base) — status, length, key markers, static assets.
Run after deploy: python scripts/smoke_pages_game_battle.py
  python scripts/smoke_pages_game_battle.py --base http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import os
import ssl
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("SMOKE_BASE_URL", "https://masternoder.dk").rstrip("/")

PAGES: list[tuple[str, str, list[str]]] = [
    ("/game", "Hunter game", [
        "hunter-game-app",
        "game-cooldown-timer",
        "data-cd-timer",
        "data-mn-game-battle-bridge",
        "cooldown-timer.js",
    ]),
    ("/battle", "Battle arena", [
        "battle-arena",
        "battle-cooldown-timer",
        "data-cd-timer",
        "data-mn-game-battle-bridge",
        "cooldown-timer.js",
    ]),
]

STATIC: list[str] = [
    "/static/css/cooldown-timer.css",
    "/static/js/cooldown-timer.js",
    "/static/css/story-monitor-5d.css",
    "/static/js/game-battle-bridge.js",
]


def fetch(url: str, timeout: float = 45) -> tuple[int | None, bytes, str | None]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "smoke_pages_game_battle/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.getcode(), r.read(500_000), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read(50_000)
        except OSError:
            body = b""
        return e.code, body, str(e)
    except Exception as e:
        return None, b"", str(e)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default=DEFAULT_BASE, help="Origin (default: env SMOKE_BASE_URL or masternoder.dk)")
    p.add_argument("--only-html", action="store_true", help="Skip static asset fetches")
    args = p.parse_args()
    base = args.base.rstrip("/")
    print(f"Base: {base}\n", flush=True)
    failed = 0
    for path, title, must in PAGES:
        code, body, err = fetch(f"{base}{path}")
        html = body.decode("utf-8", errors="replace")
        if err and code is None:
            print(f"FAIL {path} ({title}): {err}", flush=True)
            failed += 1
            continue
        if code is None or code != 200:
            print(f"FAIL {path} HTTP {code} ({title})", flush=True)
            failed += 1
            continue
        missing = [m for m in must if m not in html]
        if missing:
            print(f"WARN {path} 200 but missing: {', '.join(missing)}", flush=True)
            failed += 1
        else:
            print(f"OK  {path} 200  ({len(body)} bytes)  {title}", flush=True)
    if not args.only_html:
        for path in STATIC:
            c, b, e = fetch(f"{base}{path}", timeout=30)
            if e and c is None:
                print(f"FAIL {path} {e}", flush=True)
                failed += 1
            elif c == 200:
                print(f"OK  {path} 200  ({len(b)} bytes)", flush=True)
            else:
                print(f"FAIL {path} HTTP {c}", flush=True)
                failed += 1
    print(flush=True)
    if failed:
        print(f"Done: {failed} issue(s).", file=sys.stderr, flush=True)
        return 1
    print("Done: all checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
