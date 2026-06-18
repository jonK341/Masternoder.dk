#!/usr/bin/env python3
"""Upsert camgirls performers from a JSON file (Phase 1c ops onboarding).

Usage:
  python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.template.json
  python scripts/camgirls_onboard_performers.py --file performers.json --dry-run
  python scripts/camgirls_onboard_performers.py --deactivate-demos

Each performer object must include: id, display_name, payout_address, unlock_price_mn2.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Onboard camgirls performers from JSON")
    parser.add_argument("--file", help="JSON with { performers: [...] }")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not write")
    parser.add_argument(
        "--deactivate-demos",
        action="store_true",
        help="Set performer_demo_* rows to active=false (Phase 1c go-live)",
    )
    args = parser.parse_args()

    if args.deactivate_demos:
        if args.dry_run:
            print("[dry-run] would deactivate ids matching performer_demo_*")
            return 0
        from backend.services.camgirls_service import deactivate_demo_performers
        result = deactivate_demo_performers()
        print(f"Deactivated {result.get('count', 0)} demo performers: {', '.join(result.get('deactivated') or [])}")
        return 0 if result.get("success") else 1

    if not args.file:
        print("--file required unless using --deactivate-demos", file=sys.stderr)
        return 1

    path = args.file
    if not os.path.isabs(path):
        path = os.path.join(BASE, path)
    if not os.path.isfile(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    rows = data.get("performers") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        print("No performers array in file", file=sys.stderr)
        return 1

    from backend.services.camgirls_service import upsert_performer

    ok = 0
    for row in rows:
        if not isinstance(row, dict):
            print("Skip non-object row")
            continue
        pid = (row.get("id") or "").strip()
        if not pid:
            print("Skip row missing id")
            continue
        if not row.get("payout_address"):
            print(f"Skip {pid}: payout_address required")
            continue
        if args.dry_run:
            print(f"[dry-run] would upsert {pid} ({row.get('display_name')})")
            ok += 1
            continue
        result = upsert_performer(row)
        if result.get("success"):
            print(f"Upserted {pid}")
            ok += 1
        else:
            print(f"Failed {pid}: {result.get('error')}", file=sys.stderr)
    print(f"Done: {ok}/{len(rows)} performers")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
