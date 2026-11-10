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
    parse_spot_balances,
    place_limit_order,
    venue_api_request,
    venue_has_credentials,
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


def top_up_nonkyc_quote(
    *,
    min_quote_usd: float = 3.0,
    max_sells: int = 3,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Sell NonKYC dust/base into USDT when free quote is below min_quote_usd."""
    if not venue_has_credentials("nonkyc"):
        return {"success": False, "error": "no_credentials"}
    bal = parse_spot_balances("nonkyc", dry_run=False, force_refresh=True) or {}
    usdt = float(bal.get("USDT") or 0)
    if usdt >= min_quote_usd:
        return {"success": True, "skipped": True, "usdt": usdt, "reason": "quote_ok"}
    # Prefer ladder symbols with free inventory
    candidates = ["ALGO", "DOGE", "XRP", "ADA", "TRX", "SOL", "XLM"]
    sells: List[Dict[str, Any]] = []
    for sym in candidates:
        if len(sells) >= max_sells:
            break
        qty = float(bal.get(sym) or 0)
        if qty <= 0:
            continue
        top = cached_top(sym, max_age_sec=60.0) or {}
        bid = float(top.get("bid") or 0)
        if bid <= 0:
            continue
        # Sell up to ~$4 notional or 40% of free qty
        target_usd = min(4.0, max(min_quote_usd - usdt, 1.0))
        sell_qty = min(qty * 0.4, target_usd / bid)
        if sell_qty * bid < 0.5:
            continue
        price = round(bid * 0.998, 8)  # slight undercut for fill
        row = {"symbol": sym, "qty": sell_qty, "price": price, "usd": round(sell_qty * price, 4)}
        if dry_run:
            row["dry_run"] = True
            sells.append(row)
            continue
        res = place_limit_order(
            "nonkyc",
            sym,
            "sell",
            sell_qty,
            price,
            quote="USDT",
            client_order_id=f"pdj-topup-{sym}-{int(time.time())}",
        )
        row["result"] = {"success": bool(res.get("success")), "error": res.get("error")}
        sells.append(row)
        if res.get("success"):
            usdt += sell_qty * price
    payload = {
        "success": True,
        "usdt_before": float(bal.get("USDT") or 0),
        "usdt_est_after": usdt,
        "sells": sells,
        "updated_at": time.time(),
        "dry_run": dry_run,
    }
    _write(_TOPUP_STATE, payload)
    return payload


def enhance_ladder_cfg(cfg: Dict[str, Any], *, venue: str, balances: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Apply fee table, dynamic caps, and PPP symbol filter."""
    quote = str(cfg.get("quote") or ("USDC" if venue == "binance" else "USDT"))
    free_quote = float((balances or {}).get(quote) or 0)
    out = apply_fee_table_to_cfg(cfg, venue)
    out = apply_dynamic_level_cap(out, free_quote=free_quote)
    out = filter_symbols_by_ppp_edge(out)
    return out
