"""Ladder strategy upgrades for The Profit Daemon Jon (quote top-up, caps, PPP, fees)."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_market_feed_service import cached_top
from backend.services.exchange_profit_path_service import profit_path_summary
from backend.services.exchange_venue_api_service import (
    fetch_binance_symbol_filters,
    normalize_order_qty,
    parse_spot_balances,
    place_limit_order,
    place_market_order,
    venue_api_request,
    venue_has_credentials,
    _quantize_down,
)

_FEE_PATH = os.path.join(ex._DATA_DIR, "venue_fee_table.json")
_TOPUP_STATE = os.path.join(ex._DATA_DIR, "nonkyc_quote_topup_state.json")

# Conservative defaults (bps). Overwritten by refresh_venue_fees().
_DEFAULT_FEES = {
    "nonkyc": {"maker_bps": 20.0, "taker_bps": 20.0},
    "binance": {"maker_bps": 10.0, "taker_bps": 10.0},
}


def _read(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def refresh_venue_fees(*, force: bool = False) -> Dict[str, Any]:
    """Refresh per-venue maker/taker fee table (cached ~6h)."""
    raw = _read(_FEE_PATH, {})
    ts = float(raw.get("updated_at") or 0)
    if not force and raw.get("venues") and (time.time() - ts) < 6 * 3600:
        return {"success": True, "cached": True, **raw}
    venues = dict(_DEFAULT_FEES)
    # Best-effort live refresh from Binance tradeFee if credentials exist.
    try:
        if venue_has_credentials("binance"):
            res = venue_api_request("binance", "GET", "/sapi/v1/asset/tradeFee", params={"symbol": "XRPUSDC"})
            body = res.get("body")
            rows = body if isinstance(body, list) else (body.get("data") if isinstance(body, dict) else None)
            if isinstance(rows, list) and rows:
                row = rows[0] if isinstance(rows[0], dict) else {}
                maker = float(row.get("makerCommission") or row.get("maker") or 0)
                taker = float(row.get("takerCommission") or row.get("taker") or 0)
                # Binance returns fractions (0.001 = 10 bps)
                if maker < 1:
                    maker *= 10000.0
                if taker < 1:
                    taker *= 10000.0
                if maker > 0:
                    venues["binance"] = {"maker_bps": maker, "taker_bps": taker}
    except Exception as exc:
        venues.setdefault("_error", str(exc))
    payload = {"updated_at": time.time(), "venues": venues}
    _write(_FEE_PATH, payload)
    return {"success": True, "cached": False, **payload}


def apply_fee_table_to_cfg(cfg: Dict[str, Any], venue: str) -> Dict[str, Any]:
    out = dict(cfg)
    table = _read(_FEE_PATH, {}).get("venues") or _DEFAULT_FEES
    fees = table.get(venue) or _DEFAULT_FEES.get(venue) or {}
    maker = float(fees.get("maker_bps") or out.get("fee_bps") or 20.0)
    out["fee_bps"] = maker
    out["_fee_table"] = {"maker_bps": maker, "taker_bps": float(fees.get("taker_bps") or maker)}
    # Refuse unprofitable exit distance
    min_exit = max(float(out.get("min_exit_bps") or 0), 2.0 * maker + 5.0)
    if float(out.get("exit_bps") or 0) < min_exit:
        out["exit_bps"] = min_exit
    out["min_exit_bps"] = max(float(out.get("min_exit_bps") or 0), 2.0 * maker + 1.0)
    return out


def apply_dynamic_level_cap(cfg: Dict[str, Any], *, free_quote: float) -> Dict[str, Any]:
    """Shrink levels / max_open_orders only when quote inventory is critically thin."""
    out = dict(cfg)
    order = max(float(out.get("order_usd") or 1.0), 0.01)
    reserve = float(out.get("quote_reserve") or 0.0)
    usable = max(0.0, float(free_quote) - reserve)
    buy_slots = int(usable // order)
    levels = int(out.get("levels") or 1)
    sides = list(out.get("sides") or ["sell", "buy"])
    # Only shrink ladder depth when we cannot fund ~2 buy rungs (starvation risk).
    thin = "buy" in sides and usable < order * 2
    if thin and buy_slots < levels:
        out["levels"] = max(1, min(levels, max(1, buy_slots + (1 if "sell" in sides else 0))))
    max_open = int(out.get("max_open_orders") or 60)
    if thin:
        soft = max(4, buy_slots * 2 + 4)
        out["max_open_orders"] = min(max_open, soft)
    out["_dynamic_cap"] = {
        "free_quote": free_quote,
        "buy_slots": buy_slots,
        "thin": thin,
        "levels": out["levels"],
        "max_open_orders": out["max_open_orders"],
    }
    return out


def filter_symbols_by_ppp_edge(cfg: Dict[str, Any], *, min_hit_rate: float = 15.0) -> Dict[str, Any]:
    """Prefer ladder symbols that show positive PPP edge; never empty the list."""
    out = dict(cfg)
    symbols = [str(s).upper() for s in (out.get("symbols") or [])]
    if not symbols:
        return out
    summary: Any = None
    try:
        summary = profit_path_summary(hours=24)
    except Exception:
        summary = None
    # Parse best routes for symbol tokens
    good: List[str] = []
    routes = []
    if isinstance(summary, dict):
        routes = list(summary.get("best_routes_24h") or summary.get("routes_24h") or [])
    for route in routes:
        hit = float(route.get("hit_rate_pct") or 0)
        if hit < min_hit_rate:
            continue
        text = str(route.get("route") or route.get("symbol") or "").upper()
        for sym in symbols:
            if sym in text and sym not in good:
                good.append(sym)
    if good:
        # Keep original order, filtered
        out["symbols"] = [s for s in symbols if s in good] or symbols
        out["_ppp_filter"] = {"kept": out["symbols"], "from_routes": len(routes)}
    else:
        out["_ppp_filter"] = {"kept": symbols, "from_routes": len(routes), "fallback": True}
    return out


def quote_operating_target(cfg: Dict[str, Any]) -> float:
    """Free quote needed before the desk resumes normal buy entries (~3 rungs)."""
    order = max(float(cfg.get("order_usd") or 1.0), 0.01)
    return max(order * 3.0, float(cfg.get("min_order_usd") or order) * 3.0, 12.0)


def apply_exit_first_sides(cfg: Dict[str, Any], *, free_quote: float) -> Dict[str, Any]:
    """When quote is thin, stop new buy entries so sells/exits can recycle capital.

    Live learning: NonKYC filled many buy entries while exits starved (empty USDT),
    locking inventory. Sell-only mode until quote recovers to ~3 rung target.
    """
    out = dict(cfg)
    order = max(float(out.get("order_usd") or 1.0), 0.01)
    target = quote_operating_target(out)
    thin = float(free_quote) < target
    if thin and "buy" in list(out.get("sides") or []):
        # Drop buys only — do not invent sell-only mode when the cfg was buy-only.
        sides = [s for s in (out.get("sides") or []) if s != "buy"]
        out["sides"] = sides
        out["_exit_first"] = {
            "active": True,
            "free_quote": free_quote,
            "order_usd": order,
            "target_usd": target,
            "sides": out["sides"],
        }
    else:
        out["_exit_first"] = {"active": False, "free_quote": free_quote, "target_usd": target}
    return out


def top_up_venue_quote(
    venue: str = "nonkyc",
    *,
    quote: Optional[str] = None,
    min_quote_usd: float = 12.0,
    max_sells: int = 6,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Sell liquid base inventory into the venue quote asset when free quote is thin."""
    vid = str(venue or "nonkyc").lower()
    q = str(quote or ("USDC" if vid == "binance" else "USDT")).upper()
    if not venue_has_credentials(vid):
        return {"success": False, "error": "no_credentials", "venue": vid}
    bal = parse_spot_balances(vid, dry_run=False, force_refresh=True) or {}
    free_q = float(bal.get(q) or 0)
    if free_q >= min_quote_usd:
        return {"success": True, "skipped": True, "venue": vid, "quote": q, "free": free_q, "reason": "quote_ok"}
    candidates = ["ALGO", "DOGE", "XRP", "ADA", "TRX", "SOL", "XLM", "BNB", "AVAX", "LINK"]
    sells: List[Dict[str, Any]] = []
    need = max(min_quote_usd - free_q, 1.0)
    for sym in candidates:
        if len(sells) >= max_sells or need <= 0.5:
            break
        qty = float(bal.get(sym) or 0)
        if qty <= 0:
            continue
        top = cached_top(sym, max_age_sec=60.0) or {}
        bid = float(top.get("bid") or 0)
        if bid <= 0:
            continue
        target_usd = min(max(min_quote_usd, 12.0), need)
        # Use most free inventory; Binance still needs ~$5 min notional.
        sell_qty = min(qty * 0.95, target_usd / bid)
        if sell_qty * bid < 0.5:
            continue
        if vid == "binance" and sell_qty * bid < 5.0:
            sell_qty = min(qty * 0.99, max(5.05, need) / bid)
            if sell_qty * bid < 5.0:
                continue
        # Align to Binance PRICE_FILTER / LOT_SIZE — raw bid*0.997 at 8dp is rejected.
        price = float(bid)
        if vid == "binance":
            pair = f"{sym}{q}"
            filt = fetch_binance_symbol_filters(pair)
            tick = float((filt or {}).get("tick_size") or 0)
            if tick > 0:
                price = _quantize_down(bid, tick)
            norm = normalize_order_qty(
                vid, sym, "sell", sell_qty, price=price, market=pair, quote=q,
            )
            if not norm.get("ok"):
                sells.append({
                    "symbol": sym, "qty": sell_qty, "price": price,
                    "usd": round(sell_qty * price, 4), "venue": vid,
                    "result": {"success": False, "error": norm.get("error") or "qty_filter"},
                })
                continue
            sell_qty = float(norm["quantity"])
        else:
            price = round(bid * 0.997, 8)
        row = {"symbol": sym, "qty": sell_qty, "price": price, "usd": round(sell_qty * price, 4), "venue": vid}
        if dry_run:
            row["dry_run"] = True
            sells.append(row)
            need -= float(row["usd"])
            continue
        res = place_limit_order(
            vid,
            sym,
            "sell",
            sell_qty,
            price,
            quote=q,
            client_order_id=f"pdj-topup-{vid}-{sym}-{int(time.time() * 1000) % 10**10}",
        )
        # If the book moved / PRICE_FILTER still bites, market-sell to free quote now.
        if (
            vid == "binance"
            and not res.get("success")
            and "PRICE_FILTER" in str(res.get("error") or "").upper()
        ):
            mkt = place_market_order(vid, sym, "sell", sell_qty, quote=q)
            res = mkt if mkt.get("success") else res
            row["fallback"] = "market"
        row["result"] = {"success": bool(res.get("success")), "error": res.get("error")}
        sells.append(row)
        if res.get("success"):
            free_q += sell_qty * price
            need = max(min_quote_usd - free_q, 0.0)
    payload = {
        "success": True,
        "venue": vid,
        "quote": q,
        "free_before": float(bal.get(q) or 0),
        "free_est_after": free_q,
        "target_usd": min_quote_usd,
        "sells": sells,
        "updated_at": time.time(),
        "dry_run": dry_run,
    }
    _write(_TOPUP_STATE, payload)
    return payload


