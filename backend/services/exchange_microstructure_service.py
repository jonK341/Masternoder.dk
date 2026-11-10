"""Order-book imbalance + mid regime for ladder/maker.

Depth comes from Binance ``@depth5@100ms`` via the market-feed bus. Mid history
is a short ring (Redis list when available, file/json fallback) used to classify
calm / normal / volatile regimes that widen or tighten quote distances.
"""
from __future__ import annotations

import math
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_fast_json import dumps as json_dumps
from backend.services.exchange_fast_json import try_loads as json_try_loads
from backend.services.exchange_redis_bus import bus_get, bus_set, get_client, reset_client

DEPTH_KEY = "depth:{symbol}"
MID_KEY = "mids:{symbol}"
FEED_MAX_AGE = 3.0
MID_MAXLEN = 120
REGIME_MIN_POINTS = 20

# Realized-vol thresholds in bps of mid (over the mid ring).
REGIME_CALM_BPS = 4.0
REGIME_VOLATILE_BPS = 18.0


def depth_key(symbol: str) -> str:
    return DEPTH_KEY.format(symbol=str(symbol).upper())


def mid_key(symbol: str) -> str:
    return MID_KEY.format(symbol=str(symbol).upper())


def _levels_notional(levels: Sequence[Sequence[Any]], n: int = 5) -> Tuple[float, float]:
    """Return (qty_sum, notional_usd) for the first ``n`` book levels."""
    qty = 0.0
    notion = 0.0
    for row in list(levels)[:n]:
        try:
            px = float(row[0])
            q = float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if px <= 0 or q <= 0:
            continue
        qty += q
        notion += px * q
    return qty, notion


def depth_imbalance(
    bids: Sequence[Sequence[Any]],
    asks: Sequence[Sequence[Any]],
    *,
    levels: int = 5,
) -> float:
    """+1 = bid-heavy (buy pressure), -1 = ask-heavy. Uses top-N notional."""
    _bq, bid_n = _levels_notional(bids, levels)
    _aq, ask_n = _levels_notional(asks, levels)
    total = bid_n + ask_n
    if total <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, (bid_n - ask_n) / total))


def publish_depth(
    symbol: str,
    bids: Sequence[Sequence[Any]],
    asks: Sequence[Sequence[Any]],
    *,
    source: str = "binance_depth",
    levels: int = 5,
) -> str:
    imb = depth_imbalance(bids, asks, levels=levels)
    bid_q, bid_n = _levels_notional(bids, levels)
    ask_q, ask_n = _levels_notional(asks, levels)
    top_bid = float(bids[0][0]) if bids else 0.0
    top_ask = float(asks[0][0]) if asks else 0.0
    return bus_set(
        depth_key(symbol),
        {
            "imbalance": round(imb, 6),
            "bid_qty": round(bid_q, 8),
            "ask_qty": round(ask_q, 8),
            "bid_usd": round(bid_n, 4),
            "ask_usd": round(ask_n, 4),
            "bid": top_bid,
            "ask": top_ask,
            "levels": levels,
            "source": source,
        },
        ttl_sec=15,
    )


def cached_depth(symbol: str, *, max_age_sec: float = FEED_MAX_AGE) -> Optional[Dict[str, Any]]:
    row = bus_get(depth_key(symbol), max_age_sec=max_age_sec)
    return row if isinstance(row, dict) else None


def cached_imbalance(symbol: str, *, max_age_sec: float = FEED_MAX_AGE) -> float:
    row = cached_depth(symbol, max_age_sec=max_age_sec) or {}
    try:
        return float(row.get("imbalance") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _mid_file(symbol: str) -> str:
    return os.path.join(ex._BASE, "data", "crypto_exchange", "bus", f"mids__{symbol.upper()}.json")


def push_mid(symbol: str, mid: float, *, maxlen: int = MID_MAXLEN) -> str:
    """Append a mid sample. Redis list when available; otherwise a JSON ring file."""
    sym = str(symbol).upper()
    px = float(mid)
    if px <= 0:
        return "skip"
    client = get_client()
    key = "mn:xchg:" + mid_key(sym)
    if client is not None:
        try:
            # msgpack keeps the list compact when the codec is installed.
            try:
                import msgpack

                blob = msgpack.packb({"t": time.time(), "m": px}, use_bin_type=True)
            except Exception:
                blob = json_dumps({"t": time.time(), "m": px}).encode("utf-8")
            pipe = client.pipeline()
            pipe.lpush(key, blob)
            pipe.ltrim(key, 0, int(maxlen) - 1)
            pipe.expire(key, 3600)
            pipe.execute()
            return "redis"
        except Exception:
            reset_client()
    path = _mid_file(sym)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = []
    if os.path.isfile(path):
        raw = json_try_loads(open(path, encoding="utf-8").read(), default=[])
        if isinstance(raw, list):
            rows = raw
    rows.insert(0, {"t": time.time(), "m": px})
    rows = rows[: int(maxlen)]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json_dumps(rows) + "\n")
    return "file"


