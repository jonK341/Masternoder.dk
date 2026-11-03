#!/usr/bin/env python3
"""Provision all pending rented hosts in one run, then fleet-activate (startmasternode all).

Usage:
  python3 scripts/mn2_activate_all_rented.py
  python3 scripts/mn2_activate_all_rented.py --batch-size 500
  python3 scripts/mn2_activate_all_rented.py --skip-drain   # ping + start only
  python3 scripts/mn2_activate_all_rented.py --summary        # short stdout
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _load_env() -> None:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    os.environ.setdefault("MN2_RPC_HEALTH_TIMEOUT", "60")
    os.environ.setdefault("MN2_RPC_TIMEOUT", "60")
    os.environ.setdefault("MN2_RPC_MAX_RETRIES", "2")


def _summary(result: dict) -> dict:
    before = result.get("snapshot_before") or {}
    after = result.get("snapshot_after") or {}
    rounds = result.get("drain_rounds") or []
    starts = result.get("starts") if isinstance(result.get("starts"), dict) else {}
    return {
        "success": result.get("success"),
        "error": result.get("error"),
        "note": result.get("note"),
        "rounds": len(rounds),
        "last_round": rounds[-1] if rounds else None,
        "pending_before": len(before.get("pending") or []),
        "pending_after": len(after.get("pending") or []),
        "active_before": before.get("active_count"),
        "active_after": after.get("active_count"),
        "started_ok": starts.get("started_ok"),
        "blockers_after": after.get("blockers"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate all rented MN2 masternodes in one process")
    parser.add_argument("--batch-size", type=int, default=250, help="Hosts per drain round")
    parser.add_argument("--max-rounds", type=int, default=200, help="Max drain rounds (safety cap)")
    parser.add_argument("--skip-drain", action="store_true", help="Skip provision loop; ping + start only")
    parser.add_argument("--summary", action="store_true", help="Print compact JSON summary")
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Log each drain round to stderr (use with --summary)",
    )
    args = parser.parse_args()
    _load_env()
    from backend.services.mn2_masternode_service import activate_all_rented_masternodes

    if args.progress:

        class _Progress:
            round_idx = 0

            @staticmethod
            def hook(event: dict) -> None:
                print(
                    f"[activate-all] round {event.get('round')} "
                    f"pending={event.get('pending_before')} "
                    f"processed={event.get('processed')} "
                    f"activated={event.get('activated')} "
                    f"waiting_conf={event.get('waiting_confirmations')}",
                    file=sys.stderr,
                    flush=True,
                )

        progress_hook = _Progress.hook
    else:
        progress_hook = None

    result = activate_all_rented_masternodes(
        batch_size=args.batch_size,
        max_rounds=args.max_rounds,
        skip_drain=args.skip_drain,
        skip_explorer=True,
        progress_hook=progress_hook,
    )
    if args.summary:
        print(json.dumps(_summary(result), indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str)[:500000])
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
