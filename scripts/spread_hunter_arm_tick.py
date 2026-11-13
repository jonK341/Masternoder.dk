#!/usr/bin/env python3
"""One-shot spread-hunter arm tick (wide BN↔NK catalog hunt + locked-profit exec)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run spread-hunter arm tick")
    ap.add_argument("--force", action="store_true", help="Run even if arm env-disabled")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true", help="Print arm status / board only")
    args = ap.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass

    from backend.services.exchange_spread_hunter_arm_service import (
        run_spread_hunter_tick,
        spread_hunter_status,
    )

    if args.status:
        out = spread_hunter_status()
    else:
        out = run_spread_hunter_tick(force=args.force)
    if args.json or args.status:
        print(json.dumps(out, indent=2, default=str))
    else:
        top = out.get("top") or {}
        print(
            f"executed={out.get('executed')} univ={out.get('universe_size')} "
            f"opps={out.get('opportunity_count')} qual={out.get('qualifying')} "
            f"best={top.get('net_bps')}bps ${top.get('est_profit_usd')} "
            f"{top.get('symbol')} {top.get('buy_venue')}→{top.get('sell_venue')} "
            f"skip={out.get('skip_reason')}"
        )
    return 0 if out.get("success") or out.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
