"""Read-only connectors to external exchanges (public market data only).

Phase 1 fetches public best bid/ask/last for supported symbols across 25+ venues
and normalizes them to a common shape. No API keys, no account access, no order placement.
Live trading is gated separately (see exchange_arbitrage_service + EXCHANGE_ARBITRAGE_LIVE).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONNECTORS_PATH = os.path.join(ex._BASE, "data", "exchange_connectors_config.json")
_PRICE_CACHE_PATH = os.path.join(ex._DATA_DIR, "external_prices.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_connectors_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _venue_map(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    cfg = cfg or load_connectors_config()
    out: Dict[str, Dict[str, Any]] = {}
    for v in cfg.get("venues") or []:
        if isinstance(v, dict) and v.get("id"):
            out[str(v["id"])] = v
    return out


def venue_quote(venue_id: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    """Spot quote asset for a venue (e.g. USDC on EEA Binance, USDT on NonKYC)."""
    venue = _venue_map(cfg).get(venue_id) or {}
    return str(venue.get("quote") or "USDT").upper()


def build_pair(venue: Dict[str, Any], base: str) -> str:
    base = str(base).upper()
    base = (venue.get("base_overrides") or {}).get(base, base)
    quote = str(venue.get("quote") or "USDT")
    pair = str(venue.get("pair_template") or "{base}{quote}").format(base=base, quote=quote)
    if venue.get("lowercase_pair"):
        pair = pair.lower()
    return pair


def _f(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _norm(bid: Any, ask: Any, last: Any = None) -> Optional[Dict[str, float]]:
    b, a = _f(bid), _f(ask)
    last_v = _f(last) if last is not None else 0.0
    if b <= 0 and a <= 0 and last_v <= 0:
        return None
    if last_v <= 0:
        last_v = (b + a) / 2 if b > 0 and a > 0 else (b or a)
    return {"bid": b, "ask": a, "last": round(last_v, 12)}


# Per-venue response parsers. Each takes the decoded JSON and returns normalized dict or None.
def _p_binance(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bidPrice"), j.get("askPrice"))


def _p_coinbase(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("price"))


def _p_kraken(j: Any) -> Optional[Dict[str, float]]:
    result = (j or {}).get("result") or {}
    if not result:
        return None
    row = next(iter(result.values()))
    return _norm(row.get("b", [0])[0], row.get("a", [0])[0], row.get("c", [0])[0])


def _p_nonkyc(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("last_price"))


def _p_kucoin(j: Any) -> Optional[Dict[str, float]]:
    d = (j or {}).get("data") or {}
    return _norm(d.get("bestBid"), d.get("bestAsk"), d.get("price"))


def _p_okx(j: Any) -> Optional[Dict[str, float]]:
    rows = (j or {}).get("data") or []
    if not rows:
        return None
    d = rows[0]
    return _norm(d.get("bidPx"), d.get("askPx"), d.get("last"))


def _p_bybit(j: Any) -> Optional[Dict[str, float]]:
    rows = ((j or {}).get("result") or {}).get("list") or []
    if not rows:
        return None
    d = rows[0]
    return _norm(d.get("bid1Price"), d.get("ask1Price"), d.get("lastPrice"))


def _p_bitfinex(j: Any) -> Optional[Dict[str, float]]:
    if not isinstance(j, list) or len(j) < 7:
        return None
    return _norm(j[0], j[2], j[6])


def _p_gateio(j: Any) -> Optional[Dict[str, float]]:
    if isinstance(j, list):
        if not j:
            return None
        d = j[0]
    else:
        d = j
    return _norm(d.get("highest_bid"), d.get("lowest_ask"), d.get("last"))


def _p_bitstamp(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("last"))


def _p_cryptocom(j: Any) -> Optional[Dict[str, float]]:
    data = ((j or {}).get("result") or {}).get("data")
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]
    if not isinstance(data, dict):
        return None
    return _norm(data.get("b"), data.get("k"), data.get("a"))


def _p_mexc(j: Any) -> Optional[Dict[str, float]]:
    if isinstance(j, list) and j:
        j = j[0]
    if not isinstance(j, dict):
        return None
    return _norm(j.get("bidPrice"), j.get("askPrice"))


def _p_bitget(j: Any) -> Optional[Dict[str, float]]:
    rows = ((j or {}).get("data") or [])
    if isinstance(rows, list) and rows:
        d = rows[0]
    elif isinstance(rows, dict):
        d = rows
    else:
        return None
    return _norm(d.get("bidPr") or d.get("buyOne"), d.get("askPr") or d.get("sellOne"), d.get("lastPr"))


def _p_htx(j: Any) -> Optional[Dict[str, float]]:
    tick = (j or {}).get("tick") or {}
    return _norm(tick.get("bid"), tick.get("ask"), tick.get("close"))


def _p_gemini(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("last"))


def _p_bingx(j: Any) -> Optional[Dict[str, float]]:
    d = (j or {}).get("data") or j
    if isinstance(d, list) and d:
        d = d[0]
    return _norm(d.get("bidPrice"), d.get("askPrice"))


def _p_poloniex(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("close"))


def _p_bitmart(j: Any) -> Optional[Dict[str, float]]:
    d = (j or {}).get("data") or {}
    return _norm(d.get("bid_px"), d.get("ask_px"), d.get("last"))


def _p_coinex(j: Any) -> Optional[Dict[str, float]]:
    d = ((j or {}).get("data") or {}).get("ticker") or {}
    return _norm(d.get("buy"), d.get("sell"), d.get("last"))


def _p_lbank(j: Any) -> Optional[Dict[str, float]]:
    d = ((j or {}).get("data") or {}).get("ticker") or (j or {}).get("ticker") or {}
    return _norm(d.get("buy"), d.get("sell"), d.get("latest"))


def _p_whitebit(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("last_price") or j.get("last"))


def _p_upbit(j: Any) -> Optional[Dict[str, float]]:
    if not isinstance(j, list) or not j:
        return None
    units = (j[0] or {}).get("orderbook_units") or []
    if not units:
        return None
    u = units[0]
    return _norm(u.get("bid_price"), u.get("ask_price"))


def _p_xt(j: Any) -> Optional[Dict[str, float]]:
    rows = (j or {}).get("result") or []
    if not rows:
        return None
    d = rows[0]
    return _norm(d.get("bp"), d.get("ap"), d.get("c"))


def _p_bitunix(j: Any) -> Optional[Dict[str, float]]:
    d = (j or {}).get("data") or j
    if isinstance(d, list) and d:
        d = d[0]
    return _norm(d.get("bidPrice") or d.get("bid"), d.get("askPrice") or d.get("ask"), d.get("lastPrice") or d.get("last"))


def _p_phemex(j: Any) -> Optional[Dict[str, float]]:
    d = ((j or {}).get("result") or {})
    if isinstance(d, list) and d:
        d = d[0]
    scale = float(d.get("priceScale") or d.get("price_scale") or 10000)
    bid = _f(d.get("bidEp") or d.get("bid")) / scale if d.get("bidEp") is not None else _f(d.get("bid"))
    ask = _f(d.get("askEp") or d.get("ask")) / scale if d.get("askEp") is not None else _f(d.get("ask"))
    last = _f(d.get("lastEp") or d.get("last")) / scale if d.get("lastEp") is not None else _f(d.get("last"))
    return _norm(bid, ask, last)


def _p_tapbit(j: Any) -> Optional[Dict[str, float]]:
    d = (j or {}).get("data") or j
    if isinstance(d, list) and d:
        d = d[0]
    return _norm(d.get("bidPrice") or d.get("bid"), d.get("askPrice") or d.get("ask"), d.get("lastPrice") or d.get("last"))


def _p_xeggex(j: Any) -> Optional[Dict[str, float]]:
    return _norm(j.get("bid"), j.get("ask"), j.get("last_price"))


_PARSERS: Dict[str, Callable[[Any], Optional[Dict[str, float]]]] = {
    "binance": _p_binance,
    "coinbase": _p_coinbase,
    "kraken": _p_kraken,
    "nonkyc": _p_nonkyc,
    "kucoin": _p_kucoin,
    "okx": _p_okx,
    "bybit": _p_bybit,
    "bitfinex": _p_bitfinex,
    "gateio": _p_gateio,
    "bitstamp": _p_bitstamp,
    "cryptocom": _p_cryptocom,
    "mexc": _p_mexc,
    "bitget": _p_bitget,
    "htx": _p_htx,
    "gemini": _p_gemini,
    "bingx": _p_bingx,
    "poloniex": _p_poloniex,
    "bitmart": _p_bitmart,
    "coinex": _p_coinex,
    "lbank": _p_lbank,
    "whitebit": _p_whitebit,
    "upbit": _p_upbit,
    "xt": _p_xt,
    "bitunix": _p_bitunix,
    "phemex": _p_phemex,
    "tapbit": _p_tapbit,
    "xeggex": _p_xeggex,
}


def fetch_ticker(venue_id: str, base: str, *, timeout: float = 6.0) -> Optional[Dict[str, float]]:
    """Fetch a single normalized ticker from a venue's public endpoint."""
    venue = _venue_map().get(venue_id)
    parser = _PARSERS.get(venue_id)
    if not venue or not parser:
        return None
    try:
        import requests
    except Exception:
        return None
    from backend.services.exchange_http_util import force_ipv4_outbound_if_configured

    force_ipv4_outbound_if_configured()
    pair = build_pair(venue, base)
    url = str(venue.get("ticker_url") or "").format(pair=pair)
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "masternoder-arb/1.0"})
        if resp.status_code != 200:
            return None
        return parser(resp.json())
    except Exception:
        return None


