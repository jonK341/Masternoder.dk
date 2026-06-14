#!/usr/bin/env python3
"""Process pending webhook outbox entries."""
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
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    from backend.services.webhook_outbox import process_pending
    r = process_pending(limit=args.limit)
    print(json.dumps(r, indent=2))
    return 0 if r.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
