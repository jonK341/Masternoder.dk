"""Binance ↔ NonKYC cycle circles — continuous profit estimate + gated auto-execute.

Used by the profit daemon loop and ``scripts/venue_cycle_circles.py``.
Always plans/estimates; executes only when estimated edge clears configured
``cycle_circles_min_net_bps`` / ``cycle_circles_min_profit_usd`` ("big profit").
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "cycle_circles_state.json")
_LAST_PLAN_PATH = os.path.join(ex._DATA_DIR, "cycle_circles_last_plan.json")

DEFAULT_SYMBOLS = [
    "BNB", "LINK", "XRP", "ALGO", "ADA", "SOL", "LTC", "DOGE", "AVAX", "TRX", "PEPE",
]
FILLABLE = {"BNB", "LINK", "XRP", "ALGO", "DOGE", "SOL", "LTC", "AVAX", "TRX"}


def _iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_ppp() -> Dict[str, Any]:
    try:
        from backend.services.exchange_profit_path_service import load_config
        return load_config()
    except Exception:
        return {}


def cycle_circles_enabled() -> bool:
    if os.environ.get("CYCLE_CIRCLES_ENABLED", "").strip().lower() in ("0", "false", "no", "off"):
        return False
    if os.environ.get("CYCLE_CIRCLES_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    cfg = _load_ppp()
    return bool(cfg.get("cycle_circles_enabled", True))


def cycle_circles_auto_execute_enabled() -> bool:
    env = os.environ.get("CYCLE_CIRCLES_AUTO", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    cfg = _load_ppp()
    if cfg.get("cycle_circles_auto_execute") is True:
        return True
    # Fall back to rotation auto when circles auto not set explicitly
    if cfg.get("cycle_circles_auto_execute") is False:
        return False
    return bool(cfg.get("rotation_auto_execute")) or (
        os.environ.get("EXCHANGE_ROTATION_AUTO", "").strip() in ("1", "true", "yes")
    )


def _cfg_float(key: str, env_key: str, default: float) -> float:
    raw = os.environ.get(env_key)
    if raw not in (None, ""):
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    cfg = _load_ppp()
    try:
        return float(cfg.get(key, default))
    except (TypeError, ValueError):
        return default


def _cfg_int(key: str, env_key: str, default: int) -> int:
    return int(_cfg_float(key, env_key, float(default)))


def _symbols_from_config() -> List[str]:
    raw = os.environ.get("CYCLE_CIRCLES_SYMBOLS", "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    cfg = _load_ppp()
    conf = cfg.get("cycle_circles_symbols")
    if isinstance(conf, list) and conf:
        return [str(s).upper() for s in conf]
    return list(DEFAULT_SYMBOLS)


def _fees_bps() -> Tuple[float, float, float]:
    bn = float(os.environ.get("CYCLE_BN_TAKER_BPS", "10"))
    nk = float(os.environ.get("CYCLE_NK_TAKER_BPS", "20"))
    xfer = float(os.environ.get("CYCLE_XFER_BPS", "0"))
    return bn, nk, xfer


def refresh_balances() -> None:
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
            "leg_count": 0,
        }
    gross_bps = (bid - ask) / ask * 10000.0
    fee_bps = float(fee_buy_bps) + float(fee_sell_bps) + float(xfer_bps)
    net_bps = gross_bps - fee_bps
    qty = notion / ask
    buy_cost = notion * (1.0 + float(fee_buy_bps) / 10000.0)
    sell_proceeds = qty * bid * (1.0 - float(fee_sell_bps) / 10000.0)
    sell_proceeds *= 1.0 - float(xfer_bps) / 10000.0
    est = sell_proceeds - buy_cost
    buy_venue, sell_venue = (
        ("binance", "nonkyc") if direction.startswith("binance") else ("nonkyc", "binance")
    )
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
    """Multi-leg inventory rotate: sell raise_symbol → quote → buy target_symbol."""
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
            "leg_count": 0,
        }
    fee_bps = float(fee_sell_bps) + float(fee_buy_bps) + float(xfer_bps)
    raise_qty = notion / bid
    quote_after_sell = notion * (1.0 - float(fee_sell_bps) / 10000.0)
    quote_after_xfer = quote_after_sell * (1.0 - float(xfer_bps) / 10000.0)
    target_qty = (quote_after_xfer * (1.0 - float(fee_buy_bps) / 10000.0)) / ask
    marked = target_qty * ask
    est = marked - notion
    net_bps = (est / notion) * 10000.0 if notion else 0.0
    legs: List[Dict[str, Any]] = [
        {"n": 1, "action": "sell", "venue": venue, "symbol": raise_symbol, "qty": round(raise_qty, 6), "px": bid},
        {"n": 2, "action": "quote", "venue": venue, "note": "USDC/USDT proceeds"},
    ]
    if xfer_bps:
        legs.append({"n": 3, "action": "xfer", "xfer_bps": xfer_bps, "note": "optional cross-venue quote hop"})
        legs.append({
            "n": 4, "action": "buy", "venue": venue, "symbol": target_symbol,
            "usd": round(quote_after_xfer, 2), "px": ask,
        })
    else:
        legs.append({
            "n": 3, "action": "buy", "venue": venue, "symbol": target_symbol,
            "usd": round(quote_after_xfer, 2), "px": ask,
        })
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
    symbols: Optional[List[str]] = None,
    *,
    notional_usd: float = 25.0,
    fill_target_usd: float = 40.0,
    force_refresh: bool = True,
) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_swap_rotation_service as rot

    symbols = symbols or _symbols_from_config()
    if force_refresh:
        refresh_balances()

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

        if sym_u != "ADA":
            if gap_bn >= 10 and ada_bn_bid > 0 and float(bb.get("ADA") or 0) * ada_bn_bid >= 20:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA", target_symbol=sym_u, venue="binance",
                    notional_usd=min(notional_usd, gap_bn), raise_bid=ada_bn_bid, target_ask=ask_b,
                    fee_sell_bps=bn_fee, fee_buy_bps=bn_fee,
                )
                inv["why"] = f"BN ADA→{sym_u} fill gap ${gap_bn:.0f}"
                inventory_circles.append(inv)
            if gap_nk >= 10 and ada_nk_bid > 0 and float(nb.get("ADA") or 0) * ada_nk_bid >= 20:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA", target_symbol=sym_u, venue="nonkyc",
                    notional_usd=min(notional_usd, gap_nk), raise_bid=ada_nk_bid, target_ask=ask_n,
                    fee_sell_bps=nk_fee, fee_buy_bps=nk_fee,
                )
                inv["why"] = f"NK ADA→{sym_u} fill gap ${gap_nk:.0f}"
                inventory_circles.append(inv)
            if gap_nk >= 10 and ada_bn_bid > 0 and float(bb.get("ADA") or 0) * ada_bn_bid >= 25:
                inv = estimate_inventory_circle(
                    raise_symbol="ADA", target_symbol=sym_u, venue="binance→nonkyc",
                    notional_usd=min(notional_usd, gap_nk), raise_bid=ada_bn_bid, target_ask=ask_n,
                    fee_sell_bps=bn_fee, fee_buy_bps=nk_fee, xfer_bps=max(xfer, 1.0),
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
    best_net = max((float(a.get("net_bps") or 0) for a in arb_actions), default=0.0)
    return {
        "success": True,
        "planned_at": _iso(),
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
        "best_net_bps": round(best_net, 2),
        "circle_count": len(rows) * 2 + len(inventory_circles),
    }


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

    buy = vapi.place_market_order(buy_v, sym, "buy", qty, dry_run=False, quote=buy_q)
    if not buy.get("success"):
        return {"success": False, "error": "buy_failed", "buy": buy, "leg": leg}
    if buy_v == "nonkyc":
        time.sleep(6)
    sell_q = "USDT" if sell_v == "nonkyc" else "USDC"
    sell = vapi.place_market_order(sell_v, sym, "sell", qty, dry_run=False, quote=sell_q)
    refresh_balances()
    return {
        "success": bool(sell.get("success")),
        "direction": direction,
        "symbol": sym,
        "notional_usd": notion,
        "est_profit_usd": leg.get("est_profit_usd"),
        "net_bps": leg.get("net_bps"),
        "leg_count": leg.get("leg_count") or 3,
        "buy": {"success": buy.get("success"), "status_code": buy.get("status_code")},
        "sell": {
            "success": sell.get("success"),
            "status_code": sell.get("status_code"),
            "error": sell.get("error"),
        },
    }


def _load_state() -> Dict[str, Any]:
    try:
        with open(_STATE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    tmp = _STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, default=str)
    os.replace(tmp, _STATE_PATH)


def _save_last_plan(plan: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LAST_PLAN_PATH), exist_ok=True)
    slim = {
        "planned_at": plan.get("planned_at"),
        "est_arb_profit_usd": plan.get("est_arb_profit_usd"),
        "best_net_bps": plan.get("best_net_bps"),
        "circle_count": plan.get("circle_count"),
        "profitable_arb": plan.get("profitable_arb") or [],
        "quotes": plan.get("quotes"),
        "fill_gaps": (plan.get("fill_gaps") or [])[:8],
        "rows_summary": [
            {
                "symbol": r.get("symbol"),
                "bn_usd": r.get("bn_usd"),
                "nk_usd": r.get("nk_usd"),
                "bn_to_nk_net_bps": (r.get("binance_to_nonkyc") or {}).get("net_bps"),
                "nk_to_bn_net_bps": (r.get("nonkyc_to_binance") or {}).get("net_bps"),
            }
            for r in (plan.get("rows") or [])
        ],
    }
    tmp = _LAST_PLAN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(slim, fh, indent=2, default=str)
    os.replace(tmp, _LAST_PLAN_PATH)


def _leg_is_big_profit(leg: Dict[str, Any], *, min_net_bps: float, min_profit_usd: float) -> bool:
    return (
        bool(leg.get("profitable"))
        and bool(leg.get("fundable"))
        and float(leg.get("net_bps") or 0) >= float(min_net_bps)
        and float(leg.get("est_profit_usd") or 0) >= float(min_profit_usd)
    )


def maybe_auto_cycle_circles(*, force: bool = False) -> Dict[str, Any]:
    """Daemon tick: always estimate circle profit; execute only on big fundable edges."""
    if not cycle_circles_enabled():
        return {"skipped": True, "reason": "circles_disabled"}

    interval = _cfg_int("cycle_circles_interval_sec", "CYCLE_CIRCLES_INTERVAL_SEC", 60)
    state = _load_state()
    now = time.time()
    last_ts = float(state.get("last_plan_ts") or 0)
    if not force and last_ts and (now - last_ts) < max(15, interval):
        return {
            "skipped": True,
            "reason": "throttled",
            "retry_in_sec": round(max(0.0, interval - (now - last_ts)), 1),
            "last_best_net_bps": state.get("last_best_net_bps"),
            "last_est_profit_usd": state.get("last_est_arb_profit_usd"),
        }

    notional = _cfg_float("cycle_circles_notional_usd", "CYCLE_CIRCLES_NOTIONAL", 25.0)
    min_net = _cfg_float("cycle_circles_min_net_bps", "CYCLE_CIRCLES_MIN_NET_BPS", 15.0)
    min_usd = _cfg_float("cycle_circles_min_profit_usd", "CYCLE_CIRCLES_MIN_PROFIT_USD", 0.05)
    max_per = _cfg_int("cycle_circles_max_per_tick", "CYCLE_CIRCLES_MAX_PER_TICK", 2)
    max_usd = _cfg_float("cycle_circles_max_usd_per_tick", "CYCLE_CIRCLES_MAX_USD", 50.0)

    plan = plan_circles(_symbols_from_config(), notional_usd=notional, force_refresh=True)
    _save_last_plan(plan)
    state["last_plan_ts"] = now
    state["last_plan_at"] = _iso()
    state["last_best_net_bps"] = plan.get("best_net_bps")
    state["last_est_arb_profit_usd"] = plan.get("est_arb_profit_usd")
    state["last_profitable_count"] = len(plan.get("profitable_arb") or [])
    _save_state(state)

    candidates = [
        leg for leg in (plan.get("profitable_arb") or [])
        if _leg_is_big_profit(leg, min_net_bps=min_net, min_profit_usd=min_usd)
    ]
    out: Dict[str, Any] = {
        "planned": True,
        "planned_at": plan.get("planned_at"),
        "circle_count": plan.get("circle_count"),
        "best_net_bps": plan.get("best_net_bps"),
        "est_arb_profit_usd": plan.get("est_arb_profit_usd"),
        "profitable_count": len(plan.get("profitable_arb") or []),
        "big_profit_count": len(candidates),
        "min_net_bps": min_net,
        "min_profit_usd": min_usd,
        "auto_execute": cycle_circles_auto_execute_enabled(),
        "executed": [],
        "skipped_exec": None,
    }

    if not candidates:
        out["skipped_exec"] = "no_big_profit"
        return out

    if not cycle_circles_auto_execute_enabled():
        out["skipped_exec"] = "auto_disabled"
        out["top_candidate"] = {
            "symbol": candidates[0].get("symbol"),
            "direction": candidates[0].get("direction"),
            "net_bps": candidates[0].get("net_bps"),
            "est_profit_usd": candidates[0].get("est_profit_usd"),
        }
        return out

    from backend.services import exchange_venue_api_service as vapi

    if not vapi.live_allowed():
        out["skipped_exec"] = "live_gate_off"
        return out

    try:
        from backend.services.profit_daemon_ops_service import check_profit_kill
        kill = check_profit_kill(action="cycle_circles")
        if kill:
            out["skipped_exec"] = "profit_kill"
            out["kill"] = kill
            return out
    except Exception:
        pass

    executed: List[Dict[str, Any]] = []
    for leg in candidates[: max(1, max_per)]:
        notion = min(
            float(notional),
            float(leg.get("max_funded_usd") or 0),
            float(max_usd),
        )
        if notion < 10:
            continue
        ask = float(leg.get("ask_buy") or 0)
        sized = {
            **leg,
            "notional_usd": round(notion, 2),
            "qty": round(notion / ask, 8) if ask > 0 else leg.get("qty"),
        }
        # Daemon ignores quote floor only when spendable is already validated via max_funded;
        # still respect floor unless CYCLE_CIRCLES_IGNORE_FLOOR=1.
        ignore_floor = os.environ.get("CYCLE_CIRCLES_IGNORE_FLOOR", "").strip().lower() in (
            "1", "true", "yes", "on",
        )
        result = execute_arb_circle(sized, ignore_quote_floor=ignore_floor)
        executed.append(result)
        try:
            from backend.services.exchange_profit_path_service import record_event
            record_event(
                phase="cycle_circles",
                agent_id="venue_cycle_circles",
                strategy="venue_cycle_arb",
                decision="fill" if result.get("success") else "attempt",
                symbol=sized.get("symbol"),
                notional_usd=notion,
                execution={
                    "direction": sized.get("direction"),
                    "net_bps": sized.get("net_bps"),
                    "est_profit_usd": sized.get("est_profit_usd"),
                    "leg_count": sized.get("leg_count"),
                    "success": bool(result.get("success")),
                },
            )
        except Exception:
            pass
        time.sleep(1)

    state["last_exec_ts"] = time.time()
    state["last_exec_at"] = _iso()
    state["last_exec_count"] = len(executed)
    state["last_exec_success"] = sum(1 for r in executed if r.get("success"))
    _save_state(state)
    out["executed"] = executed
    out["executed_count"] = len(executed)
    return out


def last_plan_snapshot() -> Dict[str, Any]:
    try:
        with open(_LAST_PLAN_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}
