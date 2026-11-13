#!/usr/bin/env python3
"""Generate a fresh batch of 10 Jon Film actor appointments (daily cron)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    from backend.services import jon_film_service
    from backend.services.landing_monitor_extras_service import ensure_discord_poll

    # Always fresh — cron repeats the full process every day.
    out = jon_film_service.generate_daily_appointments(force=True, count=10)
    poll = ensure_discord_poll(
        question="Jon Film daily vote — which stage leads tonight's battlefield cut?"
    )
    print(
        json.dumps(
            {
                "success": True,
                "movie": jon_film_service.MOVIE_TITLE,
                "batch_id": out.get("batch_id"),
                "count": out.get("count"),
                "poll_id": (poll.get("poll") or {}).get("id"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
