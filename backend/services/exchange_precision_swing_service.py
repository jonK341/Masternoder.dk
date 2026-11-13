"""Precision level swing — systematic TA with disciplined price levels.

This is the named profile for: systematic technical analysis + trend
prediction + repeatable swing rules at precision S/R / pivot levels.

Computes classic floor-trader levels (floor pivots + recent swing high/low)
and posts them for grid/latch discipline — not discretionary guessing.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

import requests

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "precision_swing_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "precision_swing_ledger.jsonl")
_LEVELS_PATH = os.path.join(ex._DATA_DIR, "precision_swing_levels.json")
_KLINES = "https://api.binance.com/api/v3/klines"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def swing_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("swing"):
            return False
    except Exception:
        pass
    raw = os.environ.get("PRECISION_SWING_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "swing"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _symbols() -> List[str]:
    raw = os.environ.get("PRECISION_SWING_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,ADAUSDT").strip()
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def fetch_daily_ohlc(symbol: str, *, limit: int = 30) -> List[Dict[str, float]]:
    resp = requests.get(
        _KLINES,
        params={"symbol": symbol, "interval": "1d", "limit": int(limit)},
        timeout=12,
        headers={"User-Agent": "masternoder-precision-swing/1.0"},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"http_{resp.status_code}")
    rows = []
    for k in resp.json() or []:
        rows.append({
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
        })
    return rows


def floor_pivot_levels(high: float, low: float, close: float) -> Dict[str, float]:
    """Classic floor-trader pivots — precision levels for swing discipline."""
    p = (high + low + close) / 3.0
    r1 = 2 * p - low
    s1 = 2 * p - high
    r2 = p + (high - low)
    s2 = p - (high - low)
    r3 = high + 2 * (p - low)
    s3 = low - 2 * (high - p)
    return {
        "pivot": round(p, 8),
        "r1": round(r1, 8), "r2": round(r2, 8), "r3": round(r3, 8),
        "s1": round(s1, 8), "s2": round(s2, 8), "s3": round(s3, 8),
    }


def swing_high_low(bars: Sequence[Dict[str, float]], *, lookback: int = 5) -> Dict[str, float]:
    window = list(bars)[-(lookback + 1):-1] if len(bars) > lookback else list(bars)[:-1]
    if not window:
        window = list(bars)
    hi = max(float(b["high"]) for b in window)
    lo = min(float(b["low"]) for b in window)
    return {"swing_high": round(hi, 8), "swing_low": round(lo, 8)}


def classify_trend(bars: Sequence[Dict[str, float]]) -> str:
    if len(bars) < 5:
        return "unknown"
    closes = [float(b["close"]) for b in bars]
    fast = sum(closes[-3:]) / 3.0
    slow = sum(closes[-8:]) / min(8, len(closes))
    if fast > slow * 1.002:
        return "up"
    if fast < slow * 0.998:
        return "down"
    return "range"


def levels_for_symbol(symbol: str) -> Dict[str, Any]:
    bars = fetch_daily_ohlc(symbol, limit=30)
    if len(bars) < 2:
        return {"symbol": symbol, "ok": False, "reason": "insufficient_bars"}
    prev = bars[-2]
    piv = floor_pivot_levels(prev["high"], prev["low"], prev["close"])
    swings = swing_high_low(bars, lookback=int(_cfg_float("PRECISION_SWING_LOOKBACK", 5)))
    last = bars[-1]
    trend = classify_trend(bars)
    # Discipline: bias long only above pivot in uptrend; short below pivot in downtrend.
    bias = "neutral"
    if trend == "up" and last["close"] >= piv["pivot"]:
        bias = "long_levels"
    elif trend == "down" and last["close"] <= piv["pivot"]:
        bias = "short_levels"
    elif trend == "range":
        bias = "fade_edges"
    return {
        "symbol": symbol,
        "ok": True,
        "profile": "precision_level_swing",
        "trend": trend,
        "bias": bias,
        "last_close": last["close"],
        "levels": {**piv, **swings},
        "entries": {
            "long": piv["s1"] if bias in ("long_levels", "fade_edges") else piv["pivot"],
            "short": piv["r1"] if bias in ("short_levels", "fade_edges") else piv["pivot"],
        },
        "stops": {
            "long_stop": swings["swing_low"],
            "short_stop": swings["swing_high"],
        },
    }


def run_precision_swing_tick(*, force: bool = False) -> Dict[str, Any]:
    if not swing_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "swing"}

    rows: List[Dict[str, Any]] = []
    for sym in _symbols():
        try:
            rows.append(levels_for_symbol(sym))
        except Exception as exc:
            rows.append({"symbol": sym, "ok": False, "reason": str(exc)[:120]})

    ok_rows = [r for r in rows if r.get("ok")]
    payload = {
        "updated_at": _iso(),
        "limb": "swing",
        "profile": "precision_level_swing",
        "count": len(ok_rows),
        "levels": ok_rows,
    }
    ex._write_json(_LEVELS_PATH, payload)
    # Publish top bias to head as optional grid hint (non-destructive).
    biased = [r for r in ok_rows if r.get("bias") in ("long_levels", "short_levels")]
    top = biased[0] if biased else (ok_rows[0] if ok_rows else None)
    if top:
        try:
            ctrl_path_hint = {
                "symbol": str(top.get("symbol") or "").replace("USDT", ""),
                "bias": top.get("bias"),
                "trend": top.get("trend"),
                "pivot": (top.get("levels") or {}).get("pivot"),
                "entry": (top.get("entries") or {}).get("long" if "long" in str(top.get("bias")) else "short"),
                "profile": "precision_level_swing",
            }
            state = ex._read_json(_STATE_PATH, {})
            if not isinstance(state, dict):
                state = {}
            state["updated_at"] = _iso()
            state["last_tick"] = {"top": ctrl_path_hint, "count": len(ok_rows)}
            state["swing_hint"] = ctrl_path_hint
            ex._write_json(_STATE_PATH, state)
        except Exception:
            pass

    _append("tick", count=len(ok_rows), top=(top or {}).get("symbol"))
    summary = f"levels={len(ok_rows)} top={(top or {}).get('symbol') or '-'} bias={(top or {}).get('bias') or '-'}"
    return {
        "success": True,
        "limb": "swing",
        "name": "swing",
        "scanned_at": payload["updated_at"],
        "count": len(ok_rows),
        "top": top,
        "summary": summary,
    }


def precision_swing_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": swing_enabled(),
        "levels": ex._read_json(_LEVELS_PATH, {}),
        "state": ex._read_json(_STATE_PATH, {}),
    }
