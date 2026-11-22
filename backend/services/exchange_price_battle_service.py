"""Price battle: buy ~$5 on a dip, take a small profit, or rotate after max hold.

Remembers every open position (symbol, qty, entry price). Sells when bid clears
entry + min_profit_bps + fee_buffer, or flat-exits after max_hold_sec (default 2h)
so capital can try a new lot. Buys prefer a short-term ask dip. JSONL buy/sell logs.
"""
from __future__ import annotations

import os
import time
import uuid
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_venue_api_service as vapi
from backend.services import external_exchange_connector_service as conn
from backend.services.exchange_binance_withdraw_service import (
    _attach_binance_error,
    _http_request,
    _sign_binance,
    binance_credentials,
)

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_price_battle_config.json")
_POSITIONS_PATH = os.path.join(ex._DATA_DIR, "price_battle_positions.json")
_BUYS_PATH = os.path.join(ex._DATA_DIR, "price_battle_buys.jsonl")
_SELLS_PATH = os.path.join(ex._DATA_DIR, "price_battle_sells.jsonl")
_STATE_PATH = os.path.join(ex._DATA_DIR, "price_battle_state.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def live_enabled() -> bool:
    """Separate live gate so churn agents can stay off while price-battle runs."""
    if os.environ.get("EXCHANGE_PRICE_BATTLE_LIVE", "").strip().lower() not in ("1", "true", "yes"):
        return False
    try:
        from backend.services.exchange_arbitrage_service import live_enabled as arb_live
        if not arb_live():
            return False
    except Exception:
        return False
    return True


def _read_positions() -> Dict[str, Any]:
    data = ex._read_json(_POSITIONS_PATH, {"open": []})
    if not isinstance(data, dict):
        data = {"open": []}
    data.setdefault("open", [])
    return data


def _write_positions(data: Dict[str, Any]) -> None:
    ex._write_json(_POSITIONS_PATH, data)


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"tick_count": 0, "last_tick": None})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _append_buy(row: Dict[str, Any]) -> None:
    ex._append_jsonl(_BUYS_PATH, row)


def _append_sell(row: Dict[str, Any]) -> None:
    ex._append_jsonl(_SELLS_PATH, row)


def _fill_from_order(order: Dict[str, Any], *, side: str, fallback_qty: float, fallback_px: float) -> Dict[str, float]:
    body = order.get("body") if isinstance(order.get("body"), dict) else {}
    qty = float(body.get("executedQty") or order.get("quantity") or fallback_qty or 0)
    quote_spent = float(body.get("cummulativeQuoteQty") or 0)
    px = 0.0
    fills = body.get("fills") if isinstance(body.get("fills"), list) else []
    if fills:
        num = 0.0
        den = 0.0
        for f in fills:
            if not isinstance(f, dict):
                continue
            fq = float(f.get("qty") or 0)
            fp = float(f.get("price") or 0)
            num += fq * fp
            den += fq
        if den > 0:
            px = num / den
            qty = den
            quote_spent = num
    if px <= 0 and qty > 0 and quote_spent > 0:
        px = quote_spent / qty
    if px <= 0:
        px = float(fallback_px or 0)
    if quote_spent <= 0 and qty > 0 and px > 0:
        quote_spent = qty * px
    return {"qty": round(qty, 12), "price": round(px, 10), "quote": round(quote_spent, 8)}


def _ticker_prices(venue_id: str, symbol: str) -> Dict[str, float]:
    tick = conn.fetch_ticker(venue_id, symbol, timeout=5.0) or {}
    bid = float(tick.get("bid") or 0)
    ask = float(tick.get("ask") or 0)
    last = float(tick.get("last") or 0)
    if bid <= 0 or ask <= 0:
        batch = conn.fetch_prices([symbol], venues=[venue_id], use_cache=True)
        row = ((batch.get("prices") or {}).get(symbol) or {}).get(venue_id) or {}
        bid = bid or float(row.get("bid") or 0)
        ask = ask or float(row.get("ask") or 0)
        last = last or float(row.get("last") or 0)
    if bid <= 0:
        bid = last or ask
    if ask <= 0:
        ask = last or bid
    return {"bid": bid, "ask": ask, "last": last or ((bid + ask) / 2 if bid and ask else 0)}


