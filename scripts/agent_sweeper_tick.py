#!/usr/bin/env python3
"""Sweep agent wallet alts into exchange_sales_pool."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")


def main() -> int:
    from backend.services.exchange_agent_sweeper_service import run_agent_sweeper

    result = run_agent_sweeper()
    print(json.dumps(result, default=str))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
