#!/usr/bin/env python3
"""Run ops digest (health alerts, reconciliation summary)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")


def main() -> int:
    from backend.services.exchange_ops_digest_service import run_ops_digest

    result = run_ops_digest()
    print(json.dumps(result, default=str))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
