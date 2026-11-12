"""Search both venues and append one ledger line per exchange.

A ledger line is the order that would be sent. It records the endpoint and body.
It does not post that body to the matching engine. A separate channel probe only
reads open orders, plus Binance's order-test endpoint, which validates and does
not match.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_venue_api_service as vapi

_LEDGER_DIR = os.path.join(ex._DATA_DIR, "ledgers")
_VENUES = ("binance", "nonkyc")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ledger_path(venue_id: str) -> str:
    return os.path.join(_LEDGER_DIR, f"{str(venue_id).lower()}.jsonl")


def read_ledger(venue_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
    path = ledger_path(venue_id)
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows[-max(1, limit):]


def _append(venue_id: str, row: Dict[str, Any]) -> None:
    os.makedirs(_LEDGER_DIR, exist_ok=True)
    ex._append_jsonl(ledger_path(venue_id), row)


def _short_error(res: Dict[str, Any]) -> str:
    body = res.get("body")
    if isinstance(body, dict):
        msg = body.get("msg") or body.get("message") or body.get("error")
        if msg:
            return str(msg)[:180]
    if isinstance(body, str) and body.strip():
        return body.strip()[:180]
    return str(res.get("error") or res.get("status_code") or "")[:180]


def order_spec(venue_id: str, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
    """The body place_market_order would sign. No signature, no network."""
    venue = str(venue_id).lower()
    base = str(symbol).upper()
    side_l = str(side).lower()
    resolved = vapi.resolve_market(venue, base)
    pair = str(resolved.get("market") or "")
    qty = round(max(0.0, float(quantity or 0)), 8)
    if venue == "binance":
        return {
            "venue": venue,
            "endpoint": "POST /api/v3/order",
            "test_endpoint": "POST /api/v3/order/test",
            "market": pair,
            "quote": resolved.get("quote"),
            "body": {"symbol": pair, "side": side_l.upper(), "type": "MARKET", "quantity": qty},
        }
    return {
        "venue": venue,
        "endpoint": "POST /api/v2/createorder",
        "test_endpoint": None,
        "market": pair,
        "quote": resolved.get("quote"),
        "body": {
            "symbol": pair,
            "side": side_l,
            "type": "market",
            "quantity": str(qty),
            "strictValidate": False,
        },
    }


def _legs(row: Dict[str, Any]) -> List[Dict[str, str]]:
    route = str(row.get("route") or "")
    if route.startswith("nonkyc"):
        return [
            {"venue": "nonkyc", "side": "buy"},
            {"venue": "binance", "side": "sell"},
        ]
    return [
        {"venue": "binance", "side": "buy"},
        {"venue": "nonkyc", "side": "sell"},
    ]


def _quantity(row: Dict[str, Any], *, notional_usd: float) -> float:
    ask = float(row.get("buy_ask") or 0)
    if ask <= 0:
        return 0.0
    tradable = float(row.get("executable_usd") or 0)
    clip = tradable if tradable > 0 else notional_usd
    return round(clip / ask, 8)


def probe_order_channel(venue_id: str) -> Dict[str, Any]:
    """Read open orders. This proves the signed key without placing anything."""
    venue = str(venue_id).lower()
    res = vapi.get_open_orders(venue, "XRP", dry_run=False)
    return {
        "check": "open_orders",
        "ok": bool(res.get("success")) and not res.get("simulated"),
        "status_code": res.get("status_code"),
        "detail": _short_error(res) or ("open orders readable" if res.get("success") else "unreadable"),
    }


def probe_binance_test_order(symbol: str, side: str, quantity: float) -> Dict[str, Any]:
    """POST /api/v3/order/test. Binance validates the order and does not match it."""
    spec = order_spec("binance", symbol, side, quantity)
    res = vapi.venue_api_request("binance", "order_test", dict(spec["body"]), dry_run=False)
    accepted = bool(res.get("success")) and not res.get("simulated")
    return {
        "check": "order_test",
        "ok": accepted,
        "status_code": res.get("status_code"),
        "detail": _short_error(res) or ("test order accepted" if accepted else "test order refused"),
        "body": spec["body"],
    }


def rows_from_scan(
    scan: Dict[str, Any],
    *,
    notional_usd: float = 25.0,
    channels: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Turn a preview_fast_usdt result into one ledger row per venue per coin."""
    now = _iso()
    channels = channels or {}
    out: List[Dict[str, Any]] = []
    for coin in scan.get("coins") or []:
        if not isinstance(coin, dict):
            continue
        symbol = str(coin.get("symbol") or "").upper()
        decision = str(coin.get("decision") or "")
        qty = _quantity(coin, notional_usd=notional_usd)
        send = decision == "paper_candidate" and qty > 0
        for leg in _legs(coin):
            spec = order_spec(leg["venue"], symbol, leg["side"], qty)
            channel = channels.get(leg["venue"]) or {}
            out.append({
                "ts": now,
                "venue": leg["venue"],
                "symbol": symbol,
                "side": leg["side"],
                "decision": decision,
                "net_bps": coin.get("net_bps"),
                "executable_usd": coin.get("executable_usd"),
                "route": coin.get("route"),
                "quantity": qty,
                "market": spec["market"],
                "quote": spec["quote"],
                "endpoint": spec["endpoint"],
                "order_body": spec["body"],
                "placed": False,
                "reason": "book_ready" if send else decision or "no_book",
                "channel_ok": channel.get("ok"),
                "channel_detail": channel.get("detail"),
            })
    return out