def fetch_prices(
    symbols: Optional[List[str]] = None,
    venues: Optional[List[str]] = None,
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Return {venue_id: {symbol: {bid, ask, last}}} across venues.

    ``injected`` (venue->symbol->{bid,ask,last}) bypasses the network for tests/sims.
    """
    cfg = load_connectors_config()
    symbols = [str(s).upper() for s in (symbols or cfg.get("supported_symbols") or [])]
    vmap = _venue_map(cfg)
    venue_ids = venues or [vid for vid, v in vmap.items() if v.get("enabled", True)]
    timeout = float(cfg.get("request_timeout_sec") or 6)

    if injected is not None:
        prices = {vid: dict(injected.get(vid, {})) for vid in venue_ids}
        return {"success": True, "fetched_at": _iso(), "source": "injected", "prices": prices}

    ttl = float(cfg.get("price_cache_ttl_sec") or 30)
    if use_cache:
        cached = ex._read_json(_PRICE_CACHE_PATH, {})
        if isinstance(cached, dict) and cached.get("fetched_at"):
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(
                    cached["fetched_at"].replace("Z", "+00:00"))).total_seconds()
                if age < ttl and cached.get("prices"):
                    return {**cached, "source": "cache"}
            except Exception:
                pass

    jobs = [(vid, sym) for vid in venue_ids if vid != "internal" and vid in vmap for sym in symbols]
    prices: Dict[str, Dict[str, Dict[str, float]]] = {}

    # Fetch all (venue, symbol) tickers concurrently so a 24/7 tick finishes in seconds.
    try:
        from concurrent.futures import ThreadPoolExecutor

        max_workers = min(32, max(1, len(jobs)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(pool.map(lambda j: (j[0], j[1], fetch_ticker(j[0], j[1], timeout=timeout)), jobs))
        for vid, sym, t in results:
            if t:
                prices.setdefault(vid, {})[sym] = t
    except Exception:
        for vid, sym in jobs:
            t = fetch_ticker(vid, sym, timeout=timeout)
            if t:
                prices.setdefault(vid, {})[sym] = t

    out = {"success": True, "fetched_at": _iso(), "source": "live", "prices": prices}
    try:
        ex._write_json(_PRICE_CACHE_PATH, out)
    except Exception:
        pass
    return out


def list_venues() -> Dict[str, Any]:
    """Public, secret-free description of configured venues."""
    cfg = load_connectors_config()
    venues = []
    for v in cfg.get("venues") or []:
        if not isinstance(v, dict):
            continue
        venues.append({
            "id": v.get("id"),
            "name": v.get("name"),
            "enabled": bool(v.get("enabled", True)),
            "quote": v.get("quote"),
            "fee_taker_bps": v.get("fee_taker_bps"),
            "withdrawal_note": v.get("withdrawal_note"),
        })
    return {
        "success": True,
        "mode": cfg.get("mode", "paper"),
        "live": str(os.environ.get(cfg.get("live_env_flag") or "EXCHANGE_ARBITRAGE_LIVE", "")).strip() == "1",
        "venue_count": len(venues),
        "supported_symbols": cfg.get("supported_symbols") or [],
        "venues": venues,
    }
