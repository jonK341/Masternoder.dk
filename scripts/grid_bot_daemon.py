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
        text = (text.replace("\u201c", '"').replace("\u201d", '"')
                    .replace("\u2018", "'").replace("\u2019", "'")
                    .replace("\u00a0", " ").replace("\ufeff", ""))
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
        repaired = []
        for line in out:
            m = re.match(r'^(\s*"[^"]*"\s*:\s*)(.+?)(,?)\s*$', line)
            if m:
                prefix, val, comma = m.groups()
                v = val.strip()
                if v and v[0] not in '"{[-0123456789' and v not in ("true", "false", "null"):
                    core = v.strip('"')
                    if re.match(r'^[A-Za-z0-9_.\-/:+=@]+$', core):
                        line = prefix + '"' + core + '"' + comma
            repaired.append(line)
        return re.sub(r",(\s*[}\]])", r"\1", "\n".join(repaired))

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
                      "MN2_SPORK_GATES", "SITE_URL", "SITE_ADMIN_KEY"):
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
        from backend.services.exchange_grid_bot_service import grid_live_enabled, load_config, grid_targets
        print("[diag] grid_live_enabled (paper if False): " + str(grid_live_enabled()))
        cfg = load_config()
        allow = bool(cfg.get("allow_sell_existing_inventory"))
        print("[diag] allow_sell_existing_inventory: " + str(allow))
        targets = grid_targets(cfg)
        per_venue = {}
        for v, a in targets:
            per_venue.setdefault(v, []).append(a)
        for v, alist in per_venue.items():
            print(f"[diag] venue {v}: {len(alist)} pairs")
        from backend.services import exchange_venue_api_service as vapi
        for v in per_venue:
            has = vapi.venue_has_credentials(v)
            print(f"[diag] {v} credentials present: {has}")
            if allow and grid_live_enabled() and has:
                try:
                    bals = vapi.parse_spot_balances(v, dry_run=False)
                    held = {a: round(float(bals.get(a.upper()) or 0), 8) for a in per_venue[v]
                            if float(bals.get(a.upper()) or 0) > 0}
                    if held:
                        print(f"[diag] {v} coins held (sellable): {held}")
                except Exception as be:
                    print(f"[diag] {v} balance read error: {be!r}")
    except Exception as e:
        print("[diag] grid_live_enabled error: " + repr(e))


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid/market-maker bot daemon")
    parser.add_argument("--once", action="store_true", help="Run one tick cycle and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between tick cycles")
    parser.add_argument("--paper", action="store_true", help="Force paper mode (no real orders)")
    parser.add_argument("--enable", action="store_true", help="Enable the grid bot config before running")
    parser.add_argument("--reseed", action="store_true",
                        help="Cancel tracked open orders + clear them so a fresh full grid is placed "
                             "(use after funding more capital)")
    parser.add_argument("--autoselect", action="store_true",
                        help="Profit-rank candidate pairs (ledger + live arb, net of fees) and add "
                             "the winners to the multi-venue config before running")
    parser.add_argument("--autoselect-min-score", type=float, default=3.0,
                        help="Minimum profit score to add a pair with --autoselect (default 3.0)")
    parser.add_argument("--cross-scan", action="store_true",
                        help="Search cross-venue price differences across Binance/NonKYC/XeggeX and "
                             "add the profitable pairs to the config before running")
    parser.add_argument("--cross-min-bps", type=float, default=5.0,
                        help="Minimum net cross-venue difference (bps) to add a pair (default 5.0)")
    parser.add_argument("--cross-trade", action="store_true",
                        help="Auto-trader: each loop, SEARCH cross-venue differences and EXECUTE the "
                             "spatial arb the instant one clears the threshold (paper unless "
                             "EXCHANGE_ARBITRAGE_LIVE=1 + EXCHANGE_CROSS_TRADE_LIVE=1)")
    args = parser.parse_args()

    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass
    _load_config_env()
    _diagnose()

    from backend.services.exchange_grid_bot_service import (run_all, grid_live_enabled, set_enabled,
                                                            reset_open_orders, autoselect_profit_pairs,
                                                            autoselect_cross_venue_pairs)
    if args.enable:
        set_enabled(True)
        print("[grid-daemon] grid bot enabled in config")
    if args.autoselect:
        sel = autoselect_profit_pairs(min_score=args.autoselect_min_score, include_live=True, apply=True)
        chosen = ", ".join(r["symbol"] for r in (sel.get("selected") or [])) or "(none cleared threshold)"
        print(f"[grid-daemon] autoselect: profit-ranked pairs -> {chosen}")
        if sel.get("applied"):
            print(f"[grid-daemon] autoselect applied — {sel.get('targets_total')} total targets")
    if args.cross_scan:
        cx = autoselect_cross_venue_pairs(min_net_bps=args.cross_min_bps, apply=True)
        diffs = cx.get("differences") or []
        top = ", ".join(f"{d['symbol']}({d['net_bps']}bps {d['route']})" for d in diffs[:6]) or "(none above threshold)"
        print(f"[grid-daemon] cross-venue differences (>= {args.cross_min_bps} bps): {top}")
        if cx.get("applied"):
            print(f"[grid-daemon] cross-scan applied — {cx.get('targets_total')} total targets")
        elif cx.get("error"):
            print(f"[grid-daemon] cross-scan error: {cx.get('error')}")
    if args.reseed:
        r = reset_open_orders()
        print(f"[grid-daemon] reseed: cleared {r.get('cleared_orders')} tracked orders — full grid will re-post")

    dry = True if args.paper else None
    mode = "paper" if (args.paper or not grid_live_enabled()) else "LIVE"

    ct = None
    if args.cross_trade:
        from backend.services import exchange_cross_trade_service as ct
        ct.set_enabled(True)
        print(f"[grid-daemon] cross-trade auto-execute ON (live={ct.cross_trade_live_enabled()})")

    def _cross_trade_pass():
        if ct is None:
            return
        try:
            r = ct.run_once(dry_run=dry)
            fired = r.get("executed") or []
            if fired:
                for e in fired:
                    print(f"[cross-trade] {e['mode'].upper()} {e['symbol']} {e['route']} "
                          f"net={e['net_bps']}bps ok={e['success']} ~${e.get('est_profit_usd') or 0}")
            elif r.get("halted"):
                print(f"[cross-trade] HALTED: {r.get('reason')}")
        except Exception as exc:
            print(f"[cross-trade] error: {exc}")

    if args.once:
        print(run_all(dry_run=dry))
        _cross_trade_pass()
        return 0

    print(f"[grid-daemon] mode={mode} interval={args.interval}s")
    while True:
        try:
            res = run_all(dry_run=dry)
            if not res.get("skipped"):
                ticks = res.get("ticks") or []
                errs = [e for t in ticks for e in (t.get("place_errors") or [])]
                notes = [t.get("reconcile_note") for t in ticks if t.get("reconcile_note")]
                oo = sum(int(t.get("open_orders") or 0) for t in ticks)
                print(f"[grid-daemon] realized_pnl_usd={res.get('realized_pnl_usd')} "
                      f"ticks={len(ticks)} open_orders={oo}")
                if notes:
                    print(f"[grid-daemon] RECONCILE: {notes} (fills not inferred this tick)")
                if errs:
                    print(f"[grid-daemon] ORDER PLACEMENT ISSUES: {errs[:4]}")
                cbev = res.get("circuit_breaker_events") or []
                if cbev:
                    print(f"[grid-daemon] CIRCUIT BREAKER: {cbev}")
                if res.get("paused_venues"):
                    print(f"[grid-daemon] paused venues (skipped): {res.get('paused_venues')}")
            _cross_trade_pass()
        except Exception as exc:
            print(f"[grid-daemon] loop error: {exc}")
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
