"""Ten spot strategies for the fast-coin daemon.

Each pass scores XRP, XLM, ALGO, TRX, and SOL and writes the calculation.
When ``execute`` is on, a live long or sell signal is sent once per episode.
The same signal is not sent again on the next minute.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from statistics import mean, pstdev
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_cross_trade_service import (
    FAST_USDT_COINS,
    fetch_nonkyc_book,
    search_fast_books,
    search_log_paths,
)
from backend.services.exchange_maker_quote_service import own_sell_price
from backend.services.exchange_venue_api_service import parse_spot_balances, place_limit_order

Candle = Dict[str, float]

STRATEGIES: Tuple[Tuple[str, str], ...] = (
    ("trend", "Trendfølging"),
    ("momentum", "Momentum-handel"),
    ("breakout", "Breakout-handel"),
    ("swing", "Swing-trading"),
    ("range", "Range-trading"),
    ("scalp", "Scalping"),
    ("reversal", "Reverserings-handel"),
    ("news", "Nyhedsbaseret handel"),
    ("gap", "Gap-trading"),
    ("pairs", "Par-handel"),
)

_KLINE_URLS = (
    "https://data-api.binance.vision/api/v3/klines",
    "https://api.binance.com/api/v3/klines",
)
_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_strategy_config.json")
# NonKYC USDC kept back when converting to USDT for strategy buys.
USDC_RESERVE = 5.0
# A strategy that flips flat and back within this window does not buy the same coin again.
REENTRY_MINUTES = 240.0


def _default_config() -> Dict[str, Any]:
    return {
        "execute": False,
        "symbols": list(FAST_USDT_COINS),
        "notional_usd": 25.0,
        "strategies": [key for key, _name in STRATEGIES],
    }


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, None)
    if not isinstance(cfg, dict):
        cfg = _default_config()
    base = _default_config()
    base.update({k: v for k, v in cfg.items() if v is not None})
    if not isinstance(base.get("symbols"), list) or not base["symbols"]:
        base["symbols"] = list(FAST_USDT_COINS)
    else:
        base["symbols"] = [str(s).upper() for s in base["symbols"] if str(s).strip()]
    known = {key for key, _name in STRATEGIES}
    picked = [str(s) for s in (base.get("strategies") or []) if str(s) in known]
    base["strategies"] = picked or [key for key, _name in STRATEGIES]
    base["execute"] = bool(base.get("execute"))
    try:
        base["notional_usd"] = max(1.0, float(base.get("notional_usd") or 25.0))
    except (TypeError, ValueError):
        base["notional_usd"] = 25.0
    raw_scores = base.get("strategy_score_pct") if isinstance(base.get("strategy_score_pct"), dict) else {}
    scores: Dict[str, float] = {}
    for key, _name in STRATEGIES:
        if key not in raw_scores:
            continue
        try:
            scores[key] = float(raw_scores[key])
        except (TypeError, ValueError):
            continue
    base["strategy_score_pct"] = scores
    raw_clips = base.get("strategy_notional") if isinstance(base.get("strategy_notional"), dict) else {}
    clips: Dict[str, float] = {}
    for key, _name in STRATEGIES:
        raw = raw_clips.get(key, base["notional_usd"])
        try:
            clips[key] = max(1.0, float(raw))
        except (TypeError, ValueError):
            clips[key] = base["notional_usd"]
    base["strategy_notional"] = clips
    try:
        base["max_orders"] = max(1, int(base.get("max_orders") or 10))
    except (TypeError, ValueError):
        base["max_orders"] = 10
    return base


def select_strategy_orders(
    rows: Sequence[Dict[str, Any]],
    scores: Dict[str, float],
    *,
    max_orders: int = 2,
) -> List[Dict[str, Any]]:
    """Keep at most two live signals from strategies whose measured return is above zero."""
    picked: List[Dict[str, Any]] = []
    for row in rows or []:
        name = str(row.get("strategy") or "")
        if name not in scores or float(scores[name]) <= 0:
            continue
        if not row.get("ready") or row.get("signal") not in ("long", "sell"):
            continue
        picked.append(row)
    picked.sort(key=lambda row: float(scores[str(row.get("strategy") or "")]), reverse=True)
    return picked[: max(0, int(max_orders))]


def signal_orders(rows: Sequence[Dict[str, Any]], *, max_orders: int = 10) -> List[Dict[str, Any]]:
    """Every ready long or sell on a single coin, in strategy order."""
    order = {key: index for index, (key, _name) in enumerate(STRATEGIES)}
    picked = [
        row for row in (rows or [])
        if row.get("ready") and row.get("signal") in ("long", "sell") and "/" not in str(row.get("symbol") or "")
    ]
    picked.sort(key=lambda row: (order.get(str(row.get("strategy") or ""), 99), str(row.get("symbol") or "")))
    return picked[: max(0, int(max_orders))]


def _signal_key(row: Dict[str, Any]) -> str:
    return f"{row.get('strategy')}:{row.get('symbol')}:{row.get('signal')}"


def _order_state_path(path: Optional[str] = None) -> str:
    if path:
        return path
    return os.path.join(ex._BASE, "data", "crypto_exchange", "strategy_order_state.json")


def _load_order_state(path: str) -> Tuple[List[str], Dict[str, float]]:
    raw = ex._read_json(path, None)
    if not isinstance(raw, dict):
        return [], {}
    sent_at: Dict[str, float] = {}
    for key, ts in (raw.get("sent_at") or {}).items():
        try:
            sent_at[str(key)] = float(ts)
        except (TypeError, ValueError):
            continue
    return [str(key) for key in (raw.get("open") or [])], sent_at


def _save_order_state(path: str, keys: Sequence[str], sent_at: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"open": list(keys), "sent_at": sent_at}, handle)
        handle.write("\n")


def _book_quotes(book_report: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    quotes: Dict[str, Dict[str, float]] = {}
    for coin in (book_report or {}).get("coins") or []:
        symbol = str(coin.get("symbol") or "")
        if not symbol:
            continue
        quotes[symbol] = {
            "bid": float(coin.get("binance_bid") or 0),
            "ask": float(coin.get("binance_ask") or 0),
            "nonkyc_bid": float(coin.get("nonkyc_bid") or 0),
            "nonkyc_ask": float(coin.get("nonkyc_ask") or 0),
        }
    return quotes


def _error_text(res: Dict[str, Any]) -> str:
    body = res.get("body") if isinstance(res.get("body"), dict) else {}
    return str(res.get("error") or body.get("msg") or body.get("message") or "")


def _accepted(res: Dict[str, Any]) -> bool:
    if not res.get("success") or res.get("simulated"):
        return False
    return str(res.get("mode") or "").lower() != "paper"


_TICKS: Dict[str, Decimal] = {}


def _binance_tick(symbol: str) -> Decimal:
    cached = _TICKS.get(symbol)
    if cached is not None:
        return cached
    tick = Decimal("0")
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/exchangeInfo",
            params={"symbol": f"{symbol}USDC"},
            timeout=6,
            headers={"User-Agent": "masternoder-strategies/1.0"},
        )
        body = resp.json()
        row = (body.get("symbols") or [None])[0] or {}
        for filt in row.get("filters") or []:
            if str(filt.get("filterType") or "") == "PRICE_FILTER":
                tick = Decimal(str(filt.get("tickSize") or "0"))
    except (requests.RequestException, ValueError, ArithmeticError, IndexError):
        tick = Decimal("0")
    _TICKS[symbol] = tick
    return tick


def _on_tick(price: float, tick: Decimal, *, up: bool) -> float:
    if price <= 0 or tick <= 0:
        return float(price)
    raw = Decimal(str(price))
    rounding = ROUND_UP if up else ROUND_DOWN
    return float((raw / tick).to_integral_value(rounding=rounding) * tick)


def _walk_nonkyc_buy(symbol: str, quote_usd: float) -> Optional[float]:
    book = fetch_nonkyc_book(symbol)
    asks = sorted(
        ((float(price), float(qty)) for price, qty in (book.get("asks") or []) if float(price) > 0 and float(qty) > 0),
        key=lambda row: row[0],
    )
    if not asks:
        return None
    best = asks[0][0]
    ceiling = best * 1.005
    got = 0.0
    limit = best
    for price, qty in asks:
        if price > ceiling:
            break
        got += min(qty * price, quote_usd - got)
        limit = price
        if got >= quote_usd - 1e-6:
            return limit
    return None


def _default_place(venue: str, symbol: str, side: str, qty: float, price: float, tif: str) -> Dict[str, Any]:
    coid = f"s-{symbol[:4]}-{side[:1]}-{int(time.time() * 1000) % 10**10}"
    quote = "USDC" if venue == "binance" else "USDT"
    return place_limit_order(
        venue, symbol, side, qty, price,
        dry_run=False, quote=quote, client_order_id=coid, time_in_force=tif,
    )


def _nonkyc_usdc_bid() -> Optional[float]:
    bids = [price for price, qty in (fetch_nonkyc_book("USDC").get("bids") or []) if price > 0 and qty > 0]
    return max(bids) if bids else None


def tradable_rows(rows: Sequence[Dict[str, Any]], scores: Dict[str, float]) -> List[Dict[str, Any]]:
    """Drop rows from strategies whose walk-forward return is below zero; they stay paper-only."""
    return [
        row for row in (rows or [])
        if float(scores.get(str(row.get("strategy") or ""), 0.0)) >= 0
    ]


def dispatch_strategy_orders(
    report: Dict[str, Any],
    book_report: Optional[Dict[str, Any]] = None,
    *,
    place: Optional[Callable[..., Dict[str, Any]]] = None,
    balances: Optional[Dict[str, Dict[str, float]]] = None,
    quotes: Optional[Dict[str, Dict[str, float]]] = None,
    walk_book: Optional[Callable[[str, float], Optional[float]]] = None,
    usdc_bid: Optional[Callable[[], Optional[float]]] = None,
    state_path: Optional[str] = None,
    clock: Optional[Callable[[], float]] = None,
    maker_state_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Send one live order per new long/sell signal. Repeat signals stay locked.

    Buys go to Binance USDC first. When Binance has no budget or rejects the
    symbol, the buy goes to the NonKYC USDT book, topping USDT up from NonKYC
    USDC (USDC/USDT market) when needed.
    """
    if not report.get("execute"):
        return []
    sender = place or _default_place
    usdc_bid_fn = usdc_bid or _nonkyc_usdc_bid
    path = _order_state_path(state_path)
    quotes = quotes if quotes is not None else _book_quotes(book_report)
    if balances is None:
        balances = {
            "binance": parse_spot_balances("binance", dry_run=False, force_refresh=True),
            "nonkyc": parse_spot_balances("nonkyc", dry_run=False, force_refresh=True),
        }
    binance = {str(k).upper(): float(v or 0) for k, v in (balances.get("binance") or {}).items()}
    nonkyc = {str(k).upper(): float(v or 0) for k, v in (balances.get("nonkyc") or {}).items()}
    scores = report.get("strategy_score_pct") or {}
    live_rows = signal_orders(
        tradable_rows(report.get("rows") or report.get("orders") or [], scores),
        max_orders=int(report.get("max_orders") or 10),
    )
    live_keys = {_signal_key(row) for row in live_rows}
    try:
        stored_keys, sent_at = _load_order_state(path)
    except OSError:
        stored_keys, sent_at = [], {}
    open_keys = [key for key in stored_keys if key in live_keys]
    now = time.time() if clock is None else clock()
    cooldown_s = max(0.0, float(report.get("reentry_minutes", REENTRY_MINUTES))) * 60
    sent_at = {key: ts for key, ts in sent_at.items() if now - ts < cooldown_s}
    todo = [row for row in live_rows if _signal_key(row) not in set(open_keys) and _signal_key(row) not in sent_at]
    buys = [row for row in todo if row.get("signal") == "long"]
    usdc = float(binance.get("USDC") or 0)
    each = ((usdc - 1.0) / len(buys)) if buys and usdc > 1.0 else 0.0
    sent: List[Dict[str, Any]] = []

    def _finish(row: Dict[str, Any], res: Dict[str, Any], venue: str, side: str) -> None:
        item = {
            "strategy": row.get("strategy"),
            "symbol": row.get("symbol"),
            "signal": row.get("signal"),
            "venue": venue,
            "side": side,
            "success": _accepted(res),
            "order_id": res.get("order_id"),
            "error": _error_text(res),
        }
        sent.append(item)
        err = item["error"].lower()
        if item["success"] or "whitelist" in err or "insufficient" in err:
            open_keys.append(_signal_key(row))
        if item["success"]:
            sent_at[_signal_key(row)] = now

    def _send_row(row: Dict[str, Any], symbol: str, quote: Dict[str, float], key: str) -> None:
        if row.get("signal") == "sell":
            bid = float(quote.get("bid") or 0)
            held = float(binance.get(symbol) or 0)
            if bid <= 0 or held * bid < 5.0:
                if symbol == "XRP":
                    sent.append({"strategy": row.get("strategy"), "symbol": symbol, "signal": "sell", "skipped": "no_binance_inventory"})
                    open_keys.append(key)
                    return
                nk_bid = float(quote.get("nonkyc_bid") or 0)
                nk_held = float(nonkyc.get(symbol) or 0)
                if nk_bid <= 0 or nk_held * nk_bid < 5.0:
                    sent.append({"strategy": row.get("strategy"), "symbol": symbol, "signal": "sell", "skipped": "no_inventory"})
                    open_keys.append(key)
                    return
                qty = min(nk_held * 0.99, float(row.get("notional_usd") or 25) / nk_bid)
                res = sender("nonkyc", symbol, "sell", round(qty, 4), nk_bid, "GTC")
                _finish(row, res, "nonkyc", "sell")
                return
            clip = min(float(row.get("notional_usd") or 25), held * bid)
            price = _on_tick(bid, _binance_tick(symbol), up=False) if place is None else bid
            qty = min(held * 0.99, clip / price)
            res = sender("binance", symbol, "sell", qty, price, "IOC")
            _finish(row, res, "binance", "sell")
            return
        want = float(row.get("notional_usd") or 25)
        clip = min(want, each)
        ask = float(quote.get("ask") or 0)
        bn_error = ""
        if clip >= 5.0 and ask > 0:
            price = _on_tick(ask, _binance_tick(symbol), up=True) if place is None else ask
            res = sender("binance", symbol, "buy", clip / price, price, "IOC")
            if _accepted(res):
                _finish(row, res, "binance", "buy")
                return
            bn_error = _error_text(res)
            if "whitelist" not in bn_error.lower():
                _finish(row, res, "binance", "buy")
                return
        _nonkyc_buy(row, symbol, want, key, bn_error)

    def _top_up_usdt(need: float) -> Optional[str]:
        usdt = float(nonkyc.get("USDT") or 0)
        short = need + 0.05 - usdt
        if short <= 0:
            return None
        usdc = float(nonkyc.get("USDC") or 0)
        if usdc - USDC_RESERVE < short:
            return "no_usdt"
        bid = usdc_bid_fn()
        if not bid or bid < 0.99:
            return "usdc_book"
        px = round(bid * 0.999, 5)
        qty = round(min(usdc - USDC_RESERVE, short * 1.003 / px + 0.01), 2)
        res = sender("nonkyc", "USDC", "sell", qty, px, "GTC")
        sent.append({
            "convert": "USDC->USDT", "venue": "nonkyc", "qty": qty, "price": px,
            "success": _accepted(res), "order_id": res.get("order_id"), "error": _error_text(res),
        })
        if not _accepted(res):
            return "convert_failed"
        nonkyc["USDC"] = usdc - qty
        nonkyc["USDT"] = usdt + qty * px
        return None

    def _nonkyc_buy(row: Dict[str, Any], symbol: str, want: float, key: str, bn_error: str) -> None:
        base = {"strategy": row.get("strategy"), "symbol": symbol, "signal": "long"}
        blocked = _top_up_usdt(want)
        if blocked == "no_usdt":
            usdt = float(nonkyc.get("USDT") or 0)
            if usdt - 0.05 >= 5.0:
                want = usdt - 0.05
            else:
                sent.append({**base, "skipped": "budget", "error": bn_error})
                if bn_error:
                    open_keys.append(key)
                return
        elif blocked:
            sent.append({**base, "skipped": blocked, "error": bn_error})
            return
        walker = walk_book if walk_book is not None else _walk_nonkyc_buy
        nk_price = walker(symbol, want)
        if not nk_price:
            sent.append({**base, "skipped": "book_too_thin", "error": bn_error})
            open_keys.append(key)
            return
        own_sell = own_sell_price(symbol, maker_state_path)
        if own_sell is not None and float(nk_price) >= own_sell:
            sent.append({**base, "skipped": "own_maker_sell", "error": bn_error})
            return
        nk_res = sender("nonkyc", symbol, "buy", round(want / float(nk_price), 4), float(nk_price), "GTC")
        _finish(row, nk_res, "nonkyc", "buy")
        if _accepted(nk_res):
            nonkyc["USDT"] = max(0.0, float(nonkyc.get("USDT") or 0) - want)

    for row in todo:
        symbol = str(row.get("symbol") or "")
        quote = quotes.get(symbol) or {}
        key = _signal_key(row)
        try:
            _send_row(row, symbol, quote, key)
        except Exception as exc:
            sent.append({
                "strategy": row.get("strategy"), "symbol": symbol, "signal": row.get("signal"),
                "success": False, "error": str(exc),
            })
    try:
        _save_order_state(path, open_keys, sent_at)
    except OSError:
        pass
    return sent