def write_rows(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {venue: 0 for venue in _VENUES}
    for row in rows:
        venue = str(row.get("venue") or "")
        if venue not in counts:
            continue
        _append(venue, row)
        counts[venue] += 1
    return counts


def run_search(*, probe: bool = True, notional_usd: float = 25.0,
               scan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Search the fast USDT books and append a ledger line on each exchange."""
    if scan is None:
        from backend.services.exchange_cross_trade_service import preview_fast_usdt
        scan = preview_fast_usdt(notional_usd=notional_usd, min_net_bps=18.0)
    channels: Dict[str, Dict[str, Any]] = {}
    test_order: Optional[Dict[str, Any]] = None
    if probe:
        for venue in _VENUES:
            try:
                channels[venue] = probe_order_channel(venue)
            except Exception as exc:
                channels[venue] = {"check": "open_orders", "ok": False, "detail": str(exc)[:180]}
        xrp = next((c for c in scan.get("coins") or [] if c.get("symbol") == "XRP"), None)
        qty = _quantity(xrp, notional_usd=notional_usd) if isinstance(xrp, dict) else 0.0
        if qty <= 0 and isinstance(xrp, dict) and float(xrp.get("buy_ask") or 0) > 0:
            qty = round(notional_usd / float(xrp["buy_ask"]), 8)
        if qty > 0:
            try:
                test_order = probe_binance_test_order("XRP", "buy", qty)
            except Exception as exc:
                test_order = {"check": "order_test", "ok": False, "detail": str(exc)[:180]}
            if "binance" in channels and test_order:
                channels["binance"] = {
                    **channels["binance"],
                    "order_test_ok": test_order.get("ok"),
                    "order_test_detail": test_order.get("detail"),
                }
    rows = rows_from_scan(scan, notional_usd=notional_usd, channels=channels)
    counts = write_rows(rows)
    return {
        "success": bool(scan.get("success")),
        "tradable_count": scan.get("tradable_count"),
        "written": counts,
        "channels": channels,
        "binance_order_test": test_order,
        "rows": rows,
        "placed": False,
    }


def ledger_snapshot(*, limit: int = 8) -> Dict[str, Any]:
    return {
        "binance": read_ledger("binance", limit=limit),
        "nonkyc": read_ledger("nonkyc", limit=limit),
    }
