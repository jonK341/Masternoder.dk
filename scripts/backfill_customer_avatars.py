#!/usr/bin/env python3
"""Backfill customer avatar SVGs from unified_points directory (off-request)."""
from __future__ import annotations

import hashlib
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POINTS = os.path.join(_BASE, "logs", "unified_points")
_OUT = os.path.join(_BASE, "static", "img", "customers")


def _color(uid: str) -> str:
    h = hashlib.sha256(uid.encode()).hexdigest()
    return f"#{h[:6]}"


def _svg(uid: str) -> str:
    c = _color(uid)
    letter = (uid[:1] or "?").upper()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="{c}"/>
  <text x="32" y="40" text-anchor="middle" font-size="28" fill="#fff" font-family="sans-serif">{letter}</text>
</svg>'''


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    if not os.path.isdir(_POINTS):
        print("No unified_points directory")
        return 0
    created = 0
    for name in os.listdir(_POINTS):
        if not name.endswith(".json"):
            continue
        uid = name[:-5]
        if uid in ("default_user", "anon"):
            continue
        dest = os.path.join(_OUT, f"{uid}.svg")
        if os.path.isfile(dest):
            continue
        with open(dest, "w", encoding="utf-8") as f:
            f.write(_svg(uid))
        created += 1
        try:
            from backend.services.activity_events_service import emit
            emit("customer_new", channel="customers", user_id=uid, payload={"avatar": f"/static/img/customers/{uid}.svg"})
        except Exception:
            pass
    print(f"Created {created} avatars")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, _BASE)
    raise SystemExit(main())
