"""Live Binance bookTicker feed → Redis/file bus.

The one-minute ladder tick reads mids from here when they are fresher than
``max_age_sec`` (default 3s). NonKYC has no public WS for these pairs, so its
quotes still come from REST; Binance is the pricing anchor either way.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Iterable, List, Optional

from backend.services.exchange_redis_bus import bus_get, bus_set

DEFAULT_SYMBOLS = ("XRP", "ALGO", "XLM", "TRX", "SOL", "DOGE", "ADA")
QUOTE = "USDC"
WS_URLS = (
    "wss://stream.binance.com:9443/stream?streams={streams}",
    "wss://data-stream.binance.vision/stream?streams={streams}",
)
REST_BOOK_URLS = (
    "https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol={pair}",
    "https://api.binance.com/api/v3/ticker/bookTicker?symbol={pair}",
)
FEED_MAX_AGE = 3.0
REST_POLL_SEC = 1.0


def stream_name(symbol: str, quote: str = QUOTE) -> str:
    return f"{symbol.lower()}{quote.lower()}@bookTicker"


def feed_key(symbol: str) -> str:
    return f"mid:{str(symbol).upper()}"


def publish_top(symbol: str, bid: float, ask: float, *, source: str = "binance_ws") -> str:
    mid = (bid + ask) / 2.0
    return bus_set(
        feed_key(symbol),
        {"bid": bid, "ask": ask, "mid": mid, "quote": QUOTE, "source": source, "pair": f"{symbol}{QUOTE}"},
        ttl_sec=30,
    )


def cached_top(symbol: str, *, max_age_sec: float = FEED_MAX_AGE) -> Optional[Dict[str, float]]:
    row = bus_get(feed_key(symbol), max_age_sec=max_age_sec)
    if not isinstance(row, dict):
        return None
    try:
        bid, ask = float(row["bid"]), float(row["ask"])
    except (KeyError, TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0:
        return None
    out = {"bid": bid, "ask": ask, "quote": row.get("quote") or QUOTE, "pair": row.get("pair") or f"{symbol}{QUOTE}"}
    if row.get("source"):
        out["source"] = str(row["source"])
    return out


def feed_status(symbols: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    from backend.services.exchange_redis_bus import backend_name, bus_get_meta

    now = time.time()
    rows = {}
    for symbol in symbols or DEFAULT_SYMBOLS:
        meta = bus_get_meta(feed_key(symbol))
        if not meta:
            rows[symbol] = {"ok": False}
            continue
        rows[symbol] = {
            "ok": True,
            "age_sec": round(now - float(meta["ts"]), 3),
            "backend": meta.get("backend"),
            "value": meta.get("value"),
        }
    return {"backend": backend_name(), "symbols": rows}


def _poll_rest_once(symbols: List[str], *, on_tick=None) -> int:
    """One REST sweep through the vision/main hosts. Returns published count."""
    import urllib.request

    published = 0
    for symbol in symbols:
        pair = f"{symbol}{QUOTE}"
        body = None
        for template in REST_BOOK_URLS:
            try:
                with urllib.request.urlopen(template.format(pair=pair), timeout=3) as resp:
                    body = json.loads(resp.read().decode())
                break
            except Exception:
                body = None
        if not isinstance(body, dict):
            continue
        try:
            bid = float(body.get("bidPrice") or 0)
            ask = float(body.get("askPrice") or 0)
        except (TypeError, ValueError):
            continue
        if bid <= 0 or ask <= 0:
            continue
        backend = publish_top(symbol, bid, ask, source="binance_rest")
        published += 1
        if on_tick:
            on_tick(symbol, bid, ask, backend)
    return published


async def _run_ws(symbols: List[str], *, url: str, on_tick=None) -> None:
    import websockets

    async with websockets.connect(url, ping_interval=20, ping_timeout=20, max_queue=1024) as ws:
        async for message in ws:
            try:
                payload = json.loads(message)
            except Exception:
                continue
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                continue
            pair = str(data.get("s") or "")
            if not pair.endswith(QUOTE):
                continue
            symbol = pair[: -len(QUOTE)]
            try:
                bid = float(data.get("b") or 0)
                ask = float(data.get("a") or 0)
            except (TypeError, ValueError):
                continue
            if bid <= 0 or ask <= 0:
                continue
            backend = publish_top(symbol, bid, ask)
            if on_tick:
                on_tick(symbol, bid, ask, backend)


def run_feed_forever(symbols: Optional[List[str]] = None, *, reconnect_sec: float = 2.0) -> None:
    """Blocking loop used by ``scripts/run_exchange_market_feed.py``.

    Tries Binance websocket hosts first. Regions that get HTTP 451 fall back to
    a 1s REST poll against ``data-api.binance.vision``.
    """
    symbols = [str(s).upper() for s in (symbols or list(DEFAULT_SYMBOLS))]
    streams = "/".join(stream_name(s) for s in symbols)
    ws_failures = 0
    while True:
        if ws_failures < 3:
            for template in WS_URLS:
                url = template.format(streams=streams)
                try:
                    print(f"[market-feed] websocket {url.split('?')[0]}", flush=True)
                    asyncio.run(_run_ws(symbols, url=url))
                    ws_failures = 0
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    ws_failures += 1
                    print(f"[market-feed] ws failed ({ws_failures}): {exc}", flush=True)
                    time.sleep(reconnect_sec)
        print(f"[market-feed] REST poll every {REST_POLL_SEC}s", flush=True)
        try:
            while True:
                n = _poll_rest_once(symbols)
                if n == 0:
                    time.sleep(reconnect_sec)
                else:
                    time.sleep(REST_POLL_SEC)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"[market-feed] rest poll error: {exc}", flush=True)
            time.sleep(reconnect_sec)
            ws_failures = 0


def prefer_cached_binance_top(symbol: str, fallback, *, max_age_sec: float = FEED_MAX_AGE):
    """Return the WS mid when fresh, otherwise call ``fallback(symbol)`` (REST)."""
    hit = cached_top(symbol, max_age_sec=max_age_sec)
    if hit:
        return hit
    return fallback(symbol)
