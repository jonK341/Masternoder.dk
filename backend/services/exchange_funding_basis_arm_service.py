"""Hummingbot-style spot–perp / funding basis arm.

Mirrors Hummingbot ``spot_perpetual_arbitrage`` + DataMaxi funding-rate playbook:
* Scan Binance premiumIndex (mark vs index) and last funding rate.
* Score APR + basis divergence.
* Open / track a paper (or live when futures keys exist) delta-neutral carry:
  funding > 0 → long spot / short perp; funding < 0 → reverse when enabled.

Live perp shorts stay gated behind ``FUNDING_BASIS_LIVE=1`` and working futures
credentials — default is scan + ledger + optional spot seed only.

Refs:
  https://hummingbot.org/strategies/v1-strategies/spot-perpetual-arbitrage/
  https://docs.datamaxiplus.com/strategies/funding-rate-arb
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "funding_basis_arm_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "funding_basis_arm_ledger.jsonl")
_BOOK_PATH = os.path.join(ex._DATA_DIR, "funding_basis_book.json")
_FAPI = (os.environ.get("BINANCE_FAPI_BASE") or "https://fapi.binance.com").rstrip("/")

_DEFAULT_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "NEARUSDT",
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


def funding_basis_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("basis"):
            return False
    except Exception:
        pass
    raw = os.environ.get("FUNDING_BASIS_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _live_perp() -> bool:
    return os.environ.get("FUNDING_BASIS_LIVE", "0").strip().lower() in ("1", "true", "yes", "on")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "basis"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _symbols() -> List[str]:
    raw = os.environ.get("FUNDING_BASIS_SYMBOLS", "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    return list(_DEFAULT_SYMBOLS)


def _get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    resp = requests.get(
        url,
        params=params or {},
        timeout=12,
        headers={"User-Agent": "masternoder-funding-basis/1.0"},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"http_{resp.status_code}:{resp.text[:120]}")
    return resp.json()


def fetch_premium_index(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    data = _get_json(f"{_FAPI}/fapi/v1/premiumIndex", {"symbol": symbol} if symbol else None)
    if isinstance(data, dict):
        return [data]
    return list(data or [])


def fetch_last_funding(symbol: str) -> Optional[Dict[str, Any]]:
    rows = _get_json(f"{_FAPI}/fapi/v1/fundingRate", {"symbol": symbol, "limit": 1})
    if isinstance(rows, list) and rows:
        return rows[-1]
    return None


def _apr_from_rate(rate: float, interval_hours: float = 8.0) -> float:
    # periods per year
    periods = (365.0 * 24.0) / max(1.0, interval_hours)
    return float(rate) * periods * 100.0


def score_basis_row(row: Dict[str, Any], *, last_funding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Hummingbot-style divergence + DataMaxi APR score."""
    mark = float(row.get("markPrice") or 0)
    index = float(row.get("indexPrice") or 0)
    last_rate = float(row.get("lastFundingRate") or 0)
    if last_funding and last_funding.get("fundingRate") is not None:
        last_rate = float(last_funding.get("fundingRate") or last_rate)
    basis_bps = 0.0
    if index > 0 and mark > 0:
        basis_bps = (mark - index) / index * 10000.0
    interval_h = _cfg_float("FUNDING_BASIS_INTERVAL_HOURS", 8.0)
    apr = _apr_from_rate(last_rate, interval_h)
    min_open_pct = _cfg_float("FUNDING_BASIS_MIN_OPEN_PCT", 1.0)  # Hummingbot default 1%
    min_close_pct = _cfg_float("FUNDING_BASIS_MIN_CLOSE_PCT", 0.1)
    min_apr = _cfg_float("FUNDING_BASIS_MIN_APR", 8.0)  # DataMaxi ~5–10% after fees
    open_div = abs(basis_bps) / 100.0  # bps → percent
    # Positive funding → long spot / short perp (classic carry)
    side = "long_spot_short_perp" if last_rate >= 0 else "short_spot_long_perp"
    reverse_ok = os.environ.get("FUNDING_BASIS_ALLOW_REVERSE", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    actionable = False
    reason = None
    if last_rate < 0 and not reverse_ok:
        reason = "negative_funding_reverse_disabled"
    elif apr < min_apr and open_div < min_open_pct:
        reason = "below_apr_and_divergence"
    elif open_div >= min_open_pct or apr >= min_apr:
        actionable = True
    else:
        reason = "below_thresholds"

    return {
        "symbol": str(row.get("symbol") or "").upper(),
        "mark_price": mark,
        "index_price": index,
        "basis_bps": round(basis_bps, 2),
        "funding_rate": last_rate,
        "funding_apr_pct": round(apr, 2),
        "open_divergence_pct": round(open_div, 4),
        "min_opening_pct": min_open_pct,
        "min_closing_pct": min_close_pct,
        "side": side,
        "actionable": actionable,
        "reason": reason,
        "next_funding_time": row.get("nextFundingTime"),
    }


def build_funding_basis_book() -> Dict[str, Any]:
    want = set(_symbols())
    errors: List[str] = []
    scored: List[Dict[str, Any]] = []
    try:
        rows = fetch_premium_index()
    except Exception as exc:
        return {
            "updated_at": _iso(),
            "limb": "basis",
            "ok": False,
            "error": str(exc)[:200],
            "top": [],
            "actionable_count": 0,
        }

    for row in rows:
        sym = str(row.get("symbol") or "").upper()
        if want and sym not in want:
            continue
        try:
            hist = None
            # Optional last settled rate (premiumIndex already has lastFundingRate).
            scored.append(score_basis_row(row, last_funding=hist))
        except Exception as exc:
            errors.append(f"{sym}:{exc}")

    scored.sort(
        key=lambda r: (1 if r.get("actionable") else 0, abs(float(r.get("funding_apr_pct") or 0))),
        reverse=True,
    )
    book = {
        "updated_at": _iso(),
        "limb": "basis",
        "ok": True,
        "playbook": "hummingbot_spot_perp + datamaxi_funding",
        "live_perp": _live_perp(),
        "symbol_count": len(scored),
        "actionable_count": sum(1 for r in scored if r.get("actionable")),
        "top": scored[:10],
        "errors": errors[:5],
    }
    ex._write_json(_BOOK_PATH, book)
    return book


def _maybe_seed_spot(top: Dict[str, Any]) -> Dict[str, Any]:
    """Optional: ensure spot inventory exists on Binance for long-spot carry."""
    if os.environ.get("FUNDING_BASIS_SEED_SPOT", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return {"skipped": True, "reason": "seed_disabled"}
    if top.get("side") != "long_spot_short_perp":
        return {"skipped": True, "reason": "not_long_spot_side"}
    sym = str(top.get("symbol") or "").replace("USDT", "").replace("USDC", "")
    if not sym:
        return {"skipped": True, "reason": "bad_symbol"}
    try:
        from backend.services.exchange_courier_arm_service import sync_binance

        return sync_binance(
            floor_usd=_cfg_float("COURIER_FLOOR_USD", 12.0),
            seed_symbol=sym,
            seed_usd=_cfg_float("FUNDING_BASIS_SEED_USD", 15.0),
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)[:160]}


def run_funding_basis_tick(*, force: bool = False) -> Dict[str, Any]:
    if not funding_basis_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "basis"}

    book = build_funding_basis_book()
    top = (book.get("top") or [None])[0]
    out: Dict[str, Any] = {
        "success": bool(book.get("ok")),
        "limb": "basis",
        "name": "basis",
        "scanned_at": book.get("updated_at"),
        "symbol_count": book.get("symbol_count"),
        "actionable_count": book.get("actionable_count"),
        "top": top,
        "opened": False,
        "seed": None,
        "skip_reason": None,
        "error": book.get("error"),
    }
    if not book.get("ok"):
        out["skip_reason"] = book.get("error") or "premium_index_failed"
    elif not top:
        out["skip_reason"] = "empty_book"
    elif not top.get("actionable"):
        out["skip_reason"] = top.get("reason") or "no_actionable"
    else:
        out["seed"] = _maybe_seed_spot(top)
        # Live perp open is explicitly gated — record intent otherwise.
        if _live_perp():
            out["opened"] = False
            out["skip_reason"] = "live_perp_not_wired"  # connector stub for now
            _append("live_blocked", symbol=top.get("symbol"), side=top.get("side"))
        else:
            _append(
                "signal",
                symbol=top.get("symbol"),
                side=top.get("side"),
                apr=top.get("funding_apr_pct"),
                basis_bps=top.get("basis_bps"),
                mode="paper_signal",
            )
            out["opened"] = False
            out["skip_reason"] = "paper_signal_only"

    state = {
        "updated_at": _iso(),
        "last_tick": {
            "top": top,
            "actionable_count": out.get("actionable_count"),
            "skip_reason": out.get("skip_reason"),
            "live_perp": _live_perp(),
        },
    }
    ex._write_json(_STATE_PATH, state)
    out["summary"] = (
        f"syms={out.get('symbol_count', 0)} act={out.get('actionable_count', 0)} "
        f"top={(top or {}).get('symbol') or '-'} "
        f"apr={(top or {}).get('funding_apr_pct')} "
        f"basis={(top or {}).get('basis_bps')}"
    )
    if out.get("skip_reason"):
        out["summary"] += f" skip={out['skip_reason']}"
    return out


def funding_basis_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": funding_basis_enabled(),
        "live_perp": _live_perp(),
        "book": ex._read_json(_BOOK_PATH, {}),
        "state": ex._read_json(_STATE_PATH, {}),
    }