def _need_profit_bps(cfg: Dict[str, Any]) -> float:
    """Gross move needed: net target (min_profit_bps) + fee cushion."""
    min_bps = float(cfg.get("min_profit_bps") or 50)
    fee_buf = float(cfg.get("fee_buffer_bps") or 20)
    return min_bps + fee_buf


def _position_age_sec(pos: Dict[str, Any]) -> float:
    return max(0.0, time.time() - float(pos.get("bought_at_unix") or 0))


def _profit_ready(pos: Dict[str, Any], bid: float, cfg: Dict[str, Any]) -> Dict[str, Any]:
    entry = float(pos.get("entry_price") or 0)
    qty = float(pos.get("qty") or 0)
    need_bps = _need_profit_bps(cfg)
    if entry <= 0 or qty <= 0 or bid <= 0:
        return {"ready": False, "reason": "bad_price", "target_price": 0, "pnl_usd": 0}
    target = entry * (1.0 + need_bps / 10000.0)
    value_now = qty * bid
    cost = qty * entry
    pnl = value_now - cost
    min_hold = int(cfg.get("min_hold_sec") or 0)
    age = _position_age_sec(pos)
    if min_hold > 0 and age < min_hold:
        return {
            "ready": False,
            "reason": "min_hold",
            "target_price": round(target, 10),
            "pnl_usd": round(pnl, 6),
            "age_sec": round(age, 1),
        }
    if bid + 1e-12 < target:
        return {
            "ready": False,
            "reason": "waiting_profit",
            "target_price": round(target, 10),
            "pnl_usd": round(pnl, 6),
            "bid": bid,
            "entry": entry,
            "age_sec": round(age, 1),
        }
    return {
        "ready": True,
        "reason": "profit",
        "target_price": round(target, 10),
        "pnl_usd": round(pnl, 6),
        "bid": bid,
        "entry": entry,
        "age_sec": round(age, 1),
    }


