#!/usr/bin/env python3
"""Run autonomous casino betting agents on a loop (direct service import).

Alternative to server cron POST /api/agent/casino/run-all — no Flask required.

Env:
  CASINO_AGENT_DRY_RUN=1  — simulate bets (default when unset)
  CASINO_AGENT_INTERVAL   — seconds between ticks (default 300)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _env_dry_run() -> bool:
    return os.environ.get("CASINO_AGENT_DRY_RUN", "1").strip().lower() in ("1", "true", "yes", "on")


def _env_interval(default: int = 300) -> int:
    raw = os.environ.get("CASINO_AGENT_INTERVAL", "").strip()
    if not raw:
        return default
    try:
        return max(30, int(raw))
    except ValueError:
        return default


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[casino-agent-daemon {_ts()}] {msg}", flush=True)


def _summarize(result: dict) -> str:
    skipped = result.get("skipped") or {}
    skip_bits = [f"{k}={v}" for k, v in list(skipped.items())[:3]]
    skip_str = f" skipped={','.join(skip_bits)}" if skip_bits else ""
    mode = "dry_run" if result.get("dry_run") else "live"
    return (
        f"{mode} agents={result.get('agent_count', '?')} "
        f"ran={result.get('ran', '?')} success={result.get('success')}{skip_str}"
    )


def run_once(*, dry_run: bool = False) -> dict:
    from backend.services import casino_agents_service as casino
    if not dry_run:
        casino.ensure_agent_bankrolls()
    return casino.run_all(dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Casino autonomous agent daemon")
    parser.add_argument("--once", action="store_true", help="Single tick and exit")
    parser.add_argument("--interval", type=int, default=0, help="Seconds between ticks (overrides CASINO_AGENT_INTERVAL)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", dest="dry_run", action="store_true", help="Simulate bets only")
    group.add_argument("--live", dest="dry_run", action="store_false", help="Place real bets")
    parser.set_defaults(dry_run=None)
    args = parser.parse_args()

    dry_run = _env_dry_run() if args.dry_run is None else args.dry_run
    interval = args.interval or _env_interval()

    if args.once:
        result = run_once(dry_run=dry_run)
        print(json.dumps(result, default=str))
        return 0 if result.get("success") else 1

    _log(f"start interval={interval}s dry_run={dry_run} (set CASINO_AGENT_DRY_RUN=0 or --live for real bets)")
    while True:
        try:
            result = run_once(dry_run=dry_run)
            _log(_summarize(result))
        except Exception as exc:
            _log(f"error: {exc}")
        time.sleep(max(30, interval))


if __name__ == "__main__":
    raise SystemExit(main())
