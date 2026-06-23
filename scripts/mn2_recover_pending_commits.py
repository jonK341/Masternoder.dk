#!/usr/bin/env python3
"""Recover stale MN2 withdrawal balance commits (reserved but never finalized)."""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-minutes", type=int, default=30)
    args = ap.parse_args()

    from backend.services.mn2_balance_commit import recover_stale

    r = recover_stale(max_age_minutes=args.max_age_minutes)
    print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
