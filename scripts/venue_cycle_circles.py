#!/usr/bin/env python3
"""CLI for Binance ↔ NonKYC cycle circles (profit preview + optional execute/fill).

Core planning/execute lives in ``backend.services.venue_cycle_circles_service``
(also used by the profit daemon cron loop).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from backend.services.venue_cycle_circles_service import (  # noqa: E402
    DEFAULT_SYMBOLS,
    FILLABLE,
    execute_arb_circle,
    plan_circles,
    refresh_balances,
)

_refresh_balances = refresh_balances


def _print_plan(plan: Dict[str, Any]) -> None:
    q = plan.get("quotes") or {}
    print("QUOTES")
    print(
        f"  Binance USDC={q.get('binance_usdc')} floor={q.get('binance_floor')} "
        f"spendable={q.get('binance_spendable')}"
    )
    print(
        f"  NonKYC  USDT={q.get('nonkyc_usdt')} floor={q.get('nonkyc_floor')} "
        f"spendable={q.get('nonkyc_spendable')}"
    )
    print(
        f"FEES {plan.get('fees_bps')}  notional=${plan.get('notional_usd')}  "
        f"circles={plan.get('circle_count')}"
    )
    print("LEGS (profit before run) — 3-leg arb per direction")
    for row in plan.get("rows") or []:
        a = row["binance_to_nonkyc"]
        b = row["nonkyc_to_binance"]
        print(
            f"  {row['symbol']}: BN ${row['bn_usd']} / NK ${row['nk_usd']} | "
            f"BN->NK net {a.get('net_bps')}bps est ${a.get('est_profit_usd')} "
            f"fund ${a.get('max_funded_usd')} | "
            f"NK->BN net {b.get('net_bps')}bps est ${b.get('est_profit_usd')} "
            f"fund ${b.get('max_funded_usd')}"
        )
    skipped = plan.get("skipped_symbols") or []
    if skipped:
        print(f"SKIPPED (no dual ticker): {', '.join(skipped)}")
    print("PROFITABLE + FUNDABLE")
    prof = plan.get("profitable_arb") or []
    if not prof:
        print("  (none)")
    for a in prof:
        print(
            f"  {a.get('direction')} {a.get('symbol')}: net {a.get('net_bps')}bps "
            f"est ${a.get('est_profit_usd')} fund ${a.get('max_funded_usd')} "
            f"legs={a.get('leg_count')}"
        )
    print(f"SUM est arb profit ${plan.get('est_arb_profit_usd')}")
    print("INVENTORY CIRCLES (multi-leg reshape — est usually negative = friction)")
    invs = plan.get("inventory_circles") or []
    if not invs:
        print("  (none)")
    for inv in invs[:16]:
        print(
            f"  {inv.get('why')}: {inv.get('leg_count')}legs net {inv.get('net_bps')}bps "
            f"est ${inv.get('est_profit_usd')} on ${inv.get('notional_usd')}"
        )
    print("FILL GAPS")
    gaps = plan.get("fill_gaps") or []
    if not gaps:
        print("  (none)")
    for g in gaps[:16]:
        print(
            f"  {g['venue']} {g['symbol']}: have ${g['have_usd']} "
            f"need ${g['target_usd']} gap ${g['gap_usd']}"
        )


def _raise_from_ada(venue: str, *, needed_usd: float, keep_usd: float = 40.0) -> float:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn

    refresh_balances()
    bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
    ada = float(bals.get("ADA") or 0)
    tick = conn.fetch_ticker(venue, "ADA") or {}
    bid = float(tick.get("bid") or 0)
    if bid <= 0 or ada <= 0:
        print(f"FILL raise skipped ({venue}): no ADA/bid", flush=True)
        return 0.0
    inv_usd = ada * bid
    keep = min(keep_usd, max(15.0, inv_usd * 0.35))
    sellable_usd = max(0.0, inv_usd - keep)
    raise_usd = min(needed_usd, sellable_usd)
    qty = round((raise_usd / bid) * 1.005, 2)
    quote = "USDC" if venue == "binance" else "USDT"
    if qty < 5 or raise_usd < 10:
        print(
            f"FILL raise skipped ({venue}): sellable~${sellable_usd:.2f} need~${needed_usd:.2f}",
            flush=True,
        )
        return 0.0
    print(
        f"FILL raise {quote} on {venue}: sell ADA qty={qty} ~${raise_usd:.2f} "
        f"(keep~${keep:.0f} ADA)",
        flush=True,
    )
    o = vapi.place_market_order(venue, "ADA", "sell", qty, dry_run=False, quote=quote)
    body = o.get("body") if isinstance(o.get("body"), dict) else {}
    raised = float(body.get("cummulativeQuoteQty") or 0)
    if raised <= 0 and o.get("success"):
        raised = raise_usd
    print(f"  raised {raised} status={body.get('status') or o.get('status')}", flush=True)
    refresh_balances()
    return raised


def _free_quote(venue: str) -> float:
    from backend.services import exchange_venue_api_service as vapi

    if venue == "binance":
        from backend.services.exchange_binance_withdraw_service import get_spot_asset_free

        r = get_spot_asset_free("USDC")
        body = r.get("body") or {}
        for b in body.get("balances") or []:
            if str(b.get("asset", "")).upper() == "USDC":
                return float(b.get("free") or 0)
        return float(r.get("free") or 0)
    bals = vapi.parse_spot_balances("nonkyc", dry_run=False, force_refresh=True) or {}
    return float(bals.get("USDT") or 0)


def execute_fill_venue(
    venue: str,
    symbols: List[str],
    *,
    fill_usd_each: float,
    raise_from_ada: bool = True,
    ignore_quote_floor: bool = True,
) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn

    venue = str(venue).lower()
    quote = "USDC" if venue == "binance" else "USDT"
    needed = float(fill_usd_each) * max(1, len(symbols))
    cash = _free_quote(venue)
    raised = 0.0
    if raise_from_ada and cash < needed + 2:
        raised = _raise_from_ada(venue, needed_usd=needed + 5 - cash)
        cash = _free_quote(venue)

    est_cost_bps = 15.0
    est_cost = round(needed * est_cost_bps / 10000.0, 4)
    print(
        f"FILL plan ({venue}): ${fill_usd_each} x {symbols} "
        f"(need ~${needed:.2f}, {quote}={cash:.2f}, est friction ~${est_cost})",
        flush=True,
    )

    results = []
    per = float(fill_usd_each)
    for sym in symbols:
        cash = _free_quote(venue)
        budget = cash - 1.0
        if not ignore_quote_floor:
            from backend.services import exchange_swap_rotation_service as rot

            spend_fn = getattr(rot, "_spendable_quote_usd", None)
            if callable(spend_fn):
                budget = min(budget, float(spend_fn(venue)))
        usd = round(min(per, budget), 2)
        if usd < 5:
            results.append({
                "venue": venue, "symbol": sym, "skipped": True,
                "reason": "insufficient_quote", "quote_free": cash,
            })
            continue
        tick = conn.fetch_ticker(venue, sym) or {}
        ask = float(tick.get("ask") or tick.get("last") or 0)
        if ask <= 0:
            results.append({"venue": venue, "symbol": sym, "skipped": True, "reason": "no_ask"})
            continue
        if venue == "binance" and sym == "BNB":
            qty = round((usd / ask) * 0.995, 3)
        elif venue == "binance":
            qty = round((usd / ask) * 0.995, 6)
        else:
            qty = round((usd / ask) * 0.99, 6)
        print(f"FILL BUY {venue} {sym} ${usd} qty={qty} ask={ask}", flush=True)
        r = vapi.place_market_order(venue, sym, "buy", qty, dry_run=False, quote=quote)
        body = r.get("body") if isinstance(r.get("body"), dict) else {}
        err = None
        if not r.get("success"):
            err = r.get("error") or (body.get("msg") if isinstance(body, dict) else None)
        results.append({
            "venue": venue,
            "symbol": sym,
            "success": bool(r.get("success")),
            "usd": usd,
            "qty": qty,
            "status": body.get("status") if isinstance(body, dict) else r.get("status"),
            "executedQty": body.get("executedQty") if isinstance(body, dict) else None,
            "cummulativeQuoteQty": body.get("cummulativeQuoteQty") if isinstance(body, dict) else None,
            "error": err,
        })
        time.sleep(1)

    refresh_balances()
    return {
        "success": True,
        "mode": f"fill_{venue}",
        "raised_quote": raised,
        "est_friction_usd": est_cost,
        "results": results,
        "quote_after": _free_quote(venue),
    }


def execute_fill_binance(
    symbols: List[str],
    *,
    fill_usd_each: float,
    raise_from_ada: bool = True,
    ignore_quote_floor: bool = True,
) -> Dict[str, Any]:
    return execute_fill_venue(
        "binance",
        symbols,
        fill_usd_each=fill_usd_each,
        raise_from_ada=raise_from_ada,
        ignore_quote_floor=ignore_quote_floor,
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Repeatable venue cycle circles with profit preview")
    p.add_argument("command", choices=["plan", "run", "daemon-tick"], help="plan | run | daemon-tick")
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="Comma-separated symbols")
    p.add_argument("--notional", type=float, default=25.0, help="Arb notional USD per leg")
    p.add_argument("--min-net-bps", type=float, default=5.0, help="Min net bps to execute arb (manual run)")
    p.add_argument("--repeat", type=int, default=1, help="Repeat run cycles")
    p.add_argument("--fill", action="store_true", help="Fill inventory gaps (costly rebalance)")
    p.add_argument(
        "--fill-venue",
        default="binance",
        choices=["binance", "nonkyc", "both"],
        help="Where --fill buys inventory",
    )
    p.add_argument("--fill-usd", type=float, default=25.0, help="USD per symbol for --fill")
    p.add_argument("--fill-target", type=float, default=40.0, help="Target inventory USD for gap display")
    p.add_argument("--yes", action="store_true", help="Actually execute (otherwise dry preview only)")
    p.add_argument("--ignore-quote-floor", action="store_true", help="Allow spending below quote floor")
    p.add_argument("--force", action="store_true", help="For daemon-tick: bypass throttle")
    p.add_argument("--json", action="store_true", help="Print machine JSON")
    args = p.parse_args(argv)

    if args.command == "daemon-tick":
        from backend.services.venue_cycle_circles_service import maybe_auto_cycle_circles

        out = maybe_auto_cycle_circles(force=bool(args.force))
        print(json.dumps(out, indent=2, default=str))
        return 0

    symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    plan = plan_circles(symbols, notional_usd=args.notional, fill_target_usd=args.fill_target)
    if args.command == "plan" or not args.yes:
        _print_plan(plan)
        if args.command == "run" and not args.yes:
            print("\nDry-run only. Pass --yes to execute after reviewing profit/cost above.")
        if args.json:
            print(json.dumps(plan, indent=2, default=str))
        return 0

    from backend.services import exchange_venue_api_service as vapi

    if not vapi.live_allowed():
        print("LIVE blocked: exchange live gate off")
        return 2

    all_out: List[Dict[str, Any]] = []
    for i in range(max(1, int(args.repeat))):
        print(f"\n=== REPEAT {i+1}/{args.repeat} ===", flush=True)
        plan = plan_circles(symbols, notional_usd=args.notional, fill_target_usd=args.fill_target)
        _print_plan(plan)

        if args.fill:
            fill_syms = [s for s in symbols if s in FILLABLE]
            gaps_bn = {g["symbol"] for g in plan.get("fill_gaps") or [] if g.get("venue") == "binance"}
            gaps_nk = {g["symbol"] for g in plan.get("fill_gaps") or [] if g.get("venue") == "nonkyc"}
            venues = (
                ["binance", "nonkyc"] if args.fill_venue == "both"
                else [args.fill_venue]
            )
            for venue in venues:
                gaps = gaps_bn if venue == "binance" else gaps_nk
                use = [s for s in fill_syms if s in gaps] or fill_syms
                if venue == "binance" and gaps_bn:
                    ordered = sorted(
                        [g for g in plan.get("fill_gaps") or [] if g.get("venue") == "binance" and g["symbol"] in use],
                        key=lambda g: float(g["gap_usd"]),
                        reverse=True,
                    )
                    use = [g["symbol"] for g in ordered] or use
                print(
                    f"FILL cost estimate ({venue}) ~$"
                    f"{round(args.fill_usd * len(use) * 15 / 10000, 4)} "
                    f"friction on ~${args.fill_usd * len(use):.0f}",
                    flush=True,
                )
                out = execute_fill_venue(
                    venue,
                    use,
                    fill_usd_each=args.fill_usd,
                    raise_from_ada=True,
                    ignore_quote_floor=True if args.ignore_quote_floor or args.fill else False,
                )
                all_out.append(out)
                print(json.dumps(out, indent=2, default=str))

        for leg in plan.get("profitable_arb") or []:
            if float(leg.get("net_bps") or 0) < float(args.min_net_bps):
                continue
            notion = min(float(args.notional), float(leg.get("max_funded_usd") or 0))
            if notion < 10:
                continue
            ask = float(leg.get("ask_buy") or 0)
            leg = {
                **leg,
                "notional_usd": round(notion, 2),
                "qty": round(notion / ask, 8) if ask > 0 else leg.get("qty"),
            }
            print(
                f"EXEC arb {leg.get('direction')} {leg.get('symbol')} "
                f"net {leg.get('net_bps')}bps est ${leg.get('est_profit_usd')} "
                f"({leg.get('leg_count')} legs)",
                flush=True,
            )
            out = execute_arb_circle(leg, ignore_quote_floor=args.ignore_quote_floor)
            all_out.append(out)
            print(json.dumps(out, indent=2, default=str))
            time.sleep(2)

        if not args.fill and not (plan.get("profitable_arb") or []):
            print("No profitable+fundable arb this repeat; inventory circles listed above for fill.", flush=True)

    final = plan_circles(symbols, notional_usd=args.notional, fill_target_usd=args.fill_target)
    print("\n=== AFTER ===")
    _print_plan(final)
    if args.json:
        print(json.dumps({"runs": all_out, "final": final}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
