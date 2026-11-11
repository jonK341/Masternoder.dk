"""Cancel dead / stale strategy spots that lock quote and never trade.

Strategy client ids: ``ld-`` (ladder), ``mk-`` (maker), ``arb-``, ``pdj-`` (top-up),
``grid-``. A spot is ``dead`` when its limit drifts ``min_drift_bps`` from mid
(default 25). ``cancel_all_tagged`` sweeps every tagged open regardless of drift.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_cross_trade_service import _open_order_rows
from backend.services.exchange_market_feed_service import cached_top
from backend.services.exchange_venue_api_service import (
    cancel_order,
    get_open_orders,
    invalidate_venue_balance_cache,
    parse_spot_balances,
)
from backend.services.external_exchange_connector_service import fetch_ticker

DEFAULT_TAGS = ("ld-", "mk-", "arb-", "pdj-", "grid-")
DEFAULT_SYMBOLS = (
    "XRP", "SOL", "DOGE", "TRX", "ALGO", "XLM", "ADA", "LTC",
    "BTC", "ETH", "AVAX", "LINK", "BNB", "DOT", "UNI", "SHIB",
)


def _mid(symbol: str) -> Tuple[float, str]:
    top = cached_top(symbol, max_age_sec=5.0) or {}
    try:
        bid = float(top.get("bid") or 0)
        ask = float(top.get("ask") or 0)
    except (TypeError, ValueError):
        bid = ask = 0.0
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0, "feed"
    tick = fetch_ticker("binance", symbol) or fetch_ticker("nonkyc", symbol) or {}
    try:
        bid = float(tick.get("bid") or 0)
        ask = float(tick.get("ask") or 0)
    except (TypeError, ValueError):
        bid = ask = 0.0
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0, "rest"
    try:
        return float(tick.get("last") or tick.get("price") or 0), "last"
    except (TypeError, ValueError):
        return 0.0, "none"


def _drift_bps(price: float, mid: float) -> Optional[float]:
    if price <= 0 or mid <= 0:
        return None
    return abs(price / mid - 1.0) * 1e4


def _quote_for(venue: str) -> str:
    return "USDC" if str(venue).lower() == "binance" else "USDT"


def _coid(row: Dict[str, Any]) -> str:
    return str(
        row.get("clientOrderId")
        or row.get("userProvidedId")
        or row.get("origClientOrderId")
        or ""
    )


def _oid(row: Dict[str, Any]) -> str:
    return str(row.get("orderId") or row.get("id") or row.get("_id") or "")


def list_strategy_opens(
    venue: str,
    *,
    symbols: Optional[Sequence[str]] = None,
    tags: Sequence[str] = DEFAULT_TAGS,
    quote: Optional[str] = None,
) -> List[Dict[str, Any]]:
    vid = str(venue or "").lower()
    q = str(quote or _quote_for(vid)).upper()
    rows: List[Dict[str, Any]] = []
    for symbol in [str(s).upper() for s in (symbols or DEFAULT_SYMBOLS)]:
        res = get_open_orders(vid, symbol, dry_run=False, quote=q)
        body = res.get("body")
        orders = body if isinstance(body, list) else _open_order_rows(body)
        mid, src = _mid(symbol)
        for od in orders or []:
            if not isinstance(od, dict):
                continue
            coid = _coid(od)
            if tags and coid and not any(coid.startswith(t) for t in tags):
                continue
            if tags and not coid:
                continue
            try:
                px = float(od.get("price") or 0)
            except (TypeError, ValueError):
                px = 0.0
            try:
                qty = float(
                    od.get("origQty")
                    or od.get("quantity")
                    or od.get("remainingQuantity")
                    or od.get("remainQuantity")
                    or 0
                )
            except (TypeError, ValueError):
                qty = 0.0
            drift = _drift_bps(px, mid)
            rows.append({
                "venue": vid,
                "symbol": symbol,
                "side": str(od.get("side") or "").upper(),
                "price": px,
                "qty": qty,
                "usd": round(px * qty, 4) if px and qty else 0.0,
                "mid": mid,
                "mid_src": src,
                "drift_bps": None if drift is None else round(drift, 2),
                "client_order_id": coid,
                "order_id": _oid(od),
                "dead": bool(drift is not None and drift >= 25.0),
            })
    return rows


def _reset_ladder_state(path: str) -> Dict[str, Any]:
    raw = ex._read_json(path, None)
    if not isinstance(raw, dict):
        raw = {"orders": {}, "pending": [], "anchors": {}, "realized_usd": 0.0}
    kept_realized = float(raw.get("realized_usd") or 0.0)
    clean = {
        "orders": {},
        "pending": [],
        "anchors": {},
        "realized_usd": kept_realized,
        "cleaned_at": time.time(),
    }
    ex._write_json(path, clean)
    return {"path": path, "realized_usd": kept_realized, "cleared_orders": True}


def _reset_maker_state(path: str) -> Dict[str, Any]:
    ex._write_json(path, {})
    return {"path": path, "cleared": True}


def sweep_venue_spots(
    venue: str,
    *,
    min_drift_bps: float = 25.0,
    cancel_all_tagged: bool = False,
    symbols: Optional[Sequence[str]] = None,
    tags: Sequence[str] = DEFAULT_TAGS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Cancel dead (or all tagged) strategy opens on one venue."""
    vid = str(venue or "").lower()
    q = _quote_for(vid)
    opens = list_strategy_opens(vid, symbols=symbols, tags=tags, quote=q)
    targets = [
        row for row in opens
        if cancel_all_tagged or (
            row.get("drift_bps") is not None and float(row["drift_bps"]) >= float(min_drift_bps)
        )
    ]
    cancelled: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for row in targets:
        if dry_run:
            cancelled.append({**row, "dry_run": True})
            continue
        oid = str(row.get("order_id") or "")
        if not oid:
            errors.append({**row, "error": "missing_order_id"})
            continue
        res = cancel_order(vid, str(row["symbol"]), oid, dry_run=False, quote=q)
        if res.get("success"):
            cancelled.append({
                "symbol": row["symbol"], "side": row["side"], "coid": row.get("client_order_id"),
                "oid": oid, "drift_bps": row.get("drift_bps"), "usd": row.get("usd"),
            })
        else:
            errors.append({
                "symbol": row["symbol"], "oid": oid, "coid": row.get("client_order_id"),
                "error": res.get("error") or res.get("status_code") or "cancel_failed",
            })
    invalidate_venue_balance_cache()
    bal = parse_spot_balances(vid, dry_run=False, force_refresh=True) or {}
    return {
        "success": len(errors) == 0,
        "venue": vid,
        "quote": q,
        "scanned": len(opens),
        "targeted": len(targets),
        "cancelled": len(cancelled),
        "cancelled_usd": round(sum(float(r.get("usd") or 0) for r in cancelled), 4),
        "errors": errors[:20],
        "rows": cancelled[:40],
        "free_quote": float(bal.get(q) or 0),
        "dry_run": dry_run,
        "cancel_all_tagged": cancel_all_tagged,
        "min_drift_bps": min_drift_bps,
    }


