#!/usr/bin/env python3
"""Run autonomous casino betting agents on a loop (direct service import).

Alternative to server cron POST /api/agent/casino/run-all — no Flask required.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def run_once(*, dry_run: bool = False) -> dict:
    from backend.services import casino_agents_service as casino
    return casino.run_all(dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Casino autonomous agent daemon")
    parser.add_argument("--once", action="store_true", help="Single tick and exit")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between ticks")
    parser.add_argument("--dry-run", action="store_true", help="Simulate bets only")
    args = parser.parse_args()

    if args.once:
        print(run_once(dry_run=args.dry_run))
        return 0

    print(f"[casino-agent-daemon] interval={args.interval}s dry_run={args.dry_run}")
    while True:
        try:
            result = run_once(dry_run=args.dry_run)
            ran = result.get("ran") or result.get("agent_count") or "?"
            print(f"[casino-agent-daemon] ok ran={ran} success={result.get('success')}")
        except Exception as exc:
            print(f"[casino-agent-daemon] error: {exc}")
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
