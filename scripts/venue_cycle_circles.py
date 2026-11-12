#!/usr/bin/env python3
"""Repeatable Binance <-> NonKYC cycle circles with profit preview.

Circle kinds:

1) **arb** (2 legs) — buy cheap venue, sell rich venue (same coin). Profit estimated before run.
2) **inventory** (3–4 legs) — rotate quote via coin inventory, e.g. sell ADA@BN → USDC
   → (optional BSC xfer) → buy target@NK, or NK ADA → USDT → buy target@NK.
   Shows estimated friction / residual edge before run.
3) **fill** — buy missing sell-leg inventory on a venue (raise quote from excess ADA first).

Usage:
  python scripts/venue_cycle_circles.py plan
  python scripts/venue_cycle_circles.py plan --symbols BNB,LINK,XRP,ALGO,ADA,SOL,LTC,DOGE --notional 25
  python scripts/venue_cycle_circles.py run --min-net-bps 5 --repeat 2
  python scripts/venue_cycle_circles.py run --fill --fill-usd 30 --symbols BNB,XRP,LINK --yes
  python scripts/venue_cycle_circles.py run --fill --fill-venue both --fill-usd 25 --symbols BNB,XRP,LINK --yes

Safety: dry-run by default for ``run`` unless ``--yes`` is set. Respects quote floors for
auto spendable cash unless ``--ignore-quote-floor`` (manual fill / ops override).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

# Broad dual-venue set — plan skips symbols missing a ticker.
DEFAULT_SYMBOLS = [
    "BNB", "LINK", "XRP", "ALGO", "ADA", "SOL", "LTC", "DOGE", "AVAX", "TRX", "PEPE",
]
FILLABLE = {"BNB", "LINK", "XRP", "ALGO", "DOGE", "SOL", "LTC", "AVAX", "TRX"}


def _fees_bps() -> Tuple[float, float, float]:
    """Binance taker, NonKYC taker, round-trip transfer friction (bps)."""
    bn = float(os.environ.get("CYCLE_BN_TAKER_BPS", "10"))
    nk = float(os.environ.get("CYCLE_NK_TAKER_BPS", "20"))
    xfer = float(os.environ.get("CYCLE_XFER_BPS", "0"))  # USDC BSC usually ~0
    return bn, nk, xfer


def _refresh_balances() -> None:
    from backend.services import exchange_venue_api_service as vapi

    inv = getattr(vapi, "invalidate_venue_balance_cache", None)
    if callable(inv):
        inv()
    for vid in ("binance", "nonkyc"):
        vapi.parse_spot_balances(vid, dry_run=False, force_refresh=True)


def estimate_arb_leg(
    *,
    symbol: str,
    direction: str,
    notional_usd: float,
    ask_buy: float,
    bid_sell: float,
    fee_buy_bps: float,
    fee_sell_bps: float,
    xfer_bps: float = 0.0,
) -> Dict[str, Any]:
    """Estimate PnL for buy@ask_buy / sell@bid_sell on ``notional_usd``."""
    sym = str(symbol or "").upper()
    notion = max(0.0, float(notional_usd or 0))
    ask = float(ask_buy or 0)
    bid = float(bid_sell or 0)
    if ask <= 0 or bid <= 0 or notion <= 0:
        return {
            "symbol": sym,
            "direction": direction,
            "ok": False,
            "error": "bad_prices_or_notional",
            "gross_bps": 0.0,
            "net_bps": 0.0,
            "est_profit_usd": 0.0,
            "legs": [],
        }
    gross_bps = (bid - ask) / ask * 10000.0
    fee_bps = float(fee_buy_bps) + float(fee_sell_bps) + float(xfer_bps)
    net_bps = gross_bps - fee_bps
    qty = notion / ask
    buy_cost = notion * (1.0 + float(fee_buy_bps) / 10000.0)
    sell_proceeds = qty * bid * (1.0 - float(fee_sell_bps) / 10000.0)
    sell_proceeds *= 1.0 - float(xfer_bps) / 10000.0
    est = sell_proceeds - buy_cost
    buy_venue, sell_venue = ("binance", "nonkyc") if direction.startswith("binance") else ("nonkyc", "binance")
    legs = [
        {"n": 1, "action": "buy", "venue": buy_venue, "symbol": sym, "usd": round(notion, 2), "px": ask},
        {"n": 2, "action": "xfer", "note": "coin or quote hop", "xfer_bps": xfer_bps},
        {"n": 3, "action": "sell", "venue": sell_venue, "symbol": sym, "usd": round(notion, 2), "px": bid},
    ]
    return {
        "symbol": sym,
        "direction": direction,
        "ok": True,
        "notional_usd": round(notion, 2),
        "ask_buy": ask,
        "bid_sell": bid,
        "qty": round(qty, 8),
        "gross_bps": round(gross_bps, 2),
        "fee_bps": round(fee_bps, 2),
        "net_bps": round(net_bps, 2),
        "est_profit_usd": round(est, 4),
        "profitable": net_bps > 0 and est > 0,
        "legs": legs,
        "leg_count": 3,
    }


def estimate_inventory_circle(
    *,
    raise_symbol: str,
    target_symbol: str,
    venue: str,
    notional_usd: float,
    raise_bid: float,
    target_ask: float,
    fee_sell_bps: float,
    fee_buy_bps: float,
    xfer_bps: float = 0.0,
) -> Dict[str, Any]:
    """Multi-leg inventory rotate: sell raise_symbol → quote → buy target_symbol on same venue.

    Extra xfer_bps models an optional cross-venue quote hop (e.g. USDC BSC).
    """
    notion = max(0.0, float(notional_usd or 0))
    bid = float(raise_bid or 0)
    ask = float(target_ask or 0)
    if notion <= 0 or bid <= 0 or ask <= 0:
        return {
            "ok": False,
            "error": "bad_prices_or_notional",
            "est_profit_usd": 0.0,
            "net_bps": 0.0,
            "legs": [],
        }
    fee_bps = float(fee_sell_bps) + float(fee_buy_bps) + float(xfer_bps)
    # Sell raise @ bid, buy target @ ask — inventory reshape, expected edge ≈ -fees - spreads.
    raise_qty = notion / bid
    quote_after_sell = notion * (1.0 - float(fee_sell_bps) / 10000.0)
    quote_after_xfer = quote_after_sell * (1.0 - float(xfer_bps) / 10000.0)
    target_qty = (quote_after_xfer * (1.0 - float(fee_buy_bps) / 10000.0)) / ask
    # Mark target back at ask (conservative); residual vs starting notional is friction.
    marked = target_qty * ask
    est = marked - notion
    net_bps = (est / notion) * 10000.0 if notion else 0.0
    legs = [
        {"n": 1, "action": "sell", "venue": venue, "symbol": raise_symbol, "qty": round(raise_qty, 6), "px": bid},
        {"n": 2, "action": "quote", "venue": venue, "note": "USDC/USDT proceeds"},
    ]
    if xfer_bps:
        legs.append({"n": 3, "action": "xfer", "xfer_bps": xfer_bps, "note": "optional cross-venue quote hop"})
        legs.append({"n": 4, "action": "buy", "venue": venue, "symbol": target_symbol, "usd": round(quote_after_xfer, 2), "px": ask})
    else:
        legs.append({"n": 3, "action": "buy", "venue": venue, "symbol": target_symbol, "usd": round(quote_after_xfer, 2), "px": ask})
    return {
        "ok": True,
        "kind": "inventory",
        "venue": venue,
        "raise_symbol": raise_symbol,
        "target_symbol": target_symbol,
        "notional_usd": round(notion, 2),
        "fee_bps": round(fee_bps, 2),
        "net_bps": round(net_bps, 2),
        "est_profit_usd": round(est, 4),
        "profitable": est > 0,
        "legs": legs,
        "leg_count": len(legs),
    }


def plan_circles(
    symbols: List[str],
    *,
    notional_usd: float = 25.0,
    fill_target_usd: float = 35.0,
    force_refresh: bool = True,
) -> Dict[str, Any]:
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_swap_rotation_service as rot

    if force_refresh:
        _refresh_balances()

    def _quote_floor_usd(venue_id: str) -> float:
        fn = getattr(rot, "_quote_floor_usd", None)
        if callable(fn):
            return float(fn(venue_id))
        return 75.0

    def _spendable_quote_usd(venue_id: str, quote: Optional[str] = None) -> float:
        fn = getattr(rot, "_spendable_quote_usd", None)
        if callable(fn):
            return float(fn(venue_id, quote) if quote is not None else fn(venue_id))
        q = str(quote or vapi.venue_quote_asset(venue_id)).upper()
        return float(vapi.parse_spot_balances(venue_id, dry_run=False).get(q) or 0)

    def _sell_leg_floor_usd(symbol: Optional[str] = None) -> float:
        fn = getattr(rot, "_sell_leg_floor_usd", None)
        if callable(fn):
            return float(fn(symbol) if symbol is not None else fn())
        return 35.0

    bn_fee, nk_fee, xfer = _fees_bps()
    bb = vapi.parse_spot_balances("binance", dry_run=False, force_refresh=force_refresh) or {}
    nb = vapi.parse_spot_balances("nonkyc", dry_run=False, force_refresh=force_refresh) or {}
    rows: List[Dict[str, Any]] = []
    arb_actions: List[Dict[str, Any]] = []
    fill_gaps: List[Dict[str, Any]] = []
    inventory_circles: List[Dict[str, Any]] = []
    skipped: List[str] = []

    ada_bn_bid = float((conn.fetch_ticker("binance", "ADA") or {}).get("bid") or 0)
    ada_nk_bid = float((conn.fetch_ticker("nonkyc", "ADA") or {}).get("bid") or 0)

    for sym in symbols:
        sym_u = str(sym).upper()
        tb = conn.fetch_ticker("binance", sym_u) or {}
        tn = conn.fetch_ticker("nonkyc", sym_u) or {}
        ask_b = float(tb.get("ask") or 0)
        bid_b = float(tb.get("bid") or 0)
        ask_n = float(tn.get("ask") or 0)
        bid_n = float(tn.get("bid") or 0)
        if ask_b <= 0 or ask_n <= 0:
            skipped.append(sym_u)
            continue
        bn_qty = float(bb.get(sym_u) or 0)
        nk_qty = float(nb.get(sym_u) or 0)
        px = float(ex._price_usd(sym_u) or ask_b or ask_n or 0)
        bn_usd = bn_qty * (ask_b or px or 0)
        nk_usd = nk_qty * (ask_n or px or 0)

        bn_to_nk = estimate_arb_leg(
            symbol=sym_u,
            direction="binance->nonkyc",
            notional_usd=notional_usd,
            ask_buy=ask_b,
            bid_sell=bid_n,
            fee_buy_bps=bn_fee,
            fee_sell_bps=nk_fee,
            xfer_bps=xfer,
        )
        m1 = vapi.max_funded_notional_usd(
            sym_u, "binance", "nonkyc", ask_b or px or 1.0, configured_usd=max(notional_usd, 100),
        )
        bn_to_nk["max_funded_usd"] = round(m1, 2)
        bn_to_nk["fundable"] = m1 >= min(10.0, notional_usd)

        nk_to_bn = estimate_arb_leg(
            symbol=sym_u,
            direction="nonkyc->binance",
            notional_usd=notional_usd,
            ask_buy=ask_n,
            bid_sell=bid_b,
            fee_buy_bps=nk_fee,
            fee_sell_bps=bn_fee,
            xfer_bps=xfer,
        )
        m2 = vapi.max_funded_notional_usd(
            sym_u, "nonkyc", "binance", ask_n or px or 1.0, configured_usd=max(notional_usd, 100),
        )
        nk_to_bn["max_funded_usd"] = round(m2, 2)
        nk_to_bn["fundable"] = m2 >= min(10.0, notional_usd)

        target = max(float(fill_target_usd), float(_sell_leg_floor_usd(sym_u)))
        gap_bn = max(0.0, target - bn_usd)
        gap_nk = max(0.0, target - nk_usd)
        if gap_bn >= 3:
            fill_gaps.append({
                "venue": "binance", "symbol": sym_u, "gap_usd": round(gap_bn, 2),
                "have_usd": round(bn_usd, 2), "target_usd": target,
            })
        if gap_nk >= 3:
            fill_gaps.append({
                "venue": "nonkyc", "symbol": sym_u, "gap_usd": round(gap_nk, 2),
                "have_usd": round(nk_usd, 2), "target_usd": target,
            })

        # Inventory reshape circles (ADA raise → target) when target is short and ADA is long.
        if sym_u != "ADA":
            if gap_bn >= 10 and ada_bn_bid > 0 and float(bb.get("ADA") or 0) * ada_bn_bid >= 20:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA",
                    target_symbol=sym_u,
                    venue="binance",
                    notional_usd=min(notional_usd, gap_bn),
                    raise_bid=ada_bn_bid,
                    target_ask=ask_b,
                    fee_sell_bps=bn_fee,
                    fee_buy_bps=bn_fee,
                )
                inv["why"] = f"BN ADA→{sym_u} fill gap ${gap_bn:.0f}"
                inventory_circles.append(inv)
            if gap_nk >= 10 and ada_nk_bid > 0 and float(nb.get("ADA") or 0) * ada_nk_bid >= 20:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA",
                    target_symbol=sym_u,
                    venue="nonkyc",
                    notional_usd=min(notional_usd, gap_nk),
                    raise_bid=ada_nk_bid,
                    target_ask=ask_n,
                    fee_sell_bps=nk_fee,
                    fee_buy_bps=nk_fee,
                )
                inv["why"] = f"NK ADA→{sym_u} fill gap ${gap_nk:.0f}"
                inventory_circles.append(inv)
            # Cross-venue funding circle: BN ADA → USDC → BSC xfer → NK buy target
            if gap_nk >= 10 and ada_bn_bid > 0 and float(bb.get("ADA") or 0) * ada_bn_bid >= 25:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA",
                    target_symbol=sym_u,
                    venue="binance→nonkyc",
                    notional_usd=min(notional_usd, gap_nk),
                    raise_bid=ada_bn_bid,
                    target_ask=ask_n,
                    fee_sell_bps=bn_fee,
                    fee_buy_bps=nk_fee,
                    xfer_bps=max(xfer, 1.0),  # tiny model for withdraw/deposit latency risk
                )
                inv["why"] = f"BN ADA→USDC→BSC→NK {sym_u} (4-leg fund)"
                inventory_circles.append(inv)

        for leg in (bn_to_nk, nk_to_bn):
            if leg.get("profitable") and leg.get("fundable"):
                arb_actions.append(leg)

        rows.append({
            "symbol": sym_u,
            "bn_qty": bn_qty,
            "nk_qty": nk_qty,
            "bn_usd": round(bn_usd, 2),
            "nk_usd": round(nk_usd, 2),
            "binance_to_nonkyc": bn_to_nk,
            "nonkyc_to_binance": nk_to_bn,
            "leg_count": 3,
        })

    arb_actions.sort(key=lambda r: float(r.get("est_profit_usd") or 0), reverse=True)
    fill_gaps.sort(key=lambda r: float(r.get("gap_usd") or 0), reverse=True)
    inventory_circles.sort(key=lambda r: float(r.get("est_profit_usd") or 0), reverse=True)
    return {
        "success": True,
        "notional_usd": notional_usd,
        "fees_bps": {"binance_taker": bn_fee, "nonkyc_taker": nk_fee, "xfer": xfer},
        "quotes": {
            "binance_usdc": float(bb.get("USDC") or 0),
            "nonkyc_usdt": float(nb.get("USDT") or 0),
            "binance_floor": _quote_floor_usd("binance"),
            "nonkyc_floor": _quote_floor_usd("nonkyc"),
            "binance_spendable": _spendable_quote_usd("binance"),
            "nonkyc_spendable": _spendable_quote_usd("nonkyc"),
        },
        "rows": rows,
        "skipped_symbols": skipped,
        "profitable_arb": arb_actions,
        "inventory_circles": inventory_circles,
        "fill_gaps": fill_gaps,
        "est_arb_profit_usd": round(sum(float(a.get("est_profit_usd") or 0) for a in arb_actions), 4),
        "circle_count": len(rows) * 2 + len(inventory_circles),
    }


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


def execute_arb_circle(leg: Dict[str, Any], *, ignore_quote_floor: bool = False) -> Dict[str, Any]:
    """Live multi-leg arb: buy on cheap venue, sell on rich venue."""
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import exchange_swap_rotation_service as rot

    if not leg.get("profitable"):
        return {"success": False, "error": "not_profitable", "leg": leg}
    direction = str(leg.get("direction") or "")
    sym = str(leg.get("symbol") or "").upper()
    notion = float(leg.get("notional_usd") or 0)
    qty = float(leg.get("qty") or 0)
    if direction == "binance->nonkyc":
        buy_v, sell_v, buy_q = "binance", "nonkyc", "USDC"
    elif direction == "nonkyc->binance":
        buy_v, sell_v, buy_q = "nonkyc", "binance", "USDT"
    else:
        return {"success": False, "error": "bad_direction", "leg": leg}

    if not ignore_quote_floor:
        spend_fn = getattr(rot, "_spendable_quote_usd", None)
        if callable(spend_fn):
            spend = float(spend_fn(buy_v, buy_q))
        else:
            spend = float(vapi.parse_spot_balances(buy_v, dry_run=False).get(buy_q) or 0)
        if spend + 1e-9 < notion:
            notion = round(min(notion, spend), 2)
            if notion < 10:
                return {"success": False, "error": "below_quote_floor", "spendable": spend, "leg": leg}
            ask = float(leg.get("ask_buy") or 0)
            qty = round(notion / ask, 8) if ask > 0 else qty

    fund = float(leg.get("max_funded_usd") or 0)
    if fund > 0:
        notion = min(notion, fund)
        ask = float(leg.get("ask_buy") or 0)
        qty = round(notion / ask, 8) if ask > 0 else qty

    print(f"ARB L1 BUY {buy_v} {sym} qty={qty} ~${notion}", flush=True)
    buy = vapi.place_market_order(buy_v, sym, "buy", qty, dry_run=False, quote=buy_q)
    if not buy.get("success"):
        return {"success": False, "error": "buy_failed", "buy": buy, "leg": leg}
    if buy_v == "nonkyc":
        time.sleep(6)
    print(f"ARB L3 SELL {sell_v} {sym} qty={qty}", flush=True)
    sell_q = "USDT" if sell_v == "nonkyc" else "USDC"
    sell = vapi.place_market_order(sell_v, sym, "sell", qty, dry_run=False, quote=sell_q)
    _refresh_balances()
    return {
        "success": bool(sell.get("success")),
        "direction": direction,
        "symbol": sym,
        "notional_usd": notion,
        "est_profit_usd": leg.get("est_profit_usd"),
        "leg_count": leg.get("leg_count") or 3,
        "buy": {"success": buy.get("success"), "status_code": buy.get("status_code")},
        "sell": {
            "success": sell.get("success"),
            "status_code": sell.get("status_code"),
            "error": sell.get("error"),
        },
    }


def _raise_from_ada(
    venue: str,
    *,
    needed_usd: float,
    keep_usd: float = 40.0,
) -> float:
    """Sell ADA on venue to raise quote. Returns quote raised."""
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn

    _refresh_balances()
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
        # NonKYC may not echo cummulativeQuoteQty
        raised = raise_usd
    print(f"  raised {raised} status={body.get('status') or o.get('status')}", flush=True)
    _refresh_balances()
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
    """Fill inventory on binance or nonkyc (raise quote from ADA when short)."""
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

    _refresh_balances()
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
    """Back-compat wrapper → fill Binance."""
    return execute_fill_venue(
        "binance",
        symbols,
        fill_usd_each=fill_usd_each,
        raise_from_ada=raise_from_ada,
        ignore_quote_floor=ignore_quote_floor,
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Repeatable venue cycle circles with profit preview")
    p.add_argument("command", choices=["plan", "run"], help="plan=profit preview; run=execute")
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="Comma-separated symbols")
    p.add_argument("--notional", type=float, default=25.0, help="Arb notional USD per leg")
    p.add_argument("--min-net-bps", type=float, default=5.0, help="Min net bps to execute arb")
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
    p.add_argument("--json", action="store_true", help="Print machine JSON")
    args = p.parse_args(argv)

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
                # Prefer biggest BN gaps first when filling binance
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
