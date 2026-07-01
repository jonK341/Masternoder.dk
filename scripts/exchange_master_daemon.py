#!/usr/bin/env python3
"""24/7 master daemon: runs every trading engine + auto-sweep on a loop.

Ticks (in order), respecting the owner control board kill-switch / supervisor pauses:
  1. Platform bots (arbitrage paper + internal cross-trade) via the control board.
  2. All user-owned marketplace agents (profit accrues to each buyer).
  3. Optional auto-sweep of net platform profit to the owner's PayPal (or Binance stash).

Everything is paper until the live gates are set (see docs/EXCHANGE_CROSS_VENUE_ARBITRAGE.md).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv, daemon_mode_label, is_arbitrage_live, is_paypal_payout_live


def _auto_sweep_default(cli_flag: bool) -> bool:
    if cli_flag:
        return True
    load_dotenv()
    return is_arbitrage_live() or is_paypal_payout_live()


def _tick_all_user_agents() -> int:
    """Run a tick for every user that owns marketplace agents."""
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt

    ran = 0
    udir = mkt._USER_AGENTS_DIR
    if not os.path.isdir(udir):
        return 0
    for name in os.listdir(udir):
        if not name.endswith(".json"):
            continue
        uid = name[:-5]
        try:
            res = mkt.run_all_user_agents(uid)
            ran += int(res.get("ran") or 0)
        except Exception as exc:
            print(f"[master-daemon] user {uid} error: {exc}")
    return ran


def run_once(auto_sweep: bool = False) -> dict:
    from backend.services.trading_bots_control_service import run_all_bots

    out = {"platform": None, "user_agent_ticks": 0, "auto_renewals": None, "sweep": None}
    try:
        out["platform"] = run_all_bots()
    except Exception as exc:
        out["platform"] = {"success": False, "error": str(exc)}

    try:
        from backend.services.exchange_sales_pool_service import run_sales_pool_tick
        out["sales_pool"] = run_sales_pool_tick()
    except Exception as exc:
        out["sales_pool"] = {"success": False, "error": str(exc)}

    try:
        from backend.services.exchange_rental_service import process_auto_renewals

        out["auto_renewals"] = process_auto_renewals()
    except Exception as exc:
        out["auto_renewals"] = {"success": False, "error": str(exc)}

    out["user_agent_ticks"] = _tick_all_user_agents()

    try:
        from backend.services.exchange_daemon_matcher_service import run_mesh_tick
        out["daemon_mesh"] = run_mesh_tick()
    except Exception as exc:
        out["daemon_mesh"] = {"success": False, "error": str(exc)}

    if auto_sweep:
        try:
            from backend.services.exchange_payout_service import execute_sweep, payout_status
            if payout_status().get("ready_to_sweep"):
                out["sweep"] = execute_sweep()
        except Exception as exc:
            out["sweep"] = {"success": False, "error": str(exc)}

    try:
        from backend.services.exchange_treasury_liquidity_service import run_liquidity_tick
        out["treasury_liquidity"] = run_liquidity_tick()
    except Exception as exc:
        out["treasury_liquidity"] = {"success": False, "error": str(exc)}

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Exchange master 24/7 daemon")
    parser.add_argument("--once", action="store_true", help="Run one full tick and exit")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between ticks")
    parser.add_argument("--auto-sweep", action="store_true",
                        help="Auto-sweep net profit to PayPal when ready (default ON in live mode)")
    args = parser.parse_args()
    load_dotenv()
    auto_sweep = _auto_sweep_default(args.auto_sweep)

    if args.once:
        print(run_once(auto_sweep=auto_sweep))
        return 0

    print(f"[master-daemon] mode={daemon_mode_label()} interval={args.interval}s auto_sweep={auto_sweep}")
    while True:
        try:
            res = run_once(auto_sweep=auto_sweep)
            plat = (res.get("platform") or {})
            print(f"[master-daemon] platform_ok={plat.get('success')} "
                  f"user_ticks={res.get('user_agent_ticks')} sweep={'yes' if res.get('sweep') else 'no'}")
        except Exception as exc:
            print(f"[master-daemon] loop error: {exc}")
        time.sleep(max(15, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
