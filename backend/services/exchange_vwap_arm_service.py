"""VWAP intraday levels — volume-weighted average as dynamic S/R.

Category: ``vwap`` (see profit_strategy_categories).

Computes session (rolling) VWAP from 1m Binance klines plus ±1σ bands so
grid / latch / head can judge whether spot is cheap or rich vs day volume.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import requests

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "vwap_arm_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "vwap_arm_ledger.jsonl")
_LEVELS_PATH = os.path.join(ex._DATA_DIR, "vwap_arm_levels.json")
_KLINES = "https://api.binance.com/api/v3/klines"

_DEFAULT_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "LINKUSDT", "AVAXUSDT", "OPUSDT", "DOGEUSDT",
)


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


def _cfg_int(key: str, default: int) -> int:
    return int(_cfg_float(key, float(default)))


def vwap_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("vwap"):
            return False
    except Exception:
        pass
    raw = os.environ.get("VWAP_ARM_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "vwap", "category": "vwap"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _symbols() -> List[str]:
    raw = os.environ.get("VWAP_SYMBOLS", "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    return list(_DEFAULT_SYMBOLS)


def fetch_minute_bars(symbol: str, *, limit: int = 240) -> List[Dict[str, float]]:
    resp = requests.get(
        _KLINES,
        params={"symbol": symbol, "interval": "1m", "limit": int(limit)},
        timeout=12,
        headers={"User-Agent": "masternoder-vwap/1.0"},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"http_{resp.status_code}")
    rows: List[Dict[str, float]] = []
    for k in resp.json() or []:
        rows.append({
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return rows


def compute_vwap(bars: Sequence[Dict[str, float]]) -> Dict[str, Any]:
    """Classic session VWAP from typical price × volume."""
    if len(bars) < 5:
        return {"ok": False, "reason": "insufficient_bars"}
    num = 0.0
    den = 0.0
    tps: List[float] = []
    for b in bars:
        high = float(b["high"])
        low = float(b["low"])
        close = float(b["close"])
        vol = float(b.get("volume") or 0)
        tp = (high + low + close) / 3.0
        tps.append(tp)
        num += tp * vol
        den += vol
    if den <= 0:
        return {"ok": False, "reason": "zero_volume"}
    vwap = num / den
    last = float(bars[-1]["close"])
    # Rolling stdev of (close − vwap) using expanding vwap approx via tp series.
    diffs = [c - vwap for c in (float(b["close"]) for b in bars)]
    mean_d = sum(diffs) / len(diffs)
    var = sum((d - mean_d) ** 2 for d in diffs) / max(1, len(diffs) - 1)
    sigma = math.sqrt(max(0.0, var))
    distance_bps = ((last / vwap) - 1.0) * 10_000.0 if vwap > 0 else 0.0
    # Cheap below VWAP, rich above — institutional day-volume frame.
    entry_bps = _cfg_float("VWAP_ENTRY_BPS", 8.0)
    if distance_bps <= -entry_bps:
        bias = "buy_below_vwap"
    elif distance_bps >= entry_bps:
        bias = "sell_above_vwap"
    else:
        bias = "at_vwap"
    return {
        "ok": True,
        "vwap": round(vwap, 8),
        "last_close": last,
        "distance_bps": round(distance_bps, 2),
        "sigma": round(sigma, 8),
        "bands": {
            "upper_1": round(vwap + sigma, 8),
            "lower_1": round(vwap - sigma, 8),
            "upper_2": round(vwap + 2 * sigma, 8),
            "lower_2": round(vwap - 2 * sigma, 8),
        },
        "session_bias": bias,
        "support": round(vwap - sigma, 8),
        "resistance": round(vwap + sigma, 8),
    }


def levels_for_symbol(symbol: str) -> Dict[str, Any]:
    limit = _cfg_int("VWAP_LOOKBACK_MINUTES", 240)
    bars = fetch_minute_bars(symbol, limit=max(30, limit))
    scored = compute_vwap(bars)
    return {
        "symbol": symbol,
        "category": "vwap",
        "profile": "vwap_intraday_levels",
        "bars": len(bars),
        **scored,
    }


def run_vwap_tick(*, force: bool = False) -> Dict[str, Any]:
    if not vwap_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "vwap"}

    rows: List[Dict[str, Any]] = []
    for sym in _symbols():
        try:
            rows.append(levels_for_symbol(sym))
        except Exception as exc:
            rows.append({"symbol": sym, "ok": False, "reason": str(exc)[:120], "category": "vwap"})

    ok_rows = [r for r in rows if r.get("ok")]
    # Prefer clearest distance from VWAP for enrichment.
    ranked = sorted(ok_rows, key=lambda r: abs(float(r.get("distance_bps") or 0)), reverse=True)
    top = ranked[0] if ranked else None

    payload = {
        "updated_at": _iso(),
        "limb": "vwap",
        "category": "vwap",
        "profile": "vwap_intraday_levels",
        "count": len(ok_rows),
        "levels": ok_rows,
        "top": top,
    }
    ex._write_json(_LEVELS_PATH, payload)

    state = ex._read_json(_STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    state["updated_at"] = _iso()
    state["last_tick"] = {
        "top": (top or {}).get("symbol"),
        "bias": (top or {}).get("session_bias"),
        "distance_bps": (top or {}).get("distance_bps"),
        "vwap": (top or {}).get("vwap"),
    }
    state["vwap_hint"] = {
        "symbol": str((top or {}).get("symbol") or "").replace("USDT", ""),
        "bias": (top or {}).get("session_bias"),
        "vwap": (top or {}).get("vwap"),
        "distance_bps": (top or {}).get("distance_bps"),
        "bands": (top or {}).get("bands"),
        "category": "vwap",
        "profile": "vwap_intraday_levels",
    } if top else None
    ex._write_json(_STATE_PATH, state)

    _append("tick", count=len(ok_rows), top=(top or {}).get("symbol"), bias=(top or {}).get("session_bias"))
    summary = (
        f"levels={len(ok_rows)} top={(top or {}).get('symbol') or '-'} "
        f"bias={(top or {}).get('session_bias') or '-'} "
        f"dist={(top or {}).get('distance_bps') or '-'}bps"
    )
    return {
        "success": True,
        "limb": "vwap",
        "category": "vwap",
        "name": "vwap",
        "scanned_at": payload["updated_at"],
        "count": len(ok_rows),
        "top": top,
        "summary": summary,
    }


def vwap_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": vwap_enabled(),
        "levels": ex._read_json(_LEVELS_PATH, {}),
        "state": ex._read_json(_STATE_PATH, {}),
    }


def latest_vwap_hint(symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
    levels = ex._read_json(_LEVELS_PATH, {})
    if not isinstance(levels, dict):
        return None
    rows = levels.get("levels") or []
    if symbol:
        want = symbol.upper().replace("/", "").replace("-", "")
        if not want.endswith("USDT"):
            want = want + "USDT"
        for r in rows:
            if str(r.get("symbol") or "").upper() == want:
                return r if isinstance(r, dict) else None
    top = levels.get("top")
    return top if isinstance(top, dict) else None
