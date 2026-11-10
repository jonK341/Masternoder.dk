#!/usr/bin/env python3
"""Refresh landing monitor cache (designed for a 5s cron loop)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    from backend.services.landing_monitor_service import refresh_snapshot

    payload = refresh_snapshot(force=True)
    print(
        json.dumps(
            {
                "success": True,
                "updated_at": payload.get("updated_at"),
                "bpm": payload.get("bpm"),
                "special": (payload.get("special") or {}).get("id"),
                "lightshow": (payload.get("lightshow") or {}).get("id"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
