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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from scripts.daemon_env import daemon_mode_label, load_dotenv

PROFILE_INTERVALS = {
    "max": {"exchange": 300, "casino": 300, "fast": 120},
    "standard": {"exchange": 300, "casino": 300, "fast": 0},
    "fast": {"exchange": 120, "casino": 180, "fast": 90},
    "live-only": {"exchange": 180, "casino": 0, "fast": 120},
}

# Aggressive live-profit mode (set EXCHANGE_LIVE_PROFIT_MAX=1 in .env)
_LIVE_PROFIT_MAX_INTERVALS = {"exchange": 120, "casino": 300, "fast": 60}


def _resolve_intervals(profile: str, iv: dict) -> dict:
    if os.environ.get("EXCHANGE_LIVE_PROFIT_MAX", "").strip().lower() in ("1", "true", "yes", "on"):
        if profile in ("max", "fast", "live-only"):
            return {**iv, **_LIVE_PROFIT_MAX_INTERVALS}
    return iv


def _exchange_once(auto_sweep: bool, profile: str) -> Dict[str, Any]:
    os.environ["EXCHANGE_PROFIT_PROFILE"] = profile
    from scripts.exchange_master_daemon import run_once

    return run_once(auto_sweep=auto_sweep)


def _extended_once(profile: str) -> Dict[str, Any]:
    from backend.services.exchange_extended_profit_service import run_extended_profit_tick

    return run_extended_profit_tick(profile=profile)


def _casino_dry_run(cli_dry_run: bool) -> bool:
    if cli_dry_run:
        return True
    return os.environ.get("CASINO_AGENT_DRY_RUN", "1").strip().lower() in ("1", "true", "yes", "on")


def _casino_once(*, dry_run: bool) -> Dict[str, Any]:
    from scripts.casino_agent_daemon import run_once

    return run_once(dry_run=dry_run)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _heartbeat_path() -> str:
    return os.path.join(ROOT, "logs", "daemon_all_profit_heartbeat.json")


def _write_heartbeat(loop: str, summary: str, extra: Optional[Dict[str, Any]] = None) -> None:
    path = _heartbeat_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "updated_at": _iso(),
        "loop": loop,
        "summary": summary,
        "profile": os.environ.get("EXCHANGE_PROFIT_PROFILE", "max"),
        "mode": daemon_mode_label(),
    }
    if extra:
        payload.update(extra)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        pass


def _best_arb_bps(arb: Dict[str, Any]) -> Optional[float]:
    best: Optional[float] = None
    for action in arb.get("actions") or []:
        if not isinstance(action, dict):
            continue
        row = action.get("best") if isinstance(action.get("best"), dict) else {}
        nb = row.get("net_bps")
        if nb is None:
            continue
        val = float(nb)
        if best is None or val > best:
            best = val
    return best


def _summarize_exchange(res: Dict[str, Any]) -> str:
    plat = res.get("platform") or {}
    results = plat.get("results") or {}
    arb = results.get("arbitrage") or {}
    ai = results.get("ai_trading") or {}
    cross = results.get("cross_trade") or {}
    ext = results.get("extended_profit") or {}
    best_bps = _best_arb_bps(arb)
    parts = [
        f"platform_ok={plat.get('success')}",
        f"arb_exec={arb.get('executed_count', '?')}/{arb.get('agent_count', '?')}",
    ]
    if best_bps is not None:
        parts.append(f"best_bps={best_bps:.1f}")
    live_trades = sum(
        1 for a in (arb.get("actions") or [])
        if a.get("executed") and ((a.get("execution") or {}).get("mode") or a.get("mode")) == "live"
    )
    if live_trades:
        parts.append(f"live_trades={live_trades}")
    parts.extend([
        f"ai_exec={ai.get('executed')}",
        f"cross_actions={len((cross.get('actions') or []))}",
        f"ext_exec={ext.get('executed_count', '?')}",
        f"user_agents={res.get('user_agent_ticks', 0)}",
        f"sweep={'yes' if res.get('sweep') else 'no'}",
    ])
    stash = res.get("sweep")
    if isinstance(stash, dict) and stash.get("amount_usd"):
        parts.append(f"swept_usd={stash.get('amount_usd')}")
    return " ".join(parts)


def _summarize_casino(res: Dict[str, Any]) -> str:
    skipped = res.get("skipped") or {}
    skip_bits = [f"{k}={v}" for k, v in list(skipped.items())[:2]]
    skip_str = f" skipped={','.join(skip_bits)}" if skip_bits else ""
    return (
        f"success={res.get('success')} ran={res.get('ran', res.get('agent_count', '?'))}"
        f"/{res.get('agent_count', '?')}{skip_str}"
    )


