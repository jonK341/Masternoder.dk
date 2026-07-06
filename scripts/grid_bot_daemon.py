#!/usr/bin/env python3
"""Grid/market-maker bot daemon: ticks every configured asset on a loop.

Paper unless EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 and venue credentials are set.
Enforces per-asset inventory cap + hard loss cap (auto-halt) from the grid bot config.
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


def _load_config_env() -> None:
    """Load trader_app/config.json into env so the daemon uses the same single config as the app."""
    import json
    import re

    def _loose(text):
        out = []
        for line in text.splitlines():
            res, in_str, esc, i = [], False, False, 0
            while i < len(line):
                ch = line[i]
                if esc:
                    res.append(ch); esc = False; i += 1; continue
                if ch == "\\":
                    res.append(ch); esc = True; i += 1; continue
                if ch == '"':
                    in_str = not in_str; res.append(ch); i += 1; continue
                if (not in_str) and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
                res.append(ch); i += 1
            out.append("".join(res))
        return re.sub(r",(\s*[}\]])", r"\1", "\n".join(out))

    for p in (os.path.join(ROOT, "trader_app", "config.json"), os.path.join(os.getcwd(), "config.json")):
        if os.path.isfile(p):
            try:
                raw = open(p, encoding="utf-8").read()
                try:
                    cfg = json.loads(raw)
                except Exception:
                    cfg = json.loads(_loose(raw))
            except Exception:
                return
            for k in ("BINANCE_API_KEY", "BINANCE_API_SECRET",
                      "NONKYC_API_KEY", "NONKYC_API_SECRET", "NONKYC_API_PASSPHRASE",
                      "XEGGEX_API_KEY", "XEGGEX_API_SECRET", "XEGGEX_API_PASSPHRASE",
                      "EXCHANGE_VAULT_KEY", "EXCHANGE_ARBITRAGE_LIVE", "EXCHANGE_GRID_LIVE",
                      "SITE_URL", "SITE_ADMIN_KEY"):
                v = cfg.get(k)
                if v not in (None, "") and not os.environ.get(k):
                    os.environ[k] = str(v)
            print(f"[grid-daemon] loaded config: {p}")
            return
    print("[grid-daemon] no config.json found (looked in trader_app/ and CWD)")


def _diagnose() -> None:
    print("[diag] EXCHANGE_ARBITRAGE_LIVE=" + str(os.environ.get("EXCHANGE_ARBITRAGE_LIVE")))
    print("[diag] EXCHANGE_GRID_LIVE=" + str(os.environ.get("EXCHANGE_GRID_LIVE")))
    try:
        from backend.services.exchange_binance_withdraw_service import binance_credentials
        c = binance_credentials()
        print("[diag] binance credentials present: " + str(bool(c.get("api_key") and c.get("api_secret"))))
    except Exception as e:
        print("[diag] creds check error: " + repr(e))
    try:
        from backend.services import mn2_spork_service as spork
        print("[diag] exchange_live_spork_ok: " + str(spork.exchange_live_spork_ok()))
    except Exception as e:
        print("[diag] spork check error: " + repr(e))
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        print("[diag] arbitrage live_enabled: " + str(live_enabled()))
    except Exception as e:
        print("[diag] live_enabled error: " + repr(e))
    try:
        from backend.services.exchange_grid_bot_service import grid_live_enabled
        print("[diag] grid_live_enabled (paper if False): " + str(grid_live_enabled()))
    except Exception as e:
        print("[diag] grid_live_enabled error: " + repr(e))


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid/market-maker bot daemon")
    parser.add_argument("--once", action="store_true", help="Run one tick cycle and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between tick cycles")
    parser.add_argument("--paper", action="store_true", help="Force paper mode (no real orders)")
    parser.add_argument("--enable", action="store_true", help="Enable the grid bot config before running")
    args = parser.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass
    _load_config_env()
    _diagnose()

    from backend.services.exchange_grid_bot_service import run_all, grid_live_enabled, set_enabled
    if args.enable:
        set_enabled(True)
        print("[grid-daemon] grid bot enabled in config")

    dry = True if args.paper else None
    mode = "paper" if (args.paper or not grid_live_enabled()) else "LIVE"

    if args.once:
        print(run_all(dry_run=dry))
        return 0

    print(f"[grid-daemon] mode={mode} interval={args.interval}s")
    while True:
        try:
            res = run_all(dry_run=dry)
            if not res.get("skipped"):
                print(f"[grid-daemon] realized_pnl_usd={res.get('realized_pnl_usd')} "
                      f"ticks={len(res.get('ticks') or [])}")
        except Exception as exc:
            print(f"[grid-daemon] loop error: {exc}")
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
