#!/usr/bin/env python3
"""Run on prod: platform_treasury MN2 balance + optional test credit + liquidity tick."""
from __future__ import annotations

import json
import os
import sys

ROOT = "/var/www/html"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from backend.services.exchange_treasury_liquidity_service import run_liquidity_tick
from backend.services.unified_points_database import unified_points_db

credit_mn2 = float(os.environ.get("TREASURY_TEST_CREDIT_MN2", "0") or 0)
if credit_mn2 > 0:
    ref = f"ops-treasury-test:{int(credit_mn2)}"
    result = unified_points_db.add_points(
        "platform_treasury", "mn2_balance", credit_mn2,
        source="ops_treasury_test", metadata={"reference": ref},
    )
    print("credit_result", json.dumps(result))

pts = (unified_points_db.get_all_points("platform_treasury").get("points") or {})
print("prod_treasury_mn2", pts.get("mn2_balance", 0))
print("liquidity_tick", json.dumps(run_liquidity_tick()))