def _time_stop_ready(pos: Dict[str, Any], bid: float, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Flat-exit after max_hold_sec so we rotate into a fresh lot."""
    max_hold = int(cfg.get("max_hold_sec") or 0)
    age = _position_age_sec(pos)
    entry = float(pos.get("entry_price") or 0)
    qty = float(pos.get("qty") or 0)
    pnl = (qty * bid - qty * entry) if entry > 0 and qty > 0 and bid > 0 else 0.0
    if max_hold <= 0 or age < max_hold:
        return {
            "ready": False,
            "reason": "within_max_hold",
            "age_sec": round(age, 1),
            "max_hold_sec": max_hold,
            "pnl_usd": round(pnl, 6),
        }
    return {
        "ready": True,
        "reason": "time_stop",
        "age_sec": round(age, 1),
        "max_hold_sec": max_hold,
        "pnl_usd": round(pnl, 6),
        "bid": bid,
        "entry": entry,
    }


def _update_ask_highs(state: Dict[str, Any], venue_id: str, symbols: List[str]) -> Dict[str, float]:
    """Track recent ask highs per symbol for dip detection."""
    highs = state.setdefault("ask_high", {})
    if not isinstance(highs, dict):
        highs = {}
        state["ask_high"] = highs
    # Decay: if ask recovers above high, raise high; if much below, keep high as resistance.
    for sym in symbols:
        px = _ticker_prices(venue_id, sym)
        ask = float(px.get("ask") or 0)
        if ask <= 0:
            continue
        prev = float(highs.get(sym) or 0)
        if ask >= prev:
            highs[sym] = ask
        # Soft decay so stale highs don't block buys forever (~0.05% per tick).
        elif prev > 0 and ask < prev * 0.997:
            highs[sym] = round(prev * 0.9995 + ask * 0.0005, 10)
    return {str(k): float(v) for k, v in highs.items() if float(v or 0) > 0}


def _is_dip(sym: str, ask: float, highs: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not cfg.get("buy_dip_only", True):
        return {"ok": True, "reason": "dip_filter_off"}
    dip_bps = float(cfg.get("dip_bps") or 25)
    high = float(highs.get(sym) or 0)
    if high <= 0 or ask <= 0:
        # No history yet — allow first observation to seed, skip buy this tick.
        return {"ok": False, "reason": "no_ask_high_yet", "ask": ask, "high": high}
    threshold = high * (1.0 - dip_bps / 10000.0)
    if ask <= threshold + 1e-12:
        return {
            "ok": True,
            "reason": "dip",
            "ask": ask,
            "high": high,
            "threshold": round(threshold, 10),
            "dip_bps": dip_bps,
        }
    return {
        "ok": False,
        "reason": "not_on_dip",
        "ask": ask,
        "high": high,
        "threshold": round(threshold, 10),
        "dip_bps": dip_bps,
    }


def _ensure_spot_qty(venue_id: str, symbol: str, need: float) -> Dict[str, Any]:
    """If Flexible Earn auto-subscribed the buy, redeem enough to sell."""
    bals = vapi.parse_spot_balances(venue_id, dry_run=False, force_refresh=True)
    free = float(bals.get(symbol) or 0)
    if free + 1e-12 >= need:
        return {"ok": True, "free": free, "redeemed": 0.0}
    gap = round(need - free, 8)
    redeem = _redeem_flexible(symbol, gap)
    bals2 = vapi.parse_spot_balances(venue_id, dry_run=False, force_refresh=True)
    free2 = float(bals2.get(symbol) or 0)
    return {
        "ok": free2 + 1e-8 >= need,
        "free": free2,
        "redeemed": gap if redeem.get("success") else 0.0,
        "redeem": redeem,
    }


def _redeem_flexible(asset: str, amount: float) -> Dict[str, Any]:
    """Redeem Binance Simple Earn flexible position back to spot."""
    if not live_enabled():
        return {"success": True, "simulated": True, "mode": "paper", "asset": asset, "amount": amount}

    creds = binance_credentials()
    if not creds.get("api_key") or not creds.get("api_secret"):
        return {"success": False, "error": "missing_binance_creds"}

    # Resolve productId from flexible positions.
    params = {"timestamp": int(time.time() * 1000), "recvWindow": 10000, "size": 100}
    query = urllib.parse.urlencode(params)
    sig = _sign_binance(params, str(creds["api_secret"]))
    url = f"https://api.binance.com/sapi/v1/simple-earn/flexible/position?{query}&signature={sig}"
    listed = _http_request("GET", url, headers={"X-MBX-APIKEY": creds["api_key"]}, timeout=15.0)
    body = listed.get("body") if isinstance(listed.get("body"), dict) else {}
    rows = body.get("rows") if isinstance(body.get("rows"), list) else []
    product_id = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("asset") or "").upper() == asset.upper():
            product_id = row.get("productId")
            break
    if not product_id:
        # Common Binance pattern ASSET001
        product_id = f"{asset.upper()}001"

    redeem_params = {
        "productId": product_id,
        "amount": f"{amount:.8f}".rstrip("0").rstrip("."),
        "timestamp": int(time.time() * 1000),
        "recvWindow": 10000,
    }
    q2 = urllib.parse.urlencode(redeem_params)
    sig2 = _sign_binance(redeem_params, str(creds["api_secret"]))
    url2 = f"https://api.binance.com/sapi/v1/simple-earn/flexible/redeem?{q2}&signature={sig2}"
    res = _http_request("POST", url2, headers={"X-MBX-APIKEY": creds["api_key"]}, timeout=20.0)
    res = _attach_binance_error(res, path="/sapi/v1/simple-earn/flexible/redeem")
    res.setdefault("asset", asset)
    res.setdefault("amount", amount)
    res.setdefault("productId", product_id)
    return res


def status() -> Dict[str, Any]:
    cfg = load_config()
    pos = _read_positions()
    state = _read_state()
    open_rows = [p for p in (pos.get("open") or []) if isinstance(p, dict)]
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "live": live_enabled(),
        "position_usd": float(cfg.get("position_usd") or 5),
        "max_open_positions": int(cfg.get("max_open_positions") or 3),
        "min_profit_bps": float(cfg.get("min_profit_bps") or 50),
        "fee_buffer_bps": float(cfg.get("fee_buffer_bps") or 20),
        "need_profit_bps": _need_profit_bps(cfg),
        "max_hold_sec": int(cfg.get("max_hold_sec") or 7200),
        "buy_dip_only": bool(cfg.get("buy_dip_only", True)),
        "dip_bps": float(cfg.get("dip_bps") or 25),
        "open_count": len(open_rows),
        "open": open_rows,
        "tick_count": int(state.get("tick_count") or 0),
        "last_tick": state.get("last_tick"),
        "buys_log": _BUYS_PATH,
        "sells_log": _SELLS_PATH,
        "hint": "Set EXCHANGE_PRICE_BATTLE_LIVE=1 for real $5 buy/hold/sell orders.",
    }


def _open_symbols(open_rows: List[Dict[str, Any]]) -> set:
    return {str(p.get("symbol") or "").upper() for p in open_rows}


def _try_sell_position(pos: Dict[str, Any], cfg: Dict[str, Any], *, dry_run: bool) -> Dict[str, Any]:
    venue_id = str(cfg.get("venue_id") or "binance")
    quote = str(cfg.get("quote") or "USDC").upper()
    symbol = str(pos.get("symbol") or "").upper()
    qty = float(pos.get("qty") or 0)
    entry = float(pos.get("entry_price") or 0)
    prices = _ticker_prices(venue_id, symbol)
    bid = float(prices.get("bid") or 0)
    profit = _profit_ready(pos, bid, cfg)
    timed = _time_stop_ready(pos, bid, cfg)
    if profit.get("ready"):
        check = profit
        exit_reason = "profit"
    elif timed.get("ready"):
        # Respect min_hold even for time-stop (avoid instant flip).
        min_hold = int(cfg.get("min_hold_sec") or 0)
        if min_hold > 0 and float(timed.get("age_sec") or 0) < min_hold:
            return {
                "action": "hold",
                "position_id": pos.get("id"),
                "symbol": symbol,
                "entry_price": entry,
                "bid": bid,
                **profit,
            }
        check = timed
        exit_reason = "time_stop"
    else:
        return {
            "action": "hold",
            "position_id": pos.get("id"),
            "symbol": symbol,
            "entry_price": entry,
            "bid": bid,
            "max_hold_sec": timed.get("max_hold_sec"),
            **profit,
        }

    spot = _ensure_spot_qty(venue_id, symbol, qty)
    if not spot.get("ok") and not dry_run:
        return {
            "action": "hold",
            "position_id": pos.get("id"),
            "symbol": symbol,
            "success": False,
            "error": "insufficient_spot_after_redeem",
            "spot": spot,
            **check,
        }

    if dry_run or not live_enabled():
        fill = {"qty": qty, "price": bid, "quote": round(qty * bid, 8)}
        order = {"success": True, "simulated": True, "mode": "paper"}
    else:
        order = vapi.place_market_order(venue_id, symbol, "sell", qty, dry_run=False, quote=quote)
        if not order.get("success"):
            return {
                "action": "sell_failed",
                "position_id": pos.get("id"),
                "symbol": symbol,
                "success": False,
                "error": order.get("error") or vapi.extract_order_error(order) or "sell_failed",
                "order": order,
                "exit_reason": exit_reason,
                **check,
            }
        fill = _fill_from_order(order, side="sell", fallback_qty=qty, fallback_px=bid)

    pnl = round(float(fill["quote"]) - float(pos.get("cost_usd") or (qty * entry)), 6)
    sell_row = {
        "ts": _iso(),
        "position_id": pos.get("id"),
        "symbol": symbol,
        "side": "sell",
        "qty": fill["qty"],
        "exit_price": fill["price"],
        "entry_price": entry,
        "proceeds_usd": fill["quote"],
        "cost_usd": pos.get("cost_usd"),
        "pnl_usd": pnl,
        "exit_reason": exit_reason,
        "hold_sec": round(_position_age_sec(pos), 1),
        "order_id": (order.get("body") or {}).get("orderId") if isinstance(order.get("body"), dict) else order.get("order_id"),
        "mode": order.get("mode") or ("paper" if order.get("simulated") else "live"),
        "venue_id": venue_id,
    }
    _append_sell(sell_row)
    return {
        "action": "sold",
        "success": True,
        "position_id": pos.get("id"),
        "symbol": symbol,
        "exit_reason": exit_reason,
        "sell": sell_row,
        "order": order,
    }


def _try_open_buy(
    cfg: Dict[str, Any],
    open_rows: List[Dict[str, Any]],
    *,
    dry_run: bool,
    ask_highs: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    venue_id = str(cfg.get("venue_id") or "binance")
    quote = str(cfg.get("quote") or "USDC").upper()
    position_usd = float(cfg.get("position_usd") or 5.0)
    max_open = int(cfg.get("max_open_positions") or 3)
    reserve = float(cfg.get("min_venue_quote_reserve_usd") or 15.0)
    highs = ask_highs or {}
    if len(open_rows) >= max_open:
        return {"action": "skip_buy", "reason": "max_open_positions"}

    bals = vapi.parse_spot_balances(venue_id, dry_run=False, force_refresh=False)
    quote_free = float(bals.get(quote) or 0)
    spendable = quote_free - reserve
    if spendable < position_usd:
        return {
            "action": "skip_buy",
            "reason": "insufficient_quote",
            "quote_free": quote_free,
            "spendable": round(spendable, 4),
            "need": position_usd,
        }

    owned = _open_symbols(open_rows)
    symbols = [str(s).upper() for s in (cfg.get("symbols") or []) if str(s).upper() not in owned]
    if not symbols:
        return {"action": "skip_buy", "reason": "all_symbols_open"}

    # Prefer deepest dip among candidates (buy cheap on weakness).
    scored: List[Dict[str, Any]] = []
    dip_skips: List[Dict[str, Any]] = []
    for sym in symbols:
        px = _ticker_prices(venue_id, sym)
        ask = float(px.get("ask") or 0)
        if ask <= 0:
            continue
        dip = _is_dip(sym, ask, highs, cfg)
        if not dip.get("ok"):
            dip_skips.append({"symbol": sym, **dip})
            continue
        spec = vapi.market_order_for_leg(venue_id, "buy", sym, position_usd, quote=quote)
        if not spec.get("ok"):
            continue
        notional = float(spec.get("notional_usd") or position_usd)
        if notional > position_usd * 1.35:
            continue
        high = float(highs.get(sym) or ask)
        dip_pct = ((high - ask) / high * 100.0) if high > 0 else 0.0
        scored.append({"symbol": sym, "ask": ask, "spec": spec, "dip_pct": dip_pct, "dip": dip})
    if not scored:
        return {
            "action": "skip_buy",
            "reason": "no_dip_or_tradeable_symbol",
            "dip_skips": dip_skips[:6],
        }
    scored.sort(key=lambda r: (-float(r["dip_pct"]), float(r["ask"])))
    pick = scored[0]
    sym = pick["symbol"]
    spec = pick["spec"]
    qty = float(spec["quantity"])
    ask = float(pick["ask"])

    if dry_run or not live_enabled():
        order = {"success": True, "simulated": True, "mode": "paper", "quantity": qty}
        fill = {"qty": qty, "price": ask, "quote": round(qty * ask, 8)}
    else:
        order = vapi.place_market_order(venue_id, sym, "buy", qty, dry_run=False, quote=quote)
        if not order.get("success"):
            return {
                "action": "buy_failed",
                "success": False,
                "symbol": sym,
                "error": order.get("error") or vapi.extract_order_error(order) or "buy_failed",
                "order": order,
            }
        fill = _fill_from_order(order, side="buy", fallback_qty=qty, fallback_px=ask)

    pid = f"pb_{uuid.uuid4().hex[:12]}"
    pos = {
        "id": pid,
        "symbol": sym,
        "qty": fill["qty"],
        "entry_price": fill["price"],
        "cost_usd": fill["quote"],
        "target_profit_bps": float(cfg.get("min_profit_bps") or 50),
        "need_profit_bps": _need_profit_bps(cfg),
        "max_hold_sec": int(cfg.get("max_hold_sec") or 7200),
        "bought_at": _iso(),
        "bought_at_unix": time.time(),
        "venue_id": venue_id,
        "quote": quote,
        "mode": order.get("mode") or ("paper" if order.get("simulated") else "live"),
        "order_id": (order.get("body") or {}).get("orderId") if isinstance(order.get("body"), dict) else order.get("order_id"),
        "dip": pick.get("dip"),
    }
    buy_row = {
        "ts": _iso(),
        "position_id": pid,
        "symbol": sym,
        "side": "buy",
        "qty": fill["qty"],
        "entry_price": fill["price"],
        "cost_usd": fill["quote"],
        "ask_at_decision": ask,
        "dip_pct": pick.get("dip_pct"),
        "order_id": pos.get("order_id"),
        "mode": pos.get("mode"),
        "venue_id": venue_id,
    }
    _append_buy(buy_row)
    return {"action": "bought", "success": True, "position": pos, "buy": buy_row, "order": order}


def run_tick(*, force: bool = False, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": False, "error": "price_battle_disabled"}

    live = live_enabled()
    paper = dry_run if dry_run is not None else (not live)
    venue_id = str(cfg.get("venue_id") or "binance")

    try:
        vapi.refresh_venue_balances([venue_id], force=True)
    except Exception:
        pass

    store = _read_positions()
    open_rows = [p for p in (store.get("open") or []) if isinstance(p, dict)]
    still_open: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []

    state = _read_state()
    watch_syms = [str(s).upper() for s in (cfg.get("symbols") or [])]
    ask_highs = _update_ask_highs(state, venue_id, watch_syms)

    for pos in open_rows:
        res = _try_sell_position(pos, cfg, dry_run=paper)
        actions.append(res)
        if res.get("action") == "sold" and res.get("success"):
            continue
        still_open.append(pos)

    buy_res = _try_open_buy(cfg, still_open, dry_run=paper, ask_highs=ask_highs)
    actions.append(buy_res)
    if buy_res.get("action") == "bought" and buy_res.get("position"):
        still_open.append(buy_res["position"])

    store["open"] = still_open
    _write_positions(store)

    state["tick_count"] = int(state.get("tick_count") or 0) + 1
    state["last_tick"] = _iso()
    state["last_mode"] = "live" if live and not paper else "paper"
    state["last_open"] = len(still_open)
    _write_state(state)

    return {
        "success": True,
        "mode": state["last_mode"],
        "live_gate": live,
        "tick_count": state["tick_count"],
        "open_positions": len(still_open),
        "actions": actions,
        "positions": still_open,
        "buys_log": _BUYS_PATH,
        "sells_log": _SELLS_PATH,
    }
