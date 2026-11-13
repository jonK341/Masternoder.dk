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
    from backend.services.landing_monitor_actions_service import sync_from_activity
    from backend.services.landing_monitor_pipeline_service import build_pipeline
    from backend.services.landing_monitor_service import refresh_snapshot

    sync = sync_from_activity(limit=40)
    pipe = build_pipeline(force=False, use_llm=False)
    payload = refresh_snapshot(force=True)
    sats = payload.get("sats") or {}
    totals = sats.get("totals") or {}
    print(
        json.dumps(
            {
                "success": True,
                "updated_at": payload.get("updated_at"),
                "bpm": payload.get("bpm"),
                "special": (payload.get("special") or {}).get("id"),
                "lightshow": (payload.get("lightshow") or {}).get("id"),
                "imported": sync.get("imported"),
                "reel_count": payload.get("reel_count"),
                "network_sats": totals.get("network_sats"),
                "trade_sats": totals.get("trade_sats"),
                "pipeline_ms": pipe.get("duration_ms"),
                "pipeline_scenes": pipe.get("scene_count"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
