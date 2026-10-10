#!/usr/bin/env python3
"""Print staking reconcile report (JSON). Run on server from /var/www/html."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.mn2_staking_reconcile_service import reconcile


def main() -> int:
    rep = reconcile()
    slim = {
        "ok": rep.get("ok"),
        "failed_checks": rep.get("failed_checks"),
        "checks": rep.get("checks"),
        "totals": rep.get("totals"),
    }
    print(json.dumps(slim, indent=2))
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