def sma(values: Sequence[float], length: int) -> Optional[float]:
    if length <= 0 or len(values) < length:
        return None
    return sum(values[-length:]) / float(length)


def rsi(closes: Sequence[float], period: int = 14) -> Optional[float]:
    if period <= 0 or len(closes) < period + 1:
        return None
    gains: List[float] = []
    losses: List[float] = []
    for prev, cur in zip(closes, closes[1:]):
        delta = cur - prev
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def _closes(candles: Sequence[Candle]) -> List[float]:
    return [float(row["close"]) for row in candles]


def _signal(strategy: str, symbol: str, signal: str, calc: Dict[str, Any], *, ready: bool = True) -> Dict[str, Any]:
    names = dict(STRATEGIES)
    return {
        "strategy": strategy,
        "name": names.get(strategy, strategy),
        "symbol": symbol,
        "signal": signal,
        "ready": ready,
        "calc": calc,
    }


def eval_trend(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    closes = _closes(candles)
    fast = sma(closes, 10)
    slow = sma(closes, 30)
    if fast is None or slow is None:
        return _signal("trend", symbol, "flat", {"reason": "need_30_bars"}, ready=False)
    last = closes[-1]
    signal = "long" if fast > slow and last > slow else "flat"
    return _signal("trend", symbol, signal, {
        "close": round(last, 8),
        "sma_fast": round(fast, 8),
        "sma_slow": round(slow, 8),
        "fast_minus_slow": round(fast - slow, 8),
    })


def eval_momentum(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    if len(candles) < 21:
        return _signal("momentum", symbol, "flat", {"reason": "need_21_bars"}, ready=False)
    closes = _closes(candles)
    start = closes[-11]
    ret = (closes[-1] - start) / start * 100.0 if start else 0.0
    volumes = [float(row.get("volume") or 0) for row in candles]
    base = volumes[-21:-1]
    avg = mean(base) if base else 0.0
    last_vol = volumes[-1]
    ratio = (last_vol / avg) if avg else 0.0
    signal = "long" if ret >= 1.5 and ratio >= 1.5 else "flat"
    return _signal("momentum", symbol, signal, {
        "return_10_pct": round(ret, 3),
        "volume_ratio": round(ratio, 3),
        "need_return_pct": 1.5,
        "need_volume_ratio": 1.5,
    })


def eval_breakout(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    if len(candles) < 21:
        return _signal("breakout", symbol, "flat", {"reason": "need_21_bars"}, ready=False)
    prior = [float(row["high"]) for row in candles[-21:-1]]
    ceiling = max(prior) if prior else 0.0
    close = float(candles[-1]["close"])
    signal = "long" if ceiling > 0 and close > ceiling else "flat"
    return _signal("breakout", symbol, signal, {
        "close": round(close, 8),
        "prior_high": round(ceiling, 8),
        "break_pct": round((close - ceiling) / ceiling * 100.0, 3) if ceiling else None,
    })


def eval_swing(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    closes = _closes(candles)
    slow = sma(closes, 20)
    fast = sma(closes, 5)
    if slow is None or fast is None:
        return _signal("swing", symbol, "flat", {"reason": "need_20_bars"}, ready=False)
    last = closes[-1]
    signal = "long" if last > slow and fast > slow else "flat"
    return _signal("swing", symbol, signal, {
        "close": round(last, 8),
        "sma_5": round(fast, 8),
        "sma_20": round(slow, 8),
    })


def eval_range(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    if len(candles) < 20:
        return _signal("range", symbol, "flat", {"reason": "need_20_bars"}, ready=False)
    window = list(candles[-20:])
    low = min(float(row["low"]) for row in window)
    high = max(float(row["high"]) for row in window)
    close = float(candles[-1]["close"])
    width = (high - low) / low * 100.0 if low else 0.0
    span = high - low
    pos = (close - low) / span if span else 0.5
    if width < 1.0:
        signal = "flat"
    elif pos <= 0.15:
        signal = "long"
    elif pos >= 0.85:
        signal = "sell"
    else:
        signal = "flat"
    return _signal("range", symbol, signal, {
        "support": round(low, 8),
        "resistance": round(high, 8),
        "close": round(close, 8),
        "band_pct": round(width, 3),
        "position": round(pos, 3),
    })


def eval_scalp(symbol: str, *, bid: float, ask: float, touch_usd: float, notional_usd: float) -> Dict[str, Any]:
    if bid <= 0 or ask <= 0 or ask < bid:
        return _signal("scalp", symbol, "flat", {"reason": "no_book"}, ready=False)
    mid = (bid + ask) / 2.0
    spread_bps = (ask - bid) / mid * 10000.0
    if spread_bps >= 8.0 and touch_usd >= notional_usd:
        signal = "long"
        reason = "ready"
    elif spread_bps < 8.0:
        signal = "flat"
        reason = "spread_too_tight"
    else:
        signal = "flat"
        reason = "book_too_thin"
    return _signal("scalp", symbol, signal, {
        "bid": round(bid, 8),
        "ask": round(ask, 8),
        "spread_bps": round(spread_bps, 2),
        "touch_usd": round(touch_usd, 2),
        "need_spread_bps": 8.0,
        "need_touch_usd": notional_usd,
        "reason": reason,
    })


def eval_reversal(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    value = rsi(_closes(candles), 14)
    if value is None:
        return _signal("reversal", symbol, "flat", {"reason": "need_15_bars"}, ready=False)
    if value <= 30:
        signal = "long"
    elif value >= 70:
        signal = "sell"
    else:
        signal = "flat"
    return _signal("reversal", symbol, signal, {"rsi_14": value, "oversold": 30, "overbought": 70})


def eval_news(symbol: str, candles: Sequence[Candle]) -> Dict[str, Any]:
    closes = _closes(candles)
    if len(closes) < 22:
        return _signal("news", symbol, "flat", {"reason": "need_22_bars"}, ready=False)
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
    if len(rets) < 21:
        return _signal("news", symbol, "flat", {"reason": "need_returns"}, ready=False)
    last = rets[-1]
    sigma = pstdev(rets[-21:-1]) if len(rets[-21:-1]) > 1 else 0.0
    if sigma:
        z = last / sigma
    elif last > 0:
        z = 999.0
    elif last < 0:
        z = -999.0
    else:
        z = 0.0
    signal = "long" if z >= 2.5 else ("sell" if z <= -2.5 else "flat")
    return _signal("news", symbol, signal, {
        "last_return_pct": round(last * 100.0, 3),
        "sigma_pct": round(sigma * 100.0, 3),
        "z": round(z, 2),
        "shock_z": 2.5,
        "headline_feed": False,
    })


def eval_gap(symbol: str, daily: Sequence[Candle]) -> Dict[str, Any]:
    if len(daily) < 2:
        return _signal("gap", symbol, "flat", {"reason": "need_2_days"}, ready=False)
    prev_close = float(daily[-2]["close"])
    today_open = float(daily[-1]["open"])
    if prev_close <= 0:
        return _signal("gap", symbol, "flat", {"reason": "bad_close"}, ready=False)
    gap_pct = (today_open - prev_close) / prev_close * 100.0
    if gap_pct >= 0.5:
        signal = "sell"
    elif gap_pct <= -0.5:
        signal = "long"
    else:
        signal = "flat"
    return _signal("gap", symbol, signal, {
        "prev_close": round(prev_close, 8),
        "open": round(today_open, 8),
        "gap_pct": round(gap_pct, 3),
        "fade_threshold_pct": 0.5,
    })


def eval_pairs(left: str, right: str, left_candles: Sequence[Candle], right_candles: Sequence[Candle]) -> Dict[str, Any]:
    n = min(len(left_candles), len(right_candles))
    if n < 22:
        return _signal("pairs", f"{left}/{right}", "flat", {"reason": "need_22_bars"}, ready=False)
    a = _closes(left_candles[-n:])
    b = _closes(right_candles[-n:])
    spreads = []
    for i in range(1, n):
        if a[i - 1] <= 0 or b[i - 1] <= 0:
            continue
        spreads.append((a[i] / a[i - 1]) - (b[i] / b[i - 1]))
    if len(spreads) < 21:
        return _signal("pairs", f"{left}/{right}", "flat", {"reason": "need_spreads"}, ready=False)
    sigma = pstdev(spreads[:-1]) if len(spreads) > 2 else 0.0
    last = spreads[-1]
    if sigma:
        z = last / sigma
    elif last > 0:
        z = 999.0
    elif last < 0:
        z = -999.0
    else:
        z = 0.0
    if z >= 2.0:
        signal = "sell"
        cheap, rich = right, left
    elif z <= -2.0:
        signal = "long"
        cheap, rich = left, right
    else:
        signal = "flat"
        cheap, rich = left, right
    return _signal("pairs", f"{left}/{right}", signal, {
        "z": round(z, 2),
        "spread": round(last, 6),
        "sigma": round(sigma, 6),
        "cheap": cheap,
        "rich": rich,
        "entry_z": 2.0,
    })


def _parse_klines(rows: Any) -> List[Candle]:
    out: List[Candle] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        try:
            candle = {
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
            try:
                candle["open_time"] = int(row[0])
            except (TypeError, ValueError):
                pass
            out.append(candle)
        except (TypeError, ValueError):
            continue
    return out


def fetch_klines(symbol: str, interval: str, limit: int = 80) -> List[Candle]:
    pair = f"{str(symbol).upper()}USDC"
    params = {"symbol": pair, "interval": interval, "limit": int(limit)}
    for url in _KLINE_URLS:
        try:
            resp = requests.get(url, params=params, timeout=5, headers={"User-Agent": "masternoder-strategies/1.0"})
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        try:
            candles = _parse_klines(resp.json())
        except ValueError:
            continue
        if candles:
            return candles
    return []


def run_strategies(
    market: Dict[str, Dict[str, Any]],
    *,
    notional_usd: float = 25.0,
    strategy_notional: Optional[Dict[str, float]] = None,
    enabled: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Evaluate the ten strategies on an in-memory market. No orders."""
    wanted = set(enabled) if enabled is not None else {key for key, _name in STRATEGIES}
    clips = dict(strategy_notional or {})
    rows: List[Dict[str, Any]] = []
    symbols = [sym for sym in FAST_USDT_COINS if sym in market]

    def _keep(row: Dict[str, Any]) -> None:
        row["notional_usd"] = float(clips.get(str(row.get("strategy") or "")) or notional_usd)
        rows.append(row)

    def candles_of(sym: str, key: str = "hourly") -> List[Candle]:
        raw = (market.get(sym) or {}).get(key) or []
        return list(raw)

    for sym in symbols:
        hourly = candles_of(sym, "hourly")
        daily = candles_of(sym, "daily")
        book = market.get(sym) or {}
        if "trend" in wanted:
            _keep(eval_trend(sym, hourly))
        if "momentum" in wanted:
            _keep(eval_momentum(sym, hourly))
        if "breakout" in wanted:
            _keep(eval_breakout(sym, hourly))
        if "swing" in wanted:
            _keep(eval_swing(sym, hourly))
        if "range" in wanted:
            _keep(eval_range(sym, hourly))
        if "scalp" in wanted:
            _keep(eval_scalp(
                sym,
                bid=float(book.get("bid") or 0),
                ask=float(book.get("ask") or 0),
                touch_usd=float(book.get("touch_usd") or 0),
                notional_usd=float(clips.get("scalp") or notional_usd),
            ))
        if "reversal" in wanted:
            _keep(eval_reversal(sym, hourly))
        if "news" in wanted:
            _keep(eval_news(sym, hourly))
        if "gap" in wanted:
            _keep(eval_gap(sym, daily))
    if "pairs" in wanted and len(symbols) >= 2:
        for i, left in enumerate(symbols):
            for right in symbols[i + 1:]:
                _keep(eval_pairs(left, right, candles_of(left), candles_of(right)))
    actionable = [row for row in rows if row.get("ready") and row.get("signal") in ("long", "sell")]
    return {
        "success": True,
        "strategies": [key for key, _name in STRATEGIES],
        "notional_usd": notional_usd,
        "rows": rows,
        "actionable": len(actionable),
        "signals": actionable,
    }


def _apply_book(market: Dict[str, Dict[str, Any]], book_report: Optional[Dict[str, Any]]) -> None:
    for coin in (book_report or {}).get("coins") or []:
        sym = str(coin.get("symbol") or "")
        if sym not in market:
            continue
        touch = 0.0
        for direction in coin.get("directions") or []:
            if str(direction.get("route") or "").startswith("binance"):
                touch = float(direction.get("touch_usd") or 0)
        market[sym]["bid"] = float(coin.get("binance_bid") or 0)
        market[sym]["ask"] = float(coin.get("binance_ask") or 0)
        market[sym]["touch_usd"] = touch


def _load_symbol(symbol: str) -> Tuple[str, Dict[str, Any]]:
    return symbol, {
        "hourly": fetch_klines(symbol, "1h", 60),
        "daily": fetch_klines(symbol, "1d", 10),
        "bid": 0.0,
        "ask": 0.0,
        "touch_usd": 0.0,
    }


def search_strategies(book_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch candles, score all ten strategies, and place no order."""
    cfg = load_config()
    symbols = [sym for sym in cfg["symbols"] if sym in FAST_USDT_COINS]
    market: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_load_symbol, sym) for sym in symbols]
        for fut in as_completed(futures):
            try:
                sym, payload = fut.result()
            except Exception:
                continue
            market[sym] = payload
    books = book_report if book_report is not None else search_fast_books(
        notional_usd=float(cfg["notional_usd"]), min_net_bps=0.0,
    )
    _apply_book(market, books)
    report = run_strategies(
        market,
        notional_usd=float(cfg["notional_usd"]),
        strategy_notional=cfg.get("strategy_notional"),
        enabled=cfg["strategies"],
    )
    scores = cfg.get("strategy_score_pct") or {}
    report["strategy_score_pct"] = scores
    report["max_orders"] = int(cfg.get("max_orders") or 10)
    report["reentry_minutes"] = float(cfg.get("reentry_minutes") or REENTRY_MINUTES)
    if cfg["execute"]:
        report["orders"] = signal_orders(tradable_rows(report["rows"], scores), max_orders=report["max_orders"])
    else:
        report["orders"] = select_strategy_orders(report["rows"], scores, max_orders=report["max_orders"])
    report["best"] = [key for key, _score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if _score > 0]
    report["skipped_minus"] = [key for key, _score in scores.items() if _score < 0]
    report["execute"] = bool(cfg["execute"])
    report["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return report


def format_strategy_block(report: Dict[str, Any]) -> str:
    lines = [
        f"{report.get('ts')} strategies={len(STRATEGIES)} "
        f"actionable={report.get('actionable')} execute={bool(report.get('execute'))} "
        f"clip=${float(report.get('notional_usd') or 0):.2f}"
    ]
    for key, name in STRATEGIES:
        picked = [row for row in (report.get("rows") or []) if row.get("strategy") == key and row.get("ready")]
        if not picked:
            lines.append(f"{key} {name} no_data")
            continue
        best = max(picked, key=lambda row: (row.get("signal") != "flat", abs(float((row.get("calc") or {}).get("z") or (row.get("calc") or {}).get("gap_pct") or (row.get("calc") or {}).get("return_10_pct") or 0))))
        calc = best.get("calc") or {}
        detail = calc.get("z", calc.get("rsi_14", calc.get("gap_pct", calc.get("spread_bps", calc.get("return_10_pct", calc.get("fast_minus_slow", ""))))))
        clip = float(best.get("notional_usd") or report.get("notional_usd") or 0)
        lines.append(f"{key} {name} {best.get('symbol')} {best.get('signal')} {detail} clip=${clip:.2f}")
    best = ",".join(report.get("best") or []) or "none"
    skipped = ",".join(report.get("skipped_minus") or []) or "none"
    lines.append(
        f"orders selected={len(report.get('orders') or [])} sent={len(report.get('sent') or [])} "
        f"best={best} skipped_minus={skipped}"
    )
    return "\n".join(lines) + "\n"


def write_strategy_logs(report: Dict[str, Any], *, root: Optional[str] = None) -> Dict[str, Any]:
    paths = search_log_paths(root)
    paths = {
        "dir": paths["dir"],
        "jsonl": os.path.join(paths["dir"], "strategies.jsonl"),
        "calculations": os.path.join(paths["dir"], "strategies.log"),
        "latest": os.path.join(paths["dir"], "strategies_latest.json"),
    }
    try:
        os.makedirs(paths["dir"], exist_ok=True)
        with open(paths["jsonl"], "a", encoding="utf-8") as handle:
            handle.write(json.dumps(report, default=str) + "\n")
        with open(paths["calculations"], "a", encoding="utf-8") as handle:
            handle.write(format_strategy_block(report))
        with open(paths["latest"], "w", encoding="utf-8") as handle:
            json.dump(report, handle, default=str)
            handle.write("\n")
    except OSError as exc:
        return {"ok": False, "error": str(exc), **paths}
    return {"ok": True, **paths}
