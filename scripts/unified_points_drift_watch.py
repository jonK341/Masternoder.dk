#!/usr/bin/env python3
"""Scan unified points file store vs SQL for drift. Run hourly via cron."""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="Unified points drift watcher")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--write-alerts", action="store_true", help="Append to logs/points_drift_alerts.jsonl")
    args = ap.parse_args()

    from backend.services.points_drift_service import scan_all

    result = scan_all(limit=args.limit)
    print(json.dumps({"scanned": result["scanned"], "drift_count": result["drift_count"]}, indent=2))

    if args.write_alerts and result.get("alerts"):
        log_dir = os.path.join(_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "points_drift_alerts.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for alert in result["alerts"]:
                f.write(json.dumps(alert) + "\n")
        print(f"Wrote {len(result['alerts'])} alerts to {path}")

    return 1 if result.get("drift_count", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