def _exchange_loop(interval: int, auto_sweep: bool, profile: str, stop: threading.Event) -> None:
    print(f"[all-profit] exchange loop interval={interval}s profile={profile} mode={daemon_mode_label()}", flush=True)
    while not stop.is_set():
        try:
            res = _exchange_once(auto_sweep, profile)
            summary = _summarize_exchange(res)
            print(f"[all-profit] exchange {summary}", flush=True)
            _write_heartbeat("exchange", summary)
        except Exception as exc:
            print(f"[all-profit] exchange error: {exc}", flush=True)
        stop.wait(max(15, interval))


def _fast_loop(interval: int, profile: str, stop: threading.Event) -> None:
    print(f"[all-profit] fast rescan loop interval={interval}s profile={profile}", flush=True)
    while not stop.is_set():
        try:
            res = _extended_once(profile)
            summary = (
                f"ext_exec={res.get('executed_count', 0)} strategies={res.get('strategy_count', 0)}"
            )
            print(f"[all-profit] fast {summary}", flush=True)
            _write_heartbeat("fast", summary)
        except Exception as exc:
            print(f"[all-profit] fast error: {exc}", flush=True)
        stop.wait(max(30, interval))


def _casino_loop(interval: int, dry_run: bool, stop: threading.Event) -> None:
    label = "dry_run" if dry_run else "live"
    print(f"[all-profit] casino loop interval={interval}s {label}", flush=True)
    while not stop.is_set():
        try:
            res = _casino_once(dry_run=dry_run)
            summary = _summarize_casino(res)
            print(f"[all-profit] casino {summary}", flush=True)
            _write_heartbeat("casino", summary)
        except Exception as exc:
            print(f"[all-profit] casino error: {exc}", flush=True)
        stop.wait(max(30, interval))


def _warm_flask_for_daemons() -> None:
    """Load Flask once before worker threads — avoids parallel blueprint registration."""
    if os.environ.get("DAEMON_QUIET", "").strip().lower() not in ("1", "true", "yes", "on"):
        return
    from src.app import create_app

    create_app()


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
    parser.add_argument("--skip-preflight", action="store_true", help="Skip startup health checks")
    parser.add_argument("--json", action="store_true", help="With --once, dump full JSON instead of one-line summary")
    args = parser.parse_args()

    load_dotenv()
    profile = os.environ.get("EXCHANGE_PROFIT_PROFILE") or args.profile
    os.environ["EXCHANGE_PROFIT_PROFILE"] = profile
    iv = _resolve_intervals(profile, PROFILE_INTERVALS.get(profile, PROFILE_INTERVALS["standard"]))
    ex_iv = args.exchange_interval or args.interval or iv["exchange"]
    cas_iv = args.casino_interval or args.interval or int(os.environ.get("CASINO_AGENT_INTERVAL") or 0) or iv["casino"]
    fast_iv = iv.get("fast") or 0
    casino_dry_run = _casino_dry_run(args.casino_dry_run)

    from scripts.exchange_master_daemon import _auto_sweep_default

    auto_sweep = _auto_sweep_default(args.auto_sweep) or profile == "live-only"
    skip_casino = args.skip_casino or profile == "live-only"

    if args.once:
        _warm_flask_for_daemons()
        out: Dict[str, Any] = {}
        if not args.skip_exchange:
            out["exchange"] = _exchange_once(auto_sweep, profile)
        if not skip_casino and not args.skip_exchange:
            out["casino"] = _casino_once(dry_run=casino_dry_run)
        if args.json:
            print(json.dumps(out, indent=2, default=str))
        else:
            if "exchange" in out:
                print(f"[all-profit] exchange {_summarize_exchange(out['exchange'])}", flush=True)
            if "casino" in out:
                print(f"[all-profit] casino {_summarize_casino(out['casino'])}", flush=True)
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
        dr = "dry_run" if casino_dry_run else "live"
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
            target=_casino_loop, args=(cas_iv, casino_dry_run, stop), name="casino", daemon=True,
        ))

    if not threads:
        print("Nothing to run.")
        return 1

    if not args.skip_preflight:
        from scripts.daemon_preflight import format_preflight, run_preflight
        pf = run_preflight()
        print(format_preflight(pf), flush=True)

    _warm_flask_for_daemons()

    for t in threads:
        t.start()

    print("[all-profit] running — Ctrl+C to stop", flush=True)
    try:
        while True:
            stop.wait(timeout=30)
            if stop.is_set():
                break
            dead = [t.name for t in threads if not t.is_alive()]
            if dead:
                print(f"[all-profit] ERROR worker thread(s) died: {', '.join(dead)}", flush=True)
                stop.set()
                break
    except KeyboardInterrupt:
        print("\n[all-profit] stopping...", flush=True)
        stop.set()
    for t in threads:
        t.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