def _load_mids(symbol: str, *, limit: int = MID_MAXLEN) -> List[float]:
    sym = str(symbol).upper()
    client = get_client()
    key = "mn:xchg:" + mid_key(sym)
    if client is not None:
        try:
            blobs = client.lrange(key, 0, int(limit) - 1) or []
            out: List[float] = []
            for blob in blobs:
                row = None
                try:
                    import msgpack

                    row = msgpack.unpackb(blob, raw=False)
                except Exception:
                    row = json_try_loads(blob)
                if isinstance(row, dict) and row.get("m") is not None:
                    out.append(float(row["m"]))
            if out:
                return out
        except Exception:
            reset_client()
    path = _mid_file(sym)
    if not os.path.isfile(path):
        return []
    raw = json_try_loads(open(path, encoding="utf-8").read(), default=[])
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw[: int(limit)]:
        if isinstance(row, dict) and row.get("m") is not None:
            out.append(float(row["m"]))
    return out


def realized_vol_bps(mids: Sequence[float]) -> float:
    if len(mids) < 2:
        return 0.0
    # mids are newest-first; reverse for chronological returns.
    series = list(reversed([float(x) for x in mids if float(x) > 0]))
    if len(series) < 2:
        return 0.0
    rets = []
    for a, b in zip(series, series[1:]):
        if a <= 0:
            continue
        rets.append((b - a) / a * 1e4)
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
    return float(math.sqrt(max(0.0, var)))


def regime_for(symbol: str, *, mids: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    samples = list(mids) if mids is not None else _load_mids(symbol)
    vol = realized_vol_bps(samples)
    if len(samples) < REGIME_MIN_POINTS:
        state = "unknown"
    elif vol <= REGIME_CALM_BPS:
        state = "calm"
    elif vol >= REGIME_VOLATILE_BPS:
        state = "volatile"
    else:
        state = "normal"
    return {
        "symbol": str(symbol).upper(),
        "state": state,
        "vol_bps": round(vol, 4),
        "n": len(samples),
    }


def blend_skew(inventory_skew: float, imbalance: float, *, weight: float = 0.3) -> float:
    """Mix inventory skew with book imbalance (both in [-1, 1])."""
    w = max(0.0, min(1.0, float(weight)))
    raw = (1.0 - w) * float(inventory_skew) + w * float(imbalance)
    return max(-1.0, min(1.0, raw))


def regime_distance_mult(state: str) -> float:
    if state == "calm":
        return 0.92
    if state == "volatile":
        return 1.18
    return 1.0


def maker_edge_bps(base_edge_bps: float, side: str, imbalance: float) -> float:
    """Bid-heavy book → slightly tighter buys / wider sells (and the reverse)."""
    edge = float(base_edge_bps)
    imb = max(-1.0, min(1.0, float(imbalance)))
    if str(side).lower() == "buy":
        return max(1.0, edge * (1.0 - 0.25 * imb))
    return max(1.0, edge * (1.0 + 0.25 * imb))


def apply_regime_to_cfg(cfg: Dict[str, Any], *, symbol: str) -> Dict[str, Any]:
    out = dict(cfg)
    regime = regime_for(symbol)
    mult = regime_distance_mult(str(regime.get("state") or "normal"))
    out["first_bps"] = float(out.get("first_bps") or 30.0) * mult
    out["step_bps"] = float(out.get("step_bps") or 40.0) * mult
    out["_regime"] = regime
    out["_regime_mult"] = mult
    return out


def microstructure_status(symbols: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    from backend.services.exchange_market_feed_service import DEFAULT_SYMBOLS

    rows = {}
    for symbol in symbols or DEFAULT_SYMBOLS:
        depth = cached_depth(symbol, max_age_sec=10.0) or {}
        rows[symbol] = {
            "imbalance": depth.get("imbalance"),
            "regime": regime_for(symbol),
            "depth_ok": bool(depth),
        }
    pack = {"msgpack": False, "cachetools": False}
    try:
        import msgpack

        pack["msgpack"] = True
        pack["msgpack_version"] = ".".join(str(x) for x in msgpack.version)
    except Exception:
        pass
    try:
        import cachetools

        pack["cachetools"] = True
        pack["cachetools_version"] = getattr(cachetools, "__version__", "?")
    except Exception:
        pass
    return {"pack": pack, "symbols": rows}
