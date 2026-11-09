"""Small resting orders that book a profit on each up-and-down swing.

Runs on NonKYC (USDT quote, top-level config) and on Binance (USDC quote, the
config's ``binance`` block; Binance rejects orders under $5).
Entry rungs rest around the Binance mid: sells above it and buys below it,
``order_usd`` each, ``first_bps`` out and ``step_bps`` apart. When an entry
fills, its rung gets a paired exit on the other side ``exit_bps`` away (a
buy-back under a filled sell, a take-profit over a filled buy), so a completed
pair nets about ``exit_bps - 2 * fee_bps``. The rung only opens again after
its exit fills. Entries re-centre when the mid drifts ``recenter_bps`` from the
anchor; exits are never moved. Orders are tagged ``ld-``.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_cross_trade_service import _binance_top, _get_json, _open_order_rows
from backend.services.exchange_maker_quote_service import (
    _accepted,
    _default_cancel,
    _default_open_ids,
    _default_place,
    _order_id,
    own_sell_price,
    place_with_retry,
)
from backend.services.exchange_venue_api_service import (
    cancel_order,
    get_open_orders,
    parse_spot_balances,
    place_limit_order,
    venue_api_request,
)

TAG = "ld-"
VENUES = ("nonkyc", "binance")
QUOTES = {"nonkyc": "USDT", "binance": "USDC"}
_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_ladder_config.json")
_MARKET_URL = "https://api.nonkyc.io/api/v2/market/getbysymbol/{symbol}_USDT"
_BINANCE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo?symbol={symbol}USDC"
LOST_AFTER_SEC = 600.0

_FLOAT_KEYS = ("order_usd", "min_order_usd", "first_bps", "step_bps", "exit_bps", "fee_bps",
               "recenter_bps", "max_age_minutes", "quote_reserve")


def _default_config() -> Dict[str, Any]:
    return {
        "execute": False,
        "symbols": ["ALGO", "XRP", "DOGE", "ADA", "TRX", "SOL"],
        "sides": ["sell", "buy"],
        "order_usd": 3.5,
        "min_order_usd": 3.0,
        "levels": 6,
        "max_open_orders": 60,
        "first_bps": 30.0,
        "step_bps": 40.0,
        "exit_bps": 80.0,
        "fee_bps": 20.0,
        "recenter_bps": 150.0,
        "max_age_minutes": 360.0,
        "quote_reserve": 0.0,
    }


def load_config(venue: str = "nonkyc") -> Dict[str, Any]:
    """Top-level keys configure NonKYC; another venue overlays its own block and is off unless it says so."""
    cfg = _default_config()
    raw = ex._read_json(_CFG_PATH, None)
    raw = raw if isinstance(raw, dict) else {}
    cfg.update({k: v for k, v in raw.items() if v is not None and k not in VENUES})
    if venue != "nonkyc":
        block = raw.get(venue) if isinstance(raw.get(venue), dict) else {}
        cfg["execute"] = False
        cfg.update({k: v for k, v in block.items() if v is not None})
    cfg["venue"] = venue
    cfg["quote"] = QUOTES[venue]
    cfg["execute"] = bool(cfg.get("execute"))
    cfg["symbols"] = [str(s).upper() for s in (cfg.get("symbols") or []) if str(s).strip()]
    cfg["sides"] = [s for s in (str(x).lower() for x in (cfg.get("sides") or [])) if s in ("buy", "sell")]
    for key in _FLOAT_KEYS:
        cfg[key] = float(cfg.get(key) if cfg.get(key) is not None else _default_config()[key])
    cfg["levels"] = int(cfg.get("levels") or 0)
    cfg["max_open_orders"] = int(cfg.get("max_open_orders") or 0)
    return cfg


def state_path(path: Optional[str] = None, venue: str = "nonkyc") -> str:
    name = "ladder_state.json" if venue == "nonkyc" else f"ladder_state_{venue}.json"
    return path or os.path.join(ex._BASE, "data", "crypto_exchange", name)


def load_state(path: Optional[str] = None) -> Dict[str, Any]:
    raw = ex._read_json(state_path(path), None)
    raw = raw if isinstance(raw, dict) else {}
    return {
        "orders": dict(raw.get("orders") or {}),
        "pending": list(raw.get("pending") or []),
        "anchors": dict(raw.get("anchors") or {}),
        "realized_usd": float(raw.get("realized_usd") or 0.0),
    }


def _save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
        handle.write("\n")


def _resting(state: Dict[str, Any], symbol: str, side: str) -> List[float]:
    return [float(o["price"]) for o in state["orders"].values()
            if o["symbol"] == symbol and o["side"] == side and not o.get("cancelled")]


def lowest_own_sell(symbol: str, path: Optional[str] = None) -> Optional[float]:
    """Lowest resting ladder sell on ``symbol``, so other buyers never cross it."""
    prices = _resting(load_state(path), str(symbol).upper(), "sell")
    return min(prices) if prices else None


def _default_market(symbol: str) -> Optional[Dict[str, float]]:
    body = _get_json(_MARKET_URL.format(symbol=symbol))
    if not isinstance(body, dict) or not body.get("isActive", True):
        return None
    return {
        "price_decimals": int(body.get("priceDecimals") or 6),
        "qty_decimals": int(body.get("quantityDecimals") or 2),
        "min_qty": float(body.get("minimumQuantity") or 0),
        "min_quote": float(body.get("minQuote") or 1),
    }


def _default_closed(symbol: str, _coids: List[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for status in ("filled", "cancelled"):
        res = venue_api_request(
            "nonkyc", "open_orders", {"symbol": f"{symbol}_USDT", "status": status, "limit": 100}, dry_run=False,
        )
        for row in _open_order_rows(res.get("body")):
            uid = str(row.get("userProvidedId") or "")
            if uid.startswith(TAG):
                out.setdefault(uid, row)
    return out


def _decimals(step: str) -> int:
    text = str(step).rstrip("0")
    return len(text.split(".", 1)[1]) if "." in text else 0


def _binance_market(symbol: str) -> Optional[Dict[str, float]]:
    body = _get_json(_BINANCE_INFO_URL.format(symbol=symbol))
    try:
        row = body["symbols"][0]
    except (KeyError, IndexError, TypeError):
        return None
    if row.get("status") != "TRADING":
        return None
    f = {x["filterType"]: x for x in row.get("filters") or []}
    notional = f.get("NOTIONAL") or f.get("MIN_NOTIONAL") or {}
    return {
        "price_decimals": _decimals(f["PRICE_FILTER"]["tickSize"]),
        "qty_decimals": _decimals(f["LOT_SIZE"]["stepSize"]),
        "min_qty": float(f["LOT_SIZE"].get("minQty") or 0),
        "min_quote": float(notional.get("minNotional") or 5),
    }


def _binance_open_ids(symbol: str) -> Optional[Dict[str, str]]:
    res = get_open_orders("binance", symbol, dry_run=False, quote="USDC")
    if not res.get("success") or res.get("simulated") or not isinstance(res.get("body"), list):
        return None
    return {str(r.get("clientOrderId") or ""): str(r.get("orderId")) for r in res["body"] if r.get("clientOrderId")}


def _binance_closed(symbol: str, coids: List[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for coid in coids:
        res = venue_api_request(
            "binance", "order_status", {"symbol": f"{symbol}USDC", "origClientOrderId": coid}, dry_run=False,
        )
        body = res.get("body") if isinstance(res.get("body"), dict) else {}
        if str(body.get("status") or "") in ("FILLED", "CANCELED", "EXPIRED", "REJECTED", "EXPIRED_IN_MATCH"):
            out[coid] = {"id": body.get("orderId"), "executedQuantity": body.get("executedQty"), "status": body["status"]}
    return out


def _binance_place(symbol: str, side: str, qty: float, price: float, coid: str) -> Dict[str, Any]:
    return place_limit_order(
        "binance", symbol, side, qty, price,
        dry_run=False, quote="USDC", client_order_id=coid, time_in_force="GTC",
    )


def _binance_cancel(symbol: str, order_id: str) -> Dict[str, Any]:
    return cancel_order("binance", symbol, order_id, dry_run=False, quote="USDC")


def _venue_defaults(venue: str) -> Dict[str, Callable[..., Any]]:
    if venue == "binance":
        return {"open_ids": _binance_open_ids, "closed": _binance_closed, "market": _binance_market,
                "place": _binance_place, "cancel": _binance_cancel}
    return {"open_ids": _default_open_ids, "closed": _default_closed, "market": _default_market,
            "place": _default_place, "cancel": _default_cancel}


def round_price(price: float, side: str, decimals: int) -> float:
    """Sells round up and buys round down, so rounding never eats the margin."""
    scale = 10 ** decimals
    return (math.ceil(price * scale - 1e-9) if side == "sell" else math.floor(price * scale + 1e-9)) / scale


def floor_qty(qty: float, decimals: int) -> float:
    scale = 10 ** decimals
    return math.floor(qty * scale + 1e-9) / scale


def entry_price(ref: float, side: str, level: int, cfg: Dict[str, Any], decimals: int) -> float:
    off = (cfg["first_bps"] + level * cfg["step_bps"]) / 1e4
    return round_price(ref * (1 + off) if side == "sell" else ref * (1 - off), side, decimals)


def exit_for(order: Dict[str, Any], filled: float, cfg: Dict[str, Any], mk: Dict[str, float]) -> Dict[str, Any]:
    fee = cfg["fee_bps"] / 1e4
    entry = float(order["price"])
    if order["side"] == "sell":
        price = round_price(entry * (1 - cfg["exit_bps"] / 1e4), "buy", mk["price_decimals"])
        # Proceeds net of the entry sell's fee, leaving room for the buy-back's own fee.
        qty = floor_qty(filled * entry * (1 - fee) ** 2 / price, mk["qty_decimals"])
        side = "buy"
    else:
        price = round_price(entry * (1 + cfg["exit_bps"] / 1e4), "sell", mk["price_decimals"])
        qty = floor_qty(filled * (1 - fee), mk["qty_decimals"])
        side = "sell"
    return {"symbol": order["symbol"], "side": side, "price": price, "qty": qty, "level": order["level"],
            "entry_side": order["side"], "entry_price": entry, "entry_qty": filled}


def pair_pnl(order: Dict[str, Any], filled: float, fee_bps: float) -> float:
    """Estimated USD profit of a completed entry + exit pair.

    A buy-back's profit is the extra coins it brings back plus the quote left over after rounding.
    """
    fee = fee_bps / 1e4
    entry, price = float(order["entry_price"]), float(order["price"])
    if order["side"] == "sell":
        return filled * (price - entry) - fee * filled * (price + entry)
    sold = float(order["entry_qty"])
    leftover = sold * entry * (1 - fee) - filled * price * (1 + fee)
    return (filled - sold) * price + leftover


def _occupied(state: Dict[str, Any], symbol: str) -> set:
    taken = set()
    for o in state["orders"].values():
        if o["symbol"] == symbol and not o.get("cancelled"):
            taken.add((o["entry_side"], int(o["level"])))
    for p in state["pending"]:
        if p["symbol"] == symbol:
            taken.add((p["entry_side"], int(p["level"])))
    return taken


def _crosses(state: Dict[str, Any], symbol: str, side: str, price: float, maker_sell: Optional[float]) -> bool:
    if side == "buy":
        sells = _resting(state, symbol, "sell") + ([maker_sell] if maker_sell else [])
        sells += [float(p["price"]) for p in state["pending"] if p["symbol"] == symbol and p["side"] == "sell"]
        return bool(sells) and price >= min(sells)
    buys = _resting(state, symbol, "buy")
    buys += [float(p["price"]) for p in state["pending"] if p["symbol"] == symbol and p["side"] == "buy"]
    return bool(buys) and price <= max(buys)


def run_ladder(
    *,
    cfg: Optional[Dict[str, Any]] = None,
    top: Optional[Callable[[str], Optional[Dict[str, float]]]] = None,
    balances: Optional[Dict[str, float]] = None,
    open_ids: Optional[Callable[[str], Optional[Dict[str, str]]]] = None,
    closed: Optional[Callable[[str, List[str]], Dict[str, Dict[str, Any]]]] = None,
    market: Optional[Callable[[str], Optional[Dict[str, float]]]] = None,
    place: Optional[Callable[..., Dict[str, Any]]] = None,
    cancel: Optional[Callable[[str, str], Dict[str, Any]]] = None,
    maker_sell: Optional[Callable[[str], Optional[float]]] = None,
    clock: Optional[Callable[[], float]] = None,
    path: Optional[str] = None,
    sleep: Callable[[float], None] = time.sleep,
    venue: str = "nonkyc",
) -> Dict[str, Any]:
    cfg = cfg or load_config(venue)
    venue = cfg.get("venue") or venue
    report: Dict[str, Any] = {"venue": venue, "execute": cfg["execute"], "placed": [], "fills": [],
                              "cancelled": [], "skipped": [], "errors": []}
    if not cfg["execute"]:
        return report
    defaults = _venue_defaults(venue)
    top = top or _binance_top
    open_ids = open_ids or defaults["open_ids"]
    closed = closed or defaults["closed"]
    market = market or defaults["market"]
    place = place or defaults["place"]
    cancel = cancel or defaults["cancel"]
    if maker_sell is None:
        maker_sell = own_sell_price if venue == "nonkyc" else (lambda _s: None)
    quote = cfg.get("quote") or QUOTES[venue]
    now = (clock or time.time)()
    spath = state_path(path, venue)
    state = load_state(spath)
    orders, pending = state["orders"], state["pending"]
    if balances is None:
        balances = parse_spot_balances(venue, dry_run=False, force_refresh=True)
    bal = {str(k).upper(): float(v or 0) for k, v in (balances or {}).items()}
    bal[quote] = bal.get(quote, 0.0) - cfg["quote_reserve"]

    markets: Dict[str, Dict[str, float]] = {}
    refs: Dict[str, float] = {}
    for symbol in cfg["symbols"]:
        book, live, mk = top(symbol), open_ids(symbol), market(symbol)
        if not book or live is None or not mk:
            reason = "no_book" if not book else ("no_open_orders" if live is None else "no_market")
            report["skipped"].append({"symbol": symbol, "reason": reason})
            continue
        live = {k: v for k, v in live.items() if k.startswith(TAG)}
        markets[symbol] = mk
        missing = [c for c, o in orders.items() if o["symbol"] == symbol and c not in live]
        closed_rows = closed(symbol, missing) if missing else {}
        for coid in missing:
            row = closed_rows.get(coid)
            if row is None:
                if now - float(orders[coid].get("placed_at") or now) >= LOST_AFTER_SEC:
                    report["errors"].append({"symbol": symbol, "coid": coid, "error": "lost"})
                    orders.pop(coid)
                continue
            o = orders.pop(coid)
            filled = float(row.get("executedQuantity") or 0)
            if filled <= 0:
                continue
            fill = {"symbol": symbol, "side": o["side"], "kind": o["kind"], "level": o["level"], "coid": coid,
                    "order_id": _order_id(row), "qty": filled, "price": float(o["price"]),
                    "usd": round(filled * float(o["price"]), 4)}
            if o["kind"] == "entry":
                pending.append(exit_for(o, filled, cfg, mk))
            else:
                fill["pnl_usd"] = round(pair_pnl(o, filled, cfg["fee_bps"]), 6)
                state["realized_usd"] = round(state["realized_usd"] + fill["pnl_usd"], 6)
            report["fills"].append(fill)

        mid = (float(book["bid"]) + float(book["ask"])) / 2
        anchor = state["anchors"].get(symbol) or {}
        drift = abs(mid / float(anchor["ref"]) - 1) * 1e4 if anchor.get("ref") else None
        age_min = (now - float(anchor.get("at") or now)) / 60
        if drift is None or drift > cfg["recenter_bps"] or age_min > cfg["max_age_minutes"]:
            for coid, o in orders.items():
                if o["symbol"] != symbol or o["kind"] != "entry" or o.get("cancelled") or coid not in live:
                    continue
                res = cancel(symbol, live[coid])
                if not res.get("success"):
                    report["errors"].append({"symbol": symbol, "coid": coid, "error": str(res.get("error") or "cancel_failed")})
                    continue
                o["cancelled"] = True
                report["cancelled"].append(coid)
                if o["side"] == "sell":
                    bal[symbol] = bal.get(symbol, 0.0) + float(o["qty"])
                else:
                    bal[quote] = bal.get(quote, 0.0) + float(o["qty"]) * float(o["price"])
            state["anchors"][symbol] = {"ref": mid, "at": now}
        refs[symbol] = float(state["anchors"][symbol]["ref"])

    open_count = sum(1 for o in orders.values() if not o.get("cancelled"))

    def _try_place(spec: Dict[str, Any], kind: str) -> Optional[str]:
        nonlocal open_count
        symbol, side, price, qty = spec["symbol"], spec["side"], float(spec["price"]), float(spec["qty"])
        coid = f"{TAG}{symbol[:4]}-{side[:1]}{spec['level']}{kind[:1]}-{int(now * 1000) % 10**9}"
        res = place_with_retry(place, symbol, side, qty, price, coid, sleep=sleep)
        if not _accepted(res):
            report["errors"].append({"symbol": symbol, "side": side, "kind": kind, "price": price,
                                     "error": str(res.get("error") or "rejected")})
            return None
        orders[coid] = {**spec, "kind": kind, "price": price, "qty": qty, "placed_at": now}
        if side == "sell":
            bal[symbol] = bal.get(symbol, 0.0) - qty
        else:
            bal[quote] = bal.get(quote, 0.0) - qty * price
        open_count += 1
        report["placed"].append({"symbol": symbol, "side": side, "kind": kind, "level": spec["level"],
                                 "qty": qty, "price": price, "usd": round(qty * price, 4), "coid": coid})
        return coid

    def _fundable(symbol: str, side: str, qty: float, price: float) -> bool:
        return bal.get(symbol, 0.0) >= qty if side == "sell" else bal.get(quote, 0.0) >= qty * price

    still: List[Dict[str, Any]] = []
    for spec in pending:
        mk = markets.get(spec["symbol"])
        if not mk:
            still.append(spec)
            continue
        qty, price = float(spec["qty"]), float(spec["price"])
        if qty < mk["min_qty"] or qty * price < mk["min_quote"]:
            report["skipped"].append({"symbol": spec["symbol"], "reason": "exit_dust", "qty": qty, "price": price})
            continue
        if _crosses(state, spec["symbol"], spec["side"], price, maker_sell(spec["symbol"])):
            report["skipped"].append({"symbol": spec["symbol"], "reason": "exit_own_cross", "qty": qty, "price": price})
            still.append(spec)
            continue
        if not _fundable(spec["symbol"], spec["side"], qty, price):
            report["skipped"].append({"symbol": spec["symbol"], "reason": "exit_unfunded", "qty": qty, "price": price})
            still.append(spec)
            continue
        if _try_place(spec, "exit") is None:
            still.append(spec)
    state["pending"] = pending = still

    candidates: List[Tuple[int, int, str, str]] = []
    for pos, symbol in enumerate(cfg["symbols"]):
        if symbol not in refs:
            continue
        taken = _occupied(state, symbol)
        for side in cfg["sides"]:
            for level in range(cfg["levels"]):
                if (side, level) not in taken:
                    candidates.append((level, pos, symbol, side))
    for level, _pos, symbol, side in sorted(candidates):
        if open_count >= cfg["max_open_orders"]:
            report["skipped"].append({"reason": "max_open_orders", "limit": cfg["max_open_orders"]})
            break
        mk = markets[symbol]
        price = entry_price(refs[symbol], side, level, cfg, int(mk["price_decimals"]))
        if _crosses(state, symbol, side, price, maker_sell(symbol)):
            continue
        if side == "sell":
            qty = floor_qty(min(cfg["order_usd"] / price, bal.get(symbol, 0.0) * 0.995), int(mk["qty_decimals"]))
        else:
            qty = floor_qty(min(cfg["order_usd"], bal.get(quote, 0.0) - 0.02) / price, int(mk["qty_decimals"]))
        if qty * price < max(cfg["min_order_usd"], mk["min_quote"]) or qty < mk["min_qty"]:
            continue
        _try_place({"symbol": symbol, "side": side, "level": level, "entry_side": side, "price": price, "qty": qty},
                   "entry")

    report["open_orders"] = sum(1 for o in orders.values() if not o.get("cancelled"))
    report["pending_exits"] = len(pending)
    report["realized_usd"] = state["realized_usd"]
    _save_state(spath, state)
    return report


def format_ladder_block(report: Dict[str, Any]) -> str:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    venue = report.get("venue") or "nonkyc"
    name = "ladder" if venue == "nonkyc" else f"ladder-{venue}"
    lines = [f"{ts} {name} execute={report.get('execute')} open={report.get('open_orders')} "
             f"pending_exits={report.get('pending_exits')} realized=${report.get('realized_usd')}"]
    for f in report.get("fills") or []:
        pnl = f" pnl ${f['pnl_usd']}" if "pnl_usd" in f else ""
        lines.append(f"{name} FILL {f['symbol']} {f['kind']} {f['side']} L{f['level']} {f['qty']} @ {f['price']} (${f['usd']}){pnl}")
    for p in report.get("placed") or []:
        lines.append(f"{name} placed {p['symbol']} {p['kind']} {p['side']} L{p['level']} {p['qty']} @ {p['price']} (${p['usd']})")
    if report.get("cancelled"):
        lines.append(f"{name} recentred, cancelled {len(report['cancelled'])}")
    for e in report.get("errors") or []:
        lines.append(f"{name} error {e.get('symbol')} {e.get('side', '')} {e.get('error')}")
    for s in report.get("skipped") or []:
        if s.get("reason") in ("no_book", "no_open_orders", "no_market", "exit_dust", "exit_unfunded"):
            lines.append(f"{name} skip {s.get('symbol')} {s.get('reason')}")
    return "\n".join(lines) + "\n"


def write_ladder_log(report: Dict[str, Any], *, root: Optional[str] = None) -> str:
    base = root or os.path.join(ex._BASE, "logs", "cross_trade")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, "ladder.log")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(format_ladder_block(report))
    if report.get("fills"):
        with open(os.path.join(base, "ladder_fills.jsonl"), "a", encoding="utf-8") as handle:
            for fill in report["fills"]:
                handle.write(json.dumps({"ts": time.time(), "venue": report.get("venue") or "nonkyc", **fill}) + "\n")
    return path
