#!/usr/bin/env python3
"""One-shot dual-farm arm tick (Binance ↔ NonKYC live arb + optional prefund)."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run dual-farm arm tick")
    ap.add_argument("--force", action="store_true", help="Run even if arm env-disabled")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true", help="Print arm status only")
    args = ap.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass

    from backend.services.exchange_dual_farm_arm_service import (
        dual_farm_arm_status,
        run_dual_farm_arm_tick,
    )

    if args.status:
        out = dual_farm_arm_status()
    else:
        out = run_dual_farm_arm_tick(force=args.force)
    if args.json or args.status:
        print(json.dumps(out, indent=2, default=str))
    else:
        top = out.get("top") or {}
        print(
            f"executed={out.get('executed')} qual={out.get('external_qualifying')} "
            f"best={top.get('net_bps')} {top.get('symbol')} "
            f"{top.get('buy_venue')}→{top.get('sell_venue')} "
            f"skip={out.get('skip_reason')} prefund={out.get('prefund')}"
        )
    return 0 if out.get("success") or out.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