def top_up_nonkyc_quote(
    *,
    min_quote_usd: float = 12.0,
    max_sells: int = 6,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Back-compat wrapper — NonKYC USDT top-up."""
    return top_up_venue_quote(
        "nonkyc",
        quote="USDT",
        min_quote_usd=min_quote_usd,
        max_sells=max_sells,
        dry_run=dry_run,
    )

def enhance_ladder_cfg(cfg: Dict[str, Any], *, venue: str, balances: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Apply fee table, dynamic caps, exit-first sides, and PPP symbol filter."""
    quote = str(cfg.get("quote") or ("USDC" if venue == "binance" else "USDT"))
    free_quote = float((balances or {}).get(quote) or 0)
    out = apply_fee_table_to_cfg(cfg, venue)
    out = apply_dynamic_level_cap(out, free_quote=free_quote)
    out = apply_exit_first_sides(out, free_quote=free_quote)
    out = filter_symbols_by_ppp_edge(out)
    return out


_DESK_MAINT_STATE = os.path.join(ex._DATA_DIR, "desk_maintenance_state.json")


def run_desk_maintenance_tick(
    *,
    top_up: bool = True,
    train_fill_model: bool = True,
    fill_model_min_interval_sec: float = 3600.0,
    venues: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Scheduled NonKYC/Binance dust→quote top-up + hourly fill-model calibration.

    Owned by ``all_profit_daemons`` so desk hygiene does not depend on cron alone.
    """
    state = _read(_DESK_MAINT_STATE, {}) if isinstance(_read(_DESK_MAINT_STATE, {}), dict) else {}
    now = time.time()
    out: Dict[str, Any] = {"success": True, "ticked_at": now, "topups": [], "fill_model": None}
    if top_up:
        for vid in venues or ["nonkyc", "binance"]:
            quote = "USDC" if vid == "binance" else "USDT"
            try:
                row = top_up_venue_quote(vid, quote=quote, dry_run=False)
            except Exception as exc:
                row = {"success": False, "venue": vid, "error": str(exc)}
            out["topups"].append(row)
    last_train = float(state.get("fill_model_trained_at") or 0)
    if train_fill_model and (now - last_train) >= float(fill_model_min_interval_sec):
        try:
            from backend.services.exchange_fill_model_service import train_and_save
            model = train_and_save()
            out["fill_model"] = model
            state["fill_model_trained_at"] = now
        except Exception as exc:
            out["fill_model"] = {"success": False, "error": str(exc)}
    else:
        out["fill_model"] = {
            "skipped": True,
            "reason": "interval",
            "next_in_sec": max(0.0, float(fill_model_min_interval_sec) - (now - last_train)),
        }
    state["updated_at"] = now
    state["last"] = {
        "topup_count": len(out["topups"]),
        "fill_model": (out.get("fill_model") or {}).get("status")
        or (out.get("fill_model") or {}).get("reason")
        or (out.get("fill_model") or {}).get("error"),
    }
    _write(_DESK_MAINT_STATE, state)
    return out
