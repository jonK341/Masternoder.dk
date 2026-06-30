#!/usr/bin/env python3
"""Run every local profit daemon in one process (exchange + casino).

Exchange tick (via exchange_master_daemon.run_once):
  - Cross-venue arbitrage (6+ paper agents + live Binance/NonKYC)
  - AI multi-venue trader (18 symbols)
  - Internal cross-trade bots (7 rotation agents)
  - Extended strategies (stablecoin peg, triangular, meme, defi, payments)
  - User marketplace agents, sales pool, mesh matcher, treasury liquidity
  - PayPal auto-sweep when profit pool is ready

Casino tick (via casino_agent_daemon.run_once):
  - Autonomous casino agents (Nova, Luna, Sage, Ember, Iris)

Profiles (EXCHANGE_PROFIT_PROFILE env or --profile):
  max       — all extended strategies + 120s fast rescan loop
  standard  — core extended strategies (default)
  fast      — shorter intervals, aggressive scans
  live-only — exchange live farm only, no casino
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.daemon_env import daemon_mode_label, load_dotenv

PROFILE_INTERVALS = {
    "max": {"exchange": 300, "casino": 300, "fast": 120},
    "standard": {"exchange": 300, "casino": 300, "fast": 0},
    "fast": {"exchange": 120, "casino": 180, "fast": 90},
    "live-only": {"exchange": 180, "casino": 0, "fast": 120},
}


def _exchange_once(auto_sweep: bool, profile: str) -> Dict[str, Any]:
    os.environ["EXCHANGE_PROFIT_PROFILE"] = profile
    from scripts.exchange_master_daemon import run_once

    return run_once(auto_sweep=auto_sweep)


def _extended_once(profile: str) -> Dict[str, Any]:
    from backend.services.exchange_extended_profit_service import run_extended_profit_tick

    return run_extended_profit_tick(profile=profile)


def _casino_once(*, dry_run: bool) -> Dict[str, Any]:
    from scripts.casino_agent_daemon import run_once

    return run_once(dry_run=dry_run)


def _summarize_exchange(res: Dict[str, Any]) -> str:
    plat = res.get("platform") or {}
    results = plat.get("results") or {}
    arb = results.get("arbitrage") or {}
    ai = results.get("ai_trading") or {}
    cross = results.get("cross_trade") or {}
    ext = results.get("extended_profit") or {}
    parts = [
        f"platform_ok={plat.get('success')}",
        f"arb_exec={arb.get('executed_count', '?')}/{arb.get('agent_count', '?')}",
        f"ai_exec={ai.get('executed')}",
        f"cross_actions={len((cross.get('actions') or []))}",
        f"ext_exec={ext.get('executed_count', '?')}",
        f"user_agents={res.get('user_agent_ticks', 0)}",
        f"sweep={'yes' if res.get('sweep') else 'no'}",
    ]
    return " ".join(parts)


def _summarize_casino(res: Dict[str, Any]) -> str:
    return f"success={res.get('success')} ran={res.get('ran', res.get('agent_count', '?'))}"


def _exchange_loop(interval: int, auto_sweep: bool, profile: str, stop: threading.Event) -> None:
    print(f"[all-profit] exchange loop interval={interval}s profile={profile} mode={daemon_mode_label()}")
    while not stop.is_set():
        try:
            res = _exchange_once(auto_sweep, profile)
            print(f"[all-profit] exchange {_summarize_exchange(res)}")
        except Exception as exc:
            print(f"[all-profit] exchange error: {exc}")
        stop.wait(max(15, interval))


def _fast_loop(interval: int, profile: str, stop: threading.Event) -> None:
    print(f"[all-profit] fast rescan loop interval={interval}s profile={profile}")
    while not stop.is_set():
        try:
            res = _extended_once(profile)
            print(f"[all-profit] fast ext_exec={res.get('executed_count', 0)} strategies={res.get('strategy_count', 0)}")
        except Exception as exc:
            print(f"[all-profit] fast error: {exc}")
        stop.wait(max(30, interval))


def _casino_loop(interval: int, dry_run: bool, stop: threading.Event) -> None:
    label = "dry_run" if dry_run else "live"
    print(f"[all-profit] casino loop interval={interval}s {label}")
    while not stop.is_set():
        try:
            res = _casino_once(dry_run=dry_run)
            print(f"[all-profit] casino {_summarize_casino(res)}")
        except Exception as exc:
            print(f"[all-profit] casino error: {exc}")
        stop.wait(max(30, interval))


def main() -> int:
    parser = argparse.ArgumentParser(description="All profit daemons in one process")
    parser.add_argument("--once", action="store_true", help="Single tick and exit")
    parser.add_argument("--profile", choices=["max", "standard", "fast", "live-only"], default="max",
                        help="Profit strategy profile (default: max = everything)")
    parser.add_argument("--interval", type=int, default=0, help="Override main exchange interval")
    parser.add_argument("--exchange-interval", type=int, default=0, help="Override exchange interval")
    parser.add_argument("--casino-interval", type=int, default=0, help="Override casino interval")
    parser.add_argument("--skip-casino", action="store_true", help="Exchange engines only")
    parser.add_argument("--skip-exchange", action="store_true", help="Casino agents only")
    parser.add_argument("--auto-sweep", action="store_true", help="Force PayPal sweep when ready")
    parser.add_argument("--casino-dry-run", action="store_true", help="Casino bets simulated only")
    args = parser.parse_args()

    load_dotenv()
    profile = os.environ.get("EXCHANGE_PROFIT_PROFILE") or args.profile
    os.environ["EXCHANGE_PROFIT_PROFILE"] = profile
    iv = PROFILE_INTERVALS.get(profile, PROFILE_INTERVALS["standard"])
    ex_iv = args.exchange_interval or args.interval or iv["exchange"]
    cas_iv = args.casino_interval or args.interval or iv["casino"]
    fast_iv = iv.get("fast") or 0

    from scripts.exchange_master_daemon import _auto_sweep_default

    auto_sweep = _auto_sweep_default(args.auto_sweep) or profile == "live-only"
    skip_casino = args.skip_casino or profile == "live-only"

    if args.once:
        out: Dict[str, Any] = {}
        if not args.skip_exchange:
            out["exchange"] = _exchange_once(auto_sweep, profile)
        if not skip_casino and not args.skip_exchange:
            out["casino"] = _casino_once(dry_run=args.casino_dry_run)
        print(json.dumps(out, indent=2, default=str))
        return 0 if out else 1

    stop = threading.Event()
    threads: list[threading.Thread] = []

    print("=" * 72)
    print("MasterNoder — ALL profit daemons (single process)")
    print(f"  profile={profile} mode={daemon_mode_label()} auto_sweep={auto_sweep}")
    if not args.skip_exchange:
        print("  exchange engines:")
        print("    - 12 spatial arb agents (incl. meme, defi, live dual, triangular)")
        print("    - AI trader (18 symbols, 10 venues)")
        print("    - 7 internal cross-trade bots")
        print("    - extended: stablecoin peg, triangular, meme, defi, payments")
        print(f"    interval={ex_iv}s")
        if fast_iv:
            print(f"    fast rescan interval={fast_iv}s")
    if not skip_casino and not args.skip_exchange:
        dr = "dry_run" if args.casino_dry_run else "live"
        print(f"  casino: Nova/Luna/Sage/Ember/Iris ({cas_iv}s, {dr})")
    print("=" * 72)

    if not args.skip_exchange:
        threads.append(threading.Thread(
            target=_exchange_loop, args=(ex_iv, auto_sweep, profile, stop), name="exchange", daemon=True,
        ))
        if fast_iv:
            threads.append(threading.Thread(
                target=_fast_loop, args=(fast_iv, profile, stop), name="fast", daemon=True,
            ))
    if not skip_casino and not args.skip_exchange:
        threads.append(threading.Thread(
            target=_casino_loop, args=(cas_iv, args.casino_dry_run, stop), name="casino", daemon=True,
        ))

    if not threads:
        print("Nothing to run.")
        return 1

    for t in threads:
        t.start()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[all-profit] stopping...")
        stop.set()
        for t in threads:
            t.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
