"""Resting NonKYC quotes priced off the Binance book.

Each tick places (or re-prices) one resting limit per enabled symbol and side:
a sell at Binance ask + fees + edge, or a buy at Binance bid - fees - edge.
A fill therefore already carries the edge against the Binance price. Orders
are tagged ``mk-`` so the arb pass's ``arb-`` cleanup leaves them alone.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_cross_trade_service import _binance_top, _open_order_rows
from backend.services.exchange_venue_api_service import (
    cancel_order,
    get_open_orders,
    parse_spot_balances,
    place_limit_order,
    venue_api_request,
)

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_maker_config.json")
MIN_ORDER_USD = 5.0


def _default_config() -> Dict[str, Any]:
    return {
        "execute": False,
        "symbols": ["ALGO", "XRP"],
        "sides": ["sell"],
        "clip_usd": 25.0,
        "fee_bps": 30.0,
        "edge_bps": 18.0,
        "reprice_bps": 5.0,
        "max_age_minutes": 30.0,
    }


def load_config() -> Dict[str, Any]:
    cfg = _default_config()
    raw = ex._read_json(_CFG_PATH, None)
    if isinstance(raw, dict):
        cfg.update({k: v for k, v in raw.items() if v is not None})
    cfg["execute"] = bool(cfg.get("execute"))
    cfg["symbols"] = [str(s).upper() for s in (cfg.get("symbols") or []) if str(s).strip()]
    cfg["sides"] = [s for s in (str(x).lower() for x in (cfg.get("sides") or [])) if s in ("buy", "sell")]
    for key in ("clip_usd", "fee_bps", "edge_bps", "reprice_bps", "max_age_minutes"):
        cfg[key] = float(cfg.get(key) or _default_config()[key])
    return cfg


def state_path(path: Optional[str] = None) -> str:
    return path or os.path.join(ex._BASE, "data", "crypto_exchange", "maker_quote_state.json")


def load_state(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    raw = ex._read_json(state_path(path), None)
    return raw if isinstance(raw, dict) else {}


def _save_state(path: str, state: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
        handle.write("\n")


def own_sell_price(symbol: str, path: Optional[str] = None) -> Optional[float]:
    """Price of our resting NonKYC sell on ``symbol``, if any (to avoid buying into it)."""
    row = load_state(path).get(f"{str(symbol).upper()}:sell") or {}
    try:
        return float(row["price"]) if row.get("coid") else None
    except (KeyError, TypeError, ValueError):
        return None


def price_decimals(price: float) -> int:
    return 4 if price >= 1 else 6


def quote_price(ref: float, side: str, cfg: Dict[str, Any]) -> float:
    """Sell rounds up and buy rounds down, so rounding never eats the edge."""
    margin = (float(cfg["fee_bps"]) + float(cfg["edge_bps"])) / 1e4
    raw = ref * (1 + margin) if side == "sell" else ref * (1 - margin)
    scale = 10 ** price_decimals(ref)
    return (math.ceil(raw * scale) if side == "sell" else math.floor(raw * scale)) / scale


def _order_id(row: Dict[str, Any]) -> str:
    return str(row.get("id") or row.get("_id") or row.get("orderId") or "")


def _default_status(symbol: str, coid: str) -> Dict[str, Any]:
    # NonKYC's create response id differs from its listing id, so orders are matched on userProvidedId.
    for status in ("filled", "cancelled"):
        res = venue_api_request(
            "nonkyc", "open_orders", {"symbol": f"{symbol}_USDT", "status": status, "limit": 50}, dry_run=False,
        )
        for row in _open_order_rows(res.get("body")):
            if str(row.get("userProvidedId") or "") == coid:
                return row
    return {}


def _default_open_ids(symbol: str) -> Optional[Dict[str, str]]:
    res = get_open_orders("nonkyc", symbol, dry_run=False, quote="USDT")
    if not res.get("success") or res.get("simulated"):
        return None
    return {
        str(row.get("userProvidedId") or ""): _order_id(row)
        for row in _open_order_rows(res.get("body"))
        if row.get("userProvidedId")
    }


def _default_place(symbol: str, side: str, qty: float, price: float, coid: str) -> Dict[str, Any]:
    return place_limit_order(
        "nonkyc", symbol, side, qty, price,
        dry_run=False, quote="USDT", client_order_id=coid, time_in_force="GTC",
    )


def _default_cancel(symbol: str, order_id: str) -> Dict[str, Any]:
    return cancel_order("nonkyc", symbol, order_id, dry_run=False, quote="USDT")


def _accepted(res: Dict[str, Any]) -> bool:
    return bool(res.get("success")) and not res.get("simulated") and str(res.get("mode") or "").lower() != "paper"


def run_maker_quotes(
    *,
    cfg: Optional[Dict[str, Any]] = None,
    top: Optional[Callable[[str], Optional[Dict[str, float]]]] = None,
    balances: Optional[Dict[str, float]] = None,
    open_ids: Optional[Callable[[str], Optional[Dict[str, str]]]] = None,
    status: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    place: Optional[Callable[..., Dict[str, Any]]] = None,
    cancel: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    clock: Optional[Callable[[], float]] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = cfg or load_config()
    report: Dict[str, Any] = {"execute": cfg["execute"], "quotes": [], "fills": []}
    if not cfg["execute"]:
        return report
    top = top or _binance_top
    open_ids = open_ids or _default_open_ids
    status = status or _default_status
    place = place or _default_place
    cancel = cancel or _default_cancel
    now = (clock or time.time)()
    spath = state_path(path)
    state = load_state(spath)
    if balances is None:
        balances = parse_spot_balances("nonkyc", dry_run=False, force_refresh=True)
    bal = {str(k).upper(): float(v or 0) for k, v in (balances or {}).items()}

    for symbol in cfg["symbols"]:
        book = top(symbol)
        live_ids = open_ids(symbol)
        for side in cfg["sides"]:
            key = f"{symbol}:{side}"
            row = state.get(key) or {}
            item: Dict[str, Any] = {"symbol": symbol, "side": side}
            report["quotes"].append(item)
            if not book or live_ids is None:
                item["skipped"] = "no_book" if not book else "no_open_orders"
                continue
            ref = float(book["ask"] if side == "sell" else book["bid"])
            target = quote_price(ref, side, cfg)
            item.update({"ref": ref, "target": target})
            coid = str(row.get("coid") or "")
            if coid and coid not in live_ids:
                st = status(symbol, coid)
                filled = float(st.get("executedQuantity") or 0)
                if filled > 0:
                    fill = {
                        "symbol": symbol, "side": side, "coid": coid, "order_id": _order_id(st), "qty": filled,
                        "price": float(row.get("price") or 0), "ref": float(row.get("ref") or 0),
                        "edge_bps": cfg["edge_bps"], "status": st.get("status"),
                    }
                    fill["usd"] = round(fill["qty"] * fill["price"], 4)
                    report["fills"].append(fill)
                state.pop(key, None)
                row, coid = {}, ""
            if coid:
                moved = abs(target - float(row.get("price") or 0)) / target * 1e4
                age_min = (now - float(row.get("placed_at") or now)) / 60
                if moved < cfg["reprice_bps"] and age_min < cfg["max_age_minutes"]:
                    item.update({"resting": coid, "price": row.get("price")})
                    continue
                res = cancel(symbol, live_ids[coid])
                item["cancelled"] = coid
                if not res.get("success"):
                    item["error"] = str(res.get("error") or "cancel_failed")
                    continue
                state.pop(key, None)
                if side == "sell":
                    bal[symbol] = bal.get(symbol, 0.0) + float(row.get("qty") or 0)
                else:
                    bal["USDT"] = bal.get("USDT", 0.0) + float(row.get("qty") or 0) * float(row.get("price") or 0)
            if side == "sell":
                qty = min(cfg["clip_usd"] / target, bal.get(symbol, 0.0) * 0.99)
            else:
                qty = min(cfg["clip_usd"], bal.get("USDT", 0.0) - 0.05) / target
            qty = math.floor(qty * 100) / 100
            if qty * target < MIN_ORDER_USD:
                item["skipped"] = "inventory" if side == "sell" else "budget"
                continue
            coid = f"mk-{symbol[:4]}-{side[:1]}-{int(now * 1000) % 10**10}"
            res = place(symbol, side, qty, target, coid)
            item.update({"qty": qty, "price": target, "success": _accepted(res), "coid": coid})
            if not _accepted(res):
                item["error"] = str(res.get("error") or "")
                continue
            state[key] = {"coid": coid, "price": target, "qty": qty, "ref": ref, "placed_at": now}
            if side == "sell":
                bal[symbol] = bal.get(symbol, 0.0) - qty
            else:
                bal["USDT"] = bal.get("USDT", 0.0) - qty * target
    _save_state(spath, state)
    return report


def format_maker_block(report: Dict[str, Any]) -> str:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines = [f"{ts} maker execute={report.get('execute')}"]
    for q in report.get("quotes") or []:
        state = q.get("skipped") or ("resting " + str(q.get("resting")) if q.get("resting") else
                                     ("placed " + str(q.get("coid")) if q.get("success") else "error " + str(q.get("error"))))
        lines.append(f"maker {q.get('symbol')} {q.get('side')} ref {q.get('ref')} target {q.get('target')} {state}")
    for f in report.get("fills") or []:
        lines.append(f"maker FILL {f['symbol']} {f['side']} {f['qty']} @ {f['price']} (${f['usd']}) ref {f['ref']}")
    return "\n".join(lines) + "\n"


def write_maker_log(report: Dict[str, Any], *, root: Optional[str] = None) -> str:
    base = root or os.path.join(ex._BASE, "logs", "cross_trade")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, "maker.log")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(format_maker_block(report))
    if report.get("fills"):
        with open(os.path.join(base, "maker_fills.jsonl"), "a", encoding="utf-8") as handle:
            for fill in report["fills"]:
                handle.write(json.dumps({"ts": time.time(), **fill}) + "\n")
    return path
