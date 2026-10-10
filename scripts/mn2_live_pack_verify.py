#!/usr/bin/env python3
"""Print live-pack readiness JSON (arb, venues, pair search, payout). Run on app host."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def main() -> int:
    from scripts.daemon_env import load_dotenv
    from backend.services.trading_bots_control_service import live_pack_status

    load_dotenv()
    report = live_pack_status()
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("profit_live_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
