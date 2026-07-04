#!/usr/bin/env python3
"""Profile profit monitor_status steps (run on server)."""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def t(label, fn):
    s = time.time()
    r = fn()
    print(label, round(time.time() - s, 2), "s", type(r).__name__)
    return r


def main() -> int:
    from backend.services import crypto_exchange_service as ex

    t("read_hb", lambda: ex._read_json(os.path.join(ROOT, "logs/daemon_all_profit_heartbeat.json"), {}))
    t("payout_monitor", lambda: __import__(
        "backend.services.exchange_payout_service", fromlist=["payout_monitor_snapshot"]
    ).payout_monitor_snapshot())
    t("payout_light", lambda: __import__(
        "backend.services.exchange_payout_service", fromlist=["payout_status"]
    ).payout_status(light=True))
    t("treasury", lambda: __import__(
        "backend.services.exchange_treasury_service", fromlist=["treasury_status"]
    ).treasury_status())
    t("ppp", lambda: __import__(
        "backend.services.exchange_profit_path_service", fromlist=["profit_path_summary"]
    ).profit_path_summary(hours=24))
    t("critical", lambda: __import__(
        "backend.services.exchange_profit_agent_skills_service", fromlist=["critical_problems_top25"]
    ).critical_problems_top25(refresh=False))
    t("venue_binance", lambda: __import__(
        "backend.services.exchange_venue_api_service", fromlist=["parse_spot_balances"]
    ).parse_spot_balances("binance", dry_run=False))
    t("monitor", lambda: __import__(
        "backend.services.profit_daemon_monitor_service", fromlist=["monitor_status"]
    ).monitor_status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
