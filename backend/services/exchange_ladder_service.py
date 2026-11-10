"""Small resting orders that book a profit on each up-and-down swing.

Runs on NonKYC (USDT quote, top-level config) and on Binance (USDC quote, the
config's ``binance`` block; Binance rejects orders under $5).
Entry rungs rest around the Binance mid: sells above it and buys below it,
``order_usd`` each, ``first_bps`` out and ``step_bps`` apart. When an entry
fills, its rung gets a paired exit on the other side ``exit_bps`` away (a
buy-back under a filled sell, a take-profit over a filled buy), so a completed
pair nets about ``exit_bps - 2 * fee_bps``. The rung only opens again after
its exit fills. Entries are refreshed to the current mid every ``refresh_minutes``
or when it drifts ``recenter_bps``; a rung is only replaced when its price moves
``reprice_bps``. Unfilled exits step toward the market over ``exit_decay_minutes``,
down to ``min_exit_bps`` from their entry, so each pair stays profitable.
Orders are tagged ``ld-``.
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
from backend.services.exchange_fill_model_service import tune_ladder_cfg
from backend.services.exchange_inventory_skew import skewed_entry_offset_bps, skew_factor
from backend.services.exchange_ladder_strategy_improve import (
    enhance_ladder_cfg,
    refresh_venue_fees,
    top_up_nonkyc_quote,
)
from backend.services.exchange_market_feed_service import prefer_cached_binance_top
from backend.services.exchange_metrics_service import observe_ladder
from backend.services.exchange_maker_quote_service import (
    _accepted,
    _default_cancel,
    _default_open_ids,
    _default_place,
    _order_id,
    own_sell_price,
    place_with_retry,
)
from backend.services.exchange_registry_service import ladder_quotes, ladder_venues
from backend.services.exchange_venue_api_service import (
    cancel_order,
    get_open_orders,
    parse_spot_balances,
    place_limit_order,
    venue_api_request,
)

TAG = "ld-"
VENUES = ladder_venues()
QUOTES = ladder_quotes()
_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_ladder_config.json")
_MARKET_URL = "https://api.nonkyc.io/api/v2/market/getbysymbol/{symbol}_USDT"
_BINANCE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo?symbol={symbol}USDC"
LOST_AFTER_SEC = 600.0

_FLOAT_KEYS = ("order_usd", "min_order_usd", "first_bps", "step_bps", "exit_bps", "fee_bps",
               "recenter_bps", "refresh_minutes", "reprice_bps", "min_exit_bps", "exit_decay_minutes",
               "quote_reserve", "inventory_skew_bps", "fill_model_min_prob")


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
        "recenter_bps": 30.0,
        "refresh_minutes": 10.0,
        "reprice_bps": 5.0,
        "min_exit_bps": 55.0,
        "exit_decay_minutes": 120.0,
        "quote_reserve": 0.0,
        "inventory_skew_bps": 25.0,
        "fill_model_enabled": True,
        "fill_model_min_prob": 0.18,
    }


def load_config(venue: str = "nonkyc") -> Dict[str, Any]:
    """Top-level keys configure NonKYC; another venue overlays its own block and is off unless it says so."""
    cfg = _default_config()
    raw = ex._read_json(_CFG_PATH, None)
    raw = raw if isinstance(raw, dict) else {}
    venue_ids = set(ladder_venues()) | set(VENUES)
    cfg.update({k: v for k, v in raw.items() if v is not None and k not in venue_ids})
    if venue != "nonkyc":
        block = raw.get(venue) if isinstance(raw.get(venue), dict) else {}
        cfg["execute"] = False
        cfg.update({k: v for k, v in block.items() if v is not None})
    cfg["venue"] = venue
    quotes = {**QUOTES, **ladder_quotes()}
    cfg["quote"] = quotes.get(venue) or ("USDC" if venue == "binance" else "USDT")
    cfg["execute"] = bool(cfg.get("execute"))
    cfg["symbols"] = [str(s).upper() for s in (cfg.get("symbols") or []) if str(s).strip()]
    cfg["sides"] = [s for s in (str(x).lower() for x in (cfg.get("sides") or [])) if s in ("buy", "sell")]
    for key in _FLOAT_KEYS:
        cfg[key] = float(cfg.get(key) if cfg.get(key) is not None else _default_config()[key])
    cfg["levels"] = int(cfg.get("levels") or 0)
    cfg["max_open_orders"] = int(cfg.get("max_open_orders") or 0)
    cfg["fill_model_enabled"] = bool(cfg.get("fill_model_enabled", True))
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
    skew = float(cfg.get("_inventory_skew") or 0.0)
    off = skewed_entry_offset_bps(side, level, cfg, skew=skew) / 1e4
    return round_price(ref * (1 + off) if side == "sell" else ref * (1 - off), side, decimals)


def exit_bps_at(cfg: Dict[str, Any], age_sec: float) -> float:
    """Exit distance shrinks linearly from ``exit_bps`` to ``min_exit_bps`` over ``exit_decay_minutes``."""
    far, near = cfg["exit_bps"], min(cfg["min_exit_bps"], cfg["exit_bps"])
    decay = cfg["exit_decay_minutes"] * 60
    frac = min(1.0, max(0.0, age_sec) / decay) if decay > 0 else 1.0
    return far - (far - near) * frac


def exit_spec(entry_side: str, entry: float, filled: float, bps: float,
              cfg: Dict[str, Any], mk: Dict[str, float]) -> Dict[str, Any]:
    fee = cfg["fee_bps"] / 1e4
    if entry_side == "sell":
        price = round_price(entry * (1 - bps / 1e4), "buy", mk["price_decimals"])
        # Proceeds net of the entry sell's fee, leaving room for the buy-back's own fee.
        qty = floor_qty(filled * entry * (1 - fee) ** 2 / price, mk["qty_decimals"])
        return {"side": "buy", "price": price, "qty": qty}
    price = round_price(entry * (1 + bps / 1e4), "sell", mk["price_decimals"])
    return {"side": "sell", "price": price, "qty": floor_qty(filled * (1 - fee), mk["qty_decimals"])}


def exit_for(order: Dict[str, Any], filled: float, cfg: Dict[str, Any], mk: Dict[str, float]) -> Dict[str, Any]:
    entry = float(order["price"])
    return {"symbol": order["symbol"], "level": order["level"], "entry_side": order["side"],
            "entry_price": entry, "entry_qty": filled,
            **exit_spec(order["side"], entry, filled, cfg["exit_bps"], cfg, mk)}


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
                              "cancelled": [], "repriced": [], "kept": 0, "skipped": [], "errors": []}
    if not cfg["execute"]:
        return report
    defaults = _venue_defaults(venue)
    if top is None:
        top = lambda symbol: prefer_cached_binance_top(symbol, _binance_top)
    open_ids = open_ids or defaults["open_ids"]
    closed = closed or defaults["closed"]
    market = market or defaults["market"]
    place = place or defaults["place"]
    cancel = cancel or defaults["cancel"]
    if maker_sell is None:
        maker_sell = own_sell_price if venue == "nonkyc" else (lambda _s: None)
    quote = cfg.get("quote") or QUOTES.get(venue) or ladder_quotes().get(venue) or "USDT"
    now = (clock or time.time)()
    spath = state_path(path, venue)
    state = load_state(spath)
    orders, pending = state["orders"], state["pending"]
    if balances is None:
        balances = parse_spot_balances(venue, dry_run=False, force_refresh=True)
    bal = {str(k).upper(): float(v or 0) for k, v in (balances or {}).items()}
    # quote_reserve is for new entries only — exits must spend the reserved quote.
    reserve = float(cfg.get("quote_reserve") or 0.0)
    injected_balances = balances is not None
    try:
        # Network top-up / fee refresh only on the live balance path (not unit tests).
        if not injected_balances:
            refresh_venue_fees()
            if venue == "nonkyc" and cfg.get("execute"):
                report["quote_topup"] = top_up_nonkyc_quote(
                    min_quote_usd=max(float(cfg.get("min_order_usd") or 3.0), 3.0),
                    dry_run=False,
                )
                if not (report["quote_topup"] or {}).get("skipped"):
                    try:
                        balances = parse_spot_balances(venue, dry_run=False, force_refresh=True)
                        bal = {str(k).upper(): float(v or 0) for k, v in (balances or {}).items()}
                    except Exception:
                        pass
        cfg = enhance_ladder_cfg(cfg, venue=venue, balances=bal)
        reserve = float(cfg.get("quote_reserve") or 0.0)
    except Exception as exc:
        report["strategy_improve_error"] = str(exc)
    cfg = tune_ladder_cfg(cfg, venue=venue, min_prob=float(cfg.get("fill_model_min_prob") or 0.18))
    report["_fill_prob_l0"] = cfg.get("_fill_prob_l0")
    report["_dynamic_cap"] = cfg.get("_dynamic_cap")
    report["_ppp_filter"] = cfg.get("_ppp_filter")
    skews: Dict[str, float] = {}

    markets: Dict[str, Dict[str, float]] = {}
    refs: Dict[str, float] = {}
    lives: Dict[str, Dict[str, Any]] = {}
    for symbol in cfg["symbols"]:
        book, live, mk = top(symbol), open_ids(symbol), market(symbol)
        if not book or live is None or not mk:
            reason = "no_book" if not book else ("no_open_orders" if live is None else "no_market")
            report["skipped"].append({"symbol": symbol, "reason": reason})
            continue
        live = {k: v for k, v in live.items() if k.startswith(TAG)}
        lives[symbol] = live
        markets[symbol] = mk
        missing = [c for c, o in orders.items() if o["symbol"] == symbol and c not in live]
        closed_rows = closed(symbol, missing) if missing else {}
        for coid in missing:
            row = closed_rows.get(coid)
            if row is None:
                seen = max(float(orders[coid].get("placed_at") or now), float(orders[coid].get("cancelled_at") or 0))
                if now - seen >= LOST_AFTER_SEC:
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
                pending.append({**exit_for(o, filled, cfg, mk), "exit_since": now})
            else:
                fill["pnl_usd"] = round(pair_pnl(o, filled, cfg["fee_bps"]), 6)
                state["realized_usd"] = round(state["realized_usd"] + fill["pnl_usd"], 6)
            report["fills"].append(fill)

        def _pull(coid: str, o: Dict[str, Any]) -> bool:
            res = cancel(symbol, live[coid])
            if not res.get("success"):
                report["errors"].append({"symbol": symbol, "coid": coid, "error": str(res.get("error") or "cancel_failed")})
                return False
            o["cancelled"], o["cancelled_at"] = True, now
            if o["side"] == "sell":
                bal[symbol] = bal.get(symbol, 0.0) + float(o["qty"])
            else:
                bal[quote] = bal.get(quote, 0.0) + float(o["qty"]) * float(o["price"])
            return True

        def _moved(target: float, current: float) -> bool:
            return abs(target / current - 1) * 1e4 >= cfg["reprice_bps"]

        mid = (float(book["bid"]) + float(book["ask"])) / 2
        # Available bal already excludes locked quote reserve; include locked base approx via open sells.
        skews[symbol] = skew_factor(bal, symbol, mid, quote)
        cfg["_inventory_skew"] = skews[symbol]
        anchor = state["anchors"].get(symbol) or {}
        drift = abs(mid / float(anchor["ref"]) - 1) * 1e4 if anchor.get("ref") else None
        age_min = (now - float(anchor.get("at") or now)) / 60
        if drift is None or drift > cfg["recenter_bps"] or age_min >= cfg["refresh_minutes"]:
            for coid, o in list(orders.items()):
                if o["symbol"] != symbol or o["kind"] != "entry" or o.get("cancelled") or coid not in live:
                    continue
                target = entry_price(mid, o["side"], int(o["level"]), cfg, int(mk["price_decimals"]))
                if not _moved(target, float(o["price"])):
                    report["kept"] += 1
                    continue
                if _pull(coid, o):
                    report["cancelled"].append(coid)
            state["anchors"][symbol] = {"ref": mid, "at": now}
        refs[symbol] = float(state["anchors"][symbol]["ref"])

        # Aged exits step toward the market, never inside min_exit_bps of their entry.
        for coid, o in list(orders.items()):
            if o["symbol"] != symbol or o["kind"] != "exit" or o.get("cancelled") or coid not in live:
                continue
            since = float(o.get("exit_since") or o.get("placed_at") or now)
            spec = exit_spec(o["entry_side"], float(o["entry_price"]), float(o["entry_qty"]),
                             exit_bps_at(cfg, now - since), cfg, mk)
            price = float(o["price"])
            closer = spec["price"] < price if o["side"] == "sell" else spec["price"] > price
            if not closer or not _moved(spec["price"], price) or not _pull(coid, o):
                continue
            report["repriced"].append(coid)
            pending.append({k: o[k] for k in ("symbol", "level", "entry_side", "entry_price", "entry_qty")}
                           | spec | {"exit_since": since})

    open_count = sum(1 for o in orders.values() if not o.get("cancelled"))

    def _try_place(spec: Dict[str, Any], kind: str) -> Optional[str]:
        nonlocal open_count
        symbol, side, price, qty = spec["symbol"], spec["side"], float(spec["price"]), float(spec["qty"])
        coid = f"{TAG}{symbol[:4]}-{side[:1]}{spec['level']}{'x' if kind == 'exit' else 'n'}-{int(now * 1000) % 10**9}"
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

    def _cancel_entry(coid: str, o: Dict[str, Any]) -> bool:
        live = lives.get(str(o.get("symbol") or ""), {})
        if coid not in live:
            return False
        res = cancel(str(o["symbol"]), live[coid])
        if not res.get("success"):
            report["errors"].append({"symbol": o["symbol"], "coid": coid, "error": str(res.get("error") or "cancel_failed")})
            return False
        o["cancelled"], o["cancelled_at"] = True, now
        if o["side"] == "sell":
            bal[str(o["symbol"])] = bal.get(str(o["symbol"]), 0.0) + float(o["qty"])
        else:
            bal[quote] = bal.get(quote, 0.0) + float(o["qty"]) * float(o["price"])
        report["cancelled"].append(coid)
        report.setdefault("freed_for_exit", []).append(coid)
        return True

    def _free_capital_for_exit(spec: Dict[str, Any]) -> bool:
        """Cancel farthest entry rungs that lock the asset an exit needs."""
        symbol, side = str(spec["symbol"]), str(spec["side"])
        qty, price = float(spec["qty"]), float(spec["price"])
        if _fundable(symbol, side, qty, price):
            return True
        lock_side = "buy" if side == "buy" else "sell"  # buy exit needs quote ← cancel buy entries
        candidates = [
            (coid, o) for coid, o in orders.items()
            if not o.get("cancelled") and o.get("kind") == "entry" and o.get("side") == lock_side
            and coid in lives.get(str(o.get("symbol") or ""), {})
        ]
        # Prefer same-symbol first, then farthest levels.
        candidates.sort(key=lambda item: (
            0 if item[1].get("symbol") == symbol else 1,
            -int(item[1].get("level") or 0),
        ))
        for coid, o in candidates:
            if _fundable(symbol, side, qty, price):
                break
            _cancel_entry(coid, o)
        return _fundable(symbol, side, qty, price)

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
            if not _free_capital_for_exit(spec):
                report["skipped"].append({"symbol": spec["symbol"], "reason": "exit_unfunded", "qty": qty, "price": price})
                still.append(spec)
                continue
        if _try_place(spec, "exit") is None:
            still.append(spec)
    state["pending"] = pending = still

    pending_quote = sum(float(s["qty"]) * float(s["price"]) for s in pending if s.get("side") == "buy")
    pending_base: Dict[str, float] = {}
    for s in pending:
        if s.get("side") == "sell":
            sym = str(s["symbol"])
            pending_base[sym] = pending_base.get(sym, 0.0) + float(s["qty"])

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
        cfg["_inventory_skew"] = skews.get(symbol, 0.0)
        price = entry_price(refs[symbol], side, level, cfg, int(mk["price_decimals"]))
        if _crosses(state, symbol, side, price, maker_sell(symbol)):
            continue
        if side == "sell":
            avail = max(0.0, bal.get(symbol, 0.0) - pending_base.get(symbol, 0.0))
            qty = floor_qty(min(cfg["order_usd"] / price, avail * 0.995), int(mk["qty_decimals"]))
        else:
            avail_quote = max(0.0, bal.get(quote, 0.0) - reserve - pending_quote)
            qty = floor_qty(min(cfg["order_usd"], max(0.0, avail_quote - 0.02)) / price, int(mk["qty_decimals"]))
        if qty * price < max(cfg["min_order_usd"], mk["min_quote"]) or qty < mk["min_qty"]:
            continue
        _try_place({"symbol": symbol, "side": side, "level": level, "entry_side": side, "price": price, "qty": qty},
                   "entry")

    report["open_orders"] = sum(1 for o in orders.values() if not o.get("cancelled"))
    report["pending_exits"] = len(pending)
    report["realized_usd"] = state["realized_usd"]
    report["skews"] = {k: round(v, 4) for k, v in skews.items()}
    _save_state(spath, state)
    try:
        observe_ladder(report, balances=bal, quote=quote, skews=skews)
    except Exception:
        pass
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
    if report.get("cancelled") or report.get("repriced"):
        lines.append(f"{name} refresh moved {len(report.get('cancelled') or [])} entries "
                     f"(kept {report.get('kept', 0)}), stepped {len(report.get('repriced') or [])} exits closer")
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
