"""Closer claw — finish half-filled spatial legs and harvest dust into quote.

Profit dies on unfinished buy/sell pairs and trapped dust. The claw retries the
missing leg and sells small coin balances back to venue quote.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_STATE_PATH = os.path.join(ex._DATA_DIR, "closer_claw_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "closer_claw_ledger.jsonl")
_OPEN_PATH = os.path.join(ex._DATA_DIR, "closer_open_legs.json")
_VENUES = ("binance", "nonkyc")


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


def closer_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("closer"):
            return False
    except Exception:
        pass
    raw = os.environ.get("CLOSER_CLAW_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _load_open() -> List[Dict[str, Any]]:
    raw = ex._read_json(_OPEN_PATH, {"legs": []})
    legs = raw.get("legs") if isinstance(raw, dict) else []
    return list(legs) if isinstance(legs, list) else []


def _save_open(legs: List[Dict[str, Any]]) -> None:
    ex._write_json(_OPEN_PATH, {"updated_at": _iso(), "legs": legs[-50:]})


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "closer"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def note_execution_legs(
    opp: Dict[str, Any],
    exec_res: Dict[str, Any],
    *,
    source: str = "spatial",
) -> Optional[Dict[str, Any]]:
    """Register a half-fill so the claw can finish the missing leg."""
    buy = exec_res.get("buy_order") or {}
    sell = exec_res.get("sell_order") or {}
    buy_ok = bool(buy.get("success"))
    sell_ok = bool(sell.get("success"))
    if buy_ok == sell_ok:
        return None
    missing = "sell" if buy_ok and not sell_ok else "buy"
    leg = {
        "id": f"{opp.get('symbol')}-{exec_res.get('executed_at') or _iso()}",
        "ts": _iso(),
        "source": source,
        "symbol": str(opp.get("symbol") or exec_res.get("symbol") or "").upper(),
        "buy_venue": str(opp.get("buy_venue") or exec_res.get("buy_venue") or "").lower(),
        "sell_venue": str(opp.get("sell_venue") or exec_res.get("sell_venue") or "").lower(),
        "quantity": float(exec_res.get("quantity") or 0),
        "notional_usd": float(exec_res.get("notional_usd") or opp.get("notional_usd") or 0),
        "missing": missing,
        "buy_order": {"success": buy_ok, "order_id": buy.get("order_id"), "error": buy.get("error")},
        "sell_order": {"success": sell_ok, "order_id": sell.get("order_id"), "error": sell.get("error")},
        "status": "open",
        "attempts": 0,
    }
    legs = _load_open()
    legs.append(leg)
    _save_open(legs)
    _append("open_leg", symbol=leg["symbol"], missing=missing, source=source)
    return leg


def _retry_open_leg(leg: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi

    sym = str(leg.get("symbol") or "").upper()
    qty = float(leg.get("quantity") or 0)
    missing = str(leg.get("missing") or "")
    if not sym or qty <= 0 or missing not in ("buy", "sell"):
        return {"success": False, "reason": "invalid_leg"}

    if missing == "sell":
        venue = str(leg.get("sell_venue") or "")
        side = "sell"
    else:
        venue = str(leg.get("buy_venue") or "")
        side = "buy"
    if not venue:
        return {"success": False, "reason": "missing_venue"}

    quote = vapi.venue_quote_asset(venue)
    # Microstructure: retry large half-legs as a clip first to clear venue mins / slip.
    clip_frac = _cfg_float("CLOSER_MICRO_CLIP_FRAC", 0.45)
    attempts = int(leg.get("attempts") or 0)
    use_qty = qty
    if attempts >= 1 and clip_frac > 0 and clip_frac < 1:
        use_qty = max(qty * clip_frac, qty * 0.2)
    order = vapi.place_market_order(venue, sym, side, use_qty, dry_run=False, quote=quote)
    ok = bool(order.get("success"))
    vapi.invalidate_venue_balance_cache(venue)
    return {
        "success": ok,
        "venue": venue,
        "side": side,
        "symbol": sym,
        "quantity": use_qty,
        "full_quantity": qty,
        "micro_clip": use_qty < qty * 0.99,
        "order_success": ok,
        "error": order.get("error") if not ok else None,
    }


def _dust_candidates(venue: str) -> List[Dict[str, Any]]:
    from backend.services import exchange_venue_api_service as vapi

    quote = str(vapi.venue_quote_asset(venue) or "").upper()
    bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
    # Microstructure: harvest smaller dust clips so quote rebuilds faster after partial fills.
    min_usd = _cfg_float("CLOSER_DUST_MIN_USD", 1.5)
    max_usd = _cfg_float("CLOSER_DUST_MAX_USD", 25.0)
    skip = {quote, "USDT", "USDC", "USD", "BUSD", "FDUSD", "DAI"}
    rows: List[Dict[str, Any]] = []
    for sym, raw in bals.items():
        s = str(sym or "").upper()
        if not s or s in skip:
            continue
        try:
            qty = float(raw or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        tick = conn.fetch_ticker(venue, s) or {}
        bid = float(tick.get("bid") or 0)
        if bid <= 0:
            continue
        usd = qty * bid
        if usd < min_usd or usd > max_usd:
            continue
        rows.append({"symbol": s, "qty": qty, "bid": bid, "usd": round(usd, 2), "venue": venue, "quote": quote})
    rows.sort(key=lambda r: r["usd"])
    return rows


def _harvest_dust(limit: int = 2) -> List[Dict[str, Any]]:
    from backend.services import exchange_venue_api_service as vapi

    actions: List[Dict[str, Any]] = []
    for venue in _VENUES:
        for row in _dust_candidates(venue)[:limit]:
            sell_qty = round(float(row["qty"]) * 0.995, 6)
            if sell_qty <= 0:
                continue
            order = vapi.place_market_order(
                venue, row["symbol"], "sell", sell_qty, dry_run=False, quote=row["quote"],
            )
            ok = bool(order.get("success"))
            vapi.invalidate_venue_balance_cache(venue)
            actions.append({
                "action": "dust_sell",
                "venue": venue,
                "symbol": row["symbol"],
                "sell_usd": row["usd"],
                "success": ok,
                "error": order.get("error") if not ok else None,
            })
            if ok:
                _append("dust_sell", venue=venue, symbol=row["symbol"], sell_usd=row["usd"])
    return actions


def run_closer_tick(*, force: bool = False) -> Dict[str, Any]:
    """Retry open half-legs, then harvest dust into quote."""
    if not closer_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "closer"}

    open_legs = _load_open()
    closed = 0
    retried = 0
    still_open: List[Dict[str, Any]] = []
    max_attempts = int(_cfg_float("CLOSER_MAX_ATTEMPTS", 5))

    for leg in open_legs:
        if str(leg.get("status") or "open") != "open":
            continue
        attempts = int(leg.get("attempts") or 0)
        if attempts >= max_attempts:
            leg = dict(leg)
            leg["status"] = "abandoned"
            leg["closed_at"] = _iso()
            still_open.append(leg)
            _append("abandon", symbol=leg.get("symbol"), missing=leg.get("missing"))
            continue
        retried += 1
        res = _retry_open_leg(leg)
        leg = dict(leg)
        leg["attempts"] = attempts + 1
        leg["last_retry"] = {"ts": _iso(), **res}
        if res.get("success"):
            leg["status"] = "closed"
            leg["closed_at"] = _iso()
            closed += 1
            _append("close", symbol=leg.get("symbol"), missing=leg.get("missing"), venue=res.get("venue"))
        still_open.append(leg)

    # Keep abandoned briefly for audit, drop closed.
    keep = [l for l in still_open if l.get("status") != "closed"]
    _save_open(keep)

    dust = []
    if os.environ.get("CLOSER_DUST_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off"):
        dust = _harvest_dust(limit=_cfg_int_safe(2))

    dust_ok = sum(1 for d in dust if d.get("success"))
    out = {
        "success": True,
        "limb": "closer",
        "name": "closer",
        "scanned_at": _iso(),
        "open_before": len(open_legs),
        "open_after": len(keep),
        "retried": retried,
        "closed": closed,
        "dust_actions": dust,
        "dust_sold": dust_ok,
    }
    out["summary"] = (
        f"open={out['open_after']} closed={closed} retried={retried} dust={dust_ok}"
    )
    state = _load_state()
    state.update({
        "updated_at": _iso(),
        "last_tick": {
            "open_after": out["open_after"],
            "closed": closed,
            "retried": retried,
            "dust_sold": dust_ok,
        },
        "close_count": int(state.get("close_count") or 0) + closed,
        "dust_count": int(state.get("dust_count") or 0) + dust_ok,
    })
    _save_state(state)
    return out


def _cfg_int_safe(default: int) -> int:
    return int(_cfg_float("CLOSER_DUST_LIMIT", float(default)))
