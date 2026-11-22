#!/usr/bin/env python3
"""Price battle daemon: buy ~$5 lots, hold until profit, log buys + sells.

Paper by default. Real orders require:
  EXCHANGE_PRICE_BATTLE_LIVE=1
  EXCHANGE_ARBITRAGE_LIVE=1
  Binance API keys
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

try:
    from scripts.daemon_env import load_dotenv
except Exception:
    def load_dotenv() -> None:
        return None


def _banner() -> str:
    try:
        from backend.services.exchange_price_battle_service import live_enabled, load_config, status
        cfg = load_config()
        st = status()
        if not cfg.get("enabled", True):
            return "DISABLED (config enabled=false)"
        if not live_enabled():
            return "PAPER (set EXCHANGE_PRICE_BATTLE_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1)"
        return (
            f"LIVE-ready pos=${cfg.get('position_usd')} "
            f"open={st.get('open_count')}/{cfg.get('max_open_positions')} "
            f"min_profit_bps={cfg.get('min_profit_bps')}"
        )
    except Exception as exc:
        return f"unknown ({exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Exchange price-battle hold-to-profit daemon")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Force paper even if live gate on")
    parser.add_argument("--interval", type=int, default=0)
    args = parser.parse_args()
    load_dotenv()

    from backend.services.exchange_price_battle_service import load_config, run_tick

    cfg = load_config()
    interval = int(args.interval or cfg.get("daemon_interval_sec") or 120)
    mode = _banner()

    if args.once:
        res = run_tick(force=args.force, dry_run=True if args.dry_run else None)
        print(f"[price-battle] mode={mode}")
        print(res)
        return 0 if res.get("success") else 1

    print(f"[price-battle] interval={interval}s mode={mode}")
    while True:
        try:
            res = run_tick(force=args.force, dry_run=True if args.dry_run else None)
            acts = res.get("actions") or []
            summary = ", ".join(
                f"{a.get('action')}:{a.get('symbol') or a.get('reason') or ''}"
                for a in acts
            )
            print(
                f"[price-battle] tick={res.get('tick_count')} "
                f"open={res.get('open_positions')} {summary}"
            )
        except KeyboardInterrupt:
            print("[price-battle] stopped")
            return 0
        except Exception as exc:
            print(f"[price-battle] error: {exc}")
        time.sleep(max(30, interval))


if __name__ == "__main__":
    raise SystemExit(main())
