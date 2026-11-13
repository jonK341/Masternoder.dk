"""Momentum trading arm — short-term price + volume burst with tight stops.

Category: ``momentum`` (see profit_strategy_categories).

Scans Binance spot klines for strong short-horizon returns with volume
confirmation, optionally nudges score from news/sentiment heat, and publishes
paper (or live-gated) entries with a hard stop-loss percent.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import requests

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "momentum_arm_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "momentum_arm_ledger.jsonl")
_BOARD_PATH = os.path.join(ex._DATA_DIR, "momentum_arm_board.json")
_KLINES = "https://api.binance.com/api/v3/klines"

_DEFAULT_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "OPUSDT",
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


def momentum_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("momentum"):
            return False
    except Exception:
        pass
    raw = os.environ.get("MOMENTUM_ARM_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _live() -> bool:
    return os.environ.get("MOMENTUM_LIVE", "0").strip().lower() in ("1", "true", "yes", "on")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "momentum", "category": "momentum"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _symbols() -> List[str]:
    raw = os.environ.get("MOMENTUM_SYMBOLS", "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    return list(_DEFAULT_SYMBOLS)


def fetch_klines(symbol: str, *, interval: str = "5m", limit: int = 36) -> List[Dict[str, float]]:
    resp = requests.get(
        _KLINES,
        params={"symbol": symbol, "interval": interval, "limit": int(limit)},
        timeout=12,
        headers={"User-Agent": "masternoder-momentum/1.0"},
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


def _sentiment_heat(symbol: str) -> float:
    """0..1 heat from recent profit-news / deterministic proxy — never blocks."""
    base = 0.45
    try:
        from backend.services.exchange_ai_trading_service import _deterministic_sentiment
        base = float(_deterministic_sentiment(symbol.replace("USDT", ""), "binance", "nonkyc"))
    except Exception:
        pass
    try:
        news = ex._read_json(os.path.join(ex._DATA_DIR, "profit_daemon_news_state.json"), {})
        key = str((news or {}).get("last_key") or "")
        if symbol.replace("USDT", "") in key.upper():
            base = min(1.0, base + 0.25)
    except Exception:
        pass
    return max(0.0, min(1.0, base))


def score_momentum_bars(
    bars: Sequence[Dict[str, float]],
    *,
    lookback: int = 6,
    min_return_bps: float = 25.0,
    min_volume_ratio: float = 1.4,
    stop_pct: float = 1.5,
    sentiment: float = 0.45,
) -> Dict[str, Any]:
    """Score a short-horizon momentum burst from OHLCV bars."""
    if len(bars) < max(lookback + 2, 8):
        return {"ok": False, "reason": "insufficient_bars"}
    window = list(bars)[-(lookback + 1):]
    first = float(window[0]["close"])
    last = float(window[-1]["close"])
    if first <= 0 or last <= 0:
        return {"ok": False, "reason": "bad_price"}
    return_bps = (last / first - 1.0) * 10_000.0
    vols = [float(b.get("volume") or 0) for b in bars[-(lookback * 3):]]
    avg_vol = (sum(vols[:-1]) / max(1, len(vols) - 1)) if len(vols) > 1 else 0.0
    last_vol = float(window[-1].get("volume") or 0)
    volume_ratio = (last_vol / avg_vol) if avg_vol > 0 else 0.0
    # Tight stop from last close.
    stop_price = round(last * (1.0 - abs(stop_pct) / 100.0), 8) if return_bps >= 0 else round(
        last * (1.0 + abs(stop_pct) / 100.0), 8
    )
    # Composite: return × volume confirmation × mild sentiment nudge.
    sent = max(0.2, min(1.2, 0.7 + 0.6 * (sentiment - 0.5)))
    score = return_bps * max(0.5, volume_ratio) * sent
    actionable = (
        return_bps >= min_return_bps
        and volume_ratio >= min_volume_ratio
        and score >= min_return_bps * min_volume_ratio * 0.8
    )
    bias = "long_burst" if return_bps >= min_return_bps else (
        "short_fade" if return_bps <= -min_return_bps else "flat"
    )
    return {
        "ok": True,
        "return_bps": round(return_bps, 2),
        "volume_ratio": round(volume_ratio, 3),
        "momentum_score": round(score, 2),
        "last_close": last,
        "stop_pct": abs(stop_pct),
        "stop_price": stop_price,
        "sentiment": round(sentiment, 3),
        "bias": bias,
        "actionable": actionable,
        "reason": None if actionable else (
            "below_return" if return_bps < min_return_bps else "below_volume"
        ),
    }


def scan_symbol(symbol: str) -> Dict[str, Any]:
    interval = os.environ.get("MOMENTUM_INTERVAL", "5m").strip() or "5m"
    lookback = _cfg_int("MOMENTUM_LOOKBACK_BARS", 6)
    bars = fetch_klines(symbol, interval=interval, limit=max(36, lookback * 4))
    scored = score_momentum_bars(
        bars,
        lookback=lookback,
        min_return_bps=_cfg_float("MOMENTUM_MIN_RETURN_BPS", 25.0),
        min_volume_ratio=_cfg_float("MOMENTUM_MIN_VOLUME_RATIO", 1.4),
        stop_pct=_cfg_float("MOMENTUM_STOP_PCT", 1.5),
        sentiment=_sentiment_heat(symbol),
    )
    return {
        "symbol": symbol,
        "category": "momentum",
        "profile": "momentum_volume_burst",
        "interval": interval,
        "lookback": lookback,
        **scored,
    }


def run_momentum_tick(*, force: bool = False) -> Dict[str, Any]:
    if not momentum_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "momentum"}

    rows: List[Dict[str, Any]] = []
    for sym in _symbols():
        try:
            rows.append(scan_symbol(sym))
        except Exception as exc:
            rows.append({"symbol": sym, "ok": False, "reason": str(exc)[:120], "category": "momentum"})

    ok_rows = [r for r in rows if r.get("ok")]
    actionable = [r for r in ok_rows if r.get("actionable")]
    actionable.sort(key=lambda r: float(r.get("momentum_score") or 0), reverse=True)
    top = actionable[0] if actionable else (ok_rows[0] if ok_rows else None)

    board = {
        "updated_at": _iso(),
        "limb": "momentum",
        "category": "momentum",
        "profile": "momentum_volume_burst",
        "live": _live(),
        "count": len(ok_rows),
        "actionable_count": len(actionable),
        "rows": ok_rows,
        "top": top,
        "skip_reason": None if actionable else "paper_signal_only_no_burst",
    }
    if actionable and not _live():
        board["skip_reason"] = "paper_signal_only"
    ex._write_json(_BOARD_PATH, board)

    state = ex._read_json(_STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    state["updated_at"] = _iso()
    state["last_tick"] = {
        "top": (top or {}).get("symbol"),
        "score": (top or {}).get("momentum_score"),
        "bias": (top or {}).get("bias"),
        "actionable": len(actionable),
        "stop_pct": (top or {}).get("stop_pct"),
    }
    state["momentum_hint"] = {
        "symbol": str((top or {}).get("symbol") or "").replace("USDT", ""),
        "bias": (top or {}).get("bias"),
        "score": (top or {}).get("momentum_score"),
        "stop_pct": (top or {}).get("stop_pct"),
        "stop_price": (top or {}).get("stop_price"),
        "category": "momentum",
        "profile": "momentum_volume_burst",
    } if top else None
    ex._write_json(_STATE_PATH, state)

    _append(
        "tick",
        count=len(ok_rows),
        actionable=len(actionable),
        top=(top or {}).get("symbol"),
        score=(top or {}).get("momentum_score"),
        live=_live(),
    )
    summary = (
        f"syms={len(ok_rows)} act={len(actionable)} "
        f"top={(top or {}).get('symbol') or '-'} "
        f"score={(top or {}).get('momentum_score') or '-'} "
        f"stop={(top or {}).get('stop_pct') or '-'}% "
        f"skip={board.get('skip_reason') or '-'}"
    )
    return {
        "success": True,
        "limb": "momentum",
        "category": "momentum",
        "name": "momentum",
        "scanned_at": board["updated_at"],
        "count": len(ok_rows),
        "actionable_count": len(actionable),
        "top": top,
        "summary": summary,
        "skip_reason": board.get("skip_reason"),
        "live": _live(),
    }


def momentum_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": momentum_enabled(),
        "live": _live(),
        "board": ex._read_json(_BOARD_PATH, {}),
        "state": ex._read_json(_STATE_PATH, {}),
    }


def latest_momentum_hint(symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
    board = ex._read_json(_BOARD_PATH, {})
    if not isinstance(board, dict):
        return None
    rows = board.get("rows") or []
    if symbol:
        want = symbol.upper().replace("/", "").replace("-", "")
        if not want.endswith("USDT"):
            want = want + "USDT"
        for r in rows:
            if str(r.get("symbol") or "").upper() == want:
                return r if isinstance(r, dict) else None
    top = board.get("top")
    return top if isinstance(top, dict) else None
