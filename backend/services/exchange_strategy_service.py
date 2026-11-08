"""Ten spot strategies for the fast-coin daemon.

Each pass scores XRP, XLM, ALGO, TRX, and SOL and writes the calculation.
Signals are ready to read. ``execute`` stays false, so a signal does not
place an order. The cross-venue limit path remains the only order path.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_cross_trade_service import FAST_USDT_COINS, search_fast_books, search_log_paths

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
    return base


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
            out.append({
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
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
    enabled: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Evaluate the ten strategies on an in-memory market. No orders."""
    wanted = set(enabled) if enabled is not None else {key for key, _name in STRATEGIES}
    rows: List[Dict[str, Any]] = []
    symbols = [sym for sym in FAST_USDT_COINS if sym in market]

    def candles_of(sym: str, key: str = "hourly") -> List[Candle]:
        raw = (market.get(sym) or {}).get(key) or []
        return list(raw)

    for sym in symbols:
        hourly = candles_of(sym, "hourly")
        daily = candles_of(sym, "daily")
        book = market.get(sym) or {}
        if "trend" in wanted:
            rows.append(eval_trend(sym, hourly))
        if "momentum" in wanted:
            rows.append(eval_momentum(sym, hourly))
        if "breakout" in wanted:
            rows.append(eval_breakout(sym, hourly))
        if "swing" in wanted:
            rows.append(eval_swing(sym, hourly))
        if "range" in wanted:
            rows.append(eval_range(sym, hourly))
        if "scalp" in wanted:
            rows.append(eval_scalp(
                sym,
                bid=float(book.get("bid") or 0),
                ask=float(book.get("ask") or 0),
                touch_usd=float(book.get("touch_usd") or 0),
                notional_usd=notional_usd,
            ))
        if "reversal" in wanted:
            rows.append(eval_reversal(sym, hourly))
        if "news" in wanted:
            rows.append(eval_news(sym, hourly))
        if "gap" in wanted:
            rows.append(eval_gap(sym, daily))
    if "pairs" in wanted and len(symbols) >= 2:
        for i, left in enumerate(symbols):
            for right in symbols[i + 1:]:
                rows.append(eval_pairs(left, right, candles_of(left), candles_of(right)))
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
    report = run_strategies(market, notional_usd=float(cfg["notional_usd"]), enabled=cfg["strategies"])
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
        lines.append(f"{key} {name} {best.get('symbol')} {best.get('signal')} {detail}")
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