def sweep_dead_spots(
    venues: Optional[Iterable[str]] = None,
    *,
    min_drift_bps: float = 25.0,
    cancel_all_tagged: bool = False,
    reset_state: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Sweep Binance + NonKYC strategy spots and optionally wipe local ladder/maker state."""
    vids = [str(v).lower() for v in (venues or ("binance", "nonkyc"))]
    report: Dict[str, Any] = {
        "success": True,
        "ticked_at": time.time(),
        "venues": {},
        "state_resets": [],
    }
    for vid in vids:
        row = sweep_venue_spots(
            vid,
            min_drift_bps=min_drift_bps,
            cancel_all_tagged=cancel_all_tagged,
            dry_run=dry_run,
        )
        report["venues"][vid] = row
        if not row.get("success"):
            report["success"] = False
    if reset_state and not dry_run:
        data = ex._DATA_DIR
        for name in ("ladder_state_binance.json", "ladder_state.json"):
            path = os.path.join(data, name)
            if os.path.isfile(path):
                report["state_resets"].append(_reset_ladder_state(path))
        maker_path = os.path.join(data, "maker_quote_state.json")
        if os.path.isfile(maker_path):
            report["state_resets"].append(_reset_maker_state(maker_path))
        # NonKYC ladder may live under ladder_state.json already; also clear empty sidecar.
        nk = os.path.join(data, "ladder_state_nonkyc.json")
        if os.path.isfile(nk):
            report["state_resets"].append(_reset_ladder_state(nk))
    report["cancelled_total"] = sum(
        int((report["venues"].get(v) or {}).get("cancelled") or 0) for v in vids
    )
    report["cancelled_usd_total"] = round(
        sum(float((report["venues"].get(v) or {}).get("cancelled_usd") or 0) for v in vids), 4
    )
    return report
