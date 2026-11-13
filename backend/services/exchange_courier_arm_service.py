"""Courier arm — cross-venue quote balancer for the profit body.

Moves free quote toward a per-venue floor (and a 50/50 split when funded) by
selling raise inventory on the starved venue. Distinct from hunter backfill:
courier equalizes BN↔NK so arms stop dying on one-sided funding.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "courier_arm_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "courier_arm_ledger.jsonl")
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


def courier_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("courier"):
            return False
    except Exception:
        pass
    raw = os.environ.get("COURIER_ARM_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "courier"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _quote_snaps() -> List[Dict[str, Any]]:
    from backend.services import exchange_venue_api_service as vapi

    out: List[Dict[str, Any]] = []
    for venue in _VENUES:
        quote = str(vapi.venue_quote_asset(venue) or "").upper()
        bals = vapi.parse_spot_balances(venue, dry_run=False, force_refresh=True) or {}
        free = float(bals.get(quote) or 0) if quote else 0.0
        out.append({"venue": venue, "quote": quote, "free": round(free, 4)})
    return out


def _imbalance(snaps: List[Dict[str, Any]], *, floor: float) -> Dict[str, Any]:
    total = sum(float(s.get("free") or 0) for s in snaps)
    by_id = {str(s.get("venue") or ""): s for s in snaps}
    # Keep Binance current: if BN is under floor, treat it as the starved venue even
    # when another venue is slightly poorer in absolute free quote.
    priority = (os.environ.get("COURIER_PRIORITY_VENUE") or "binance").strip().lower()
    rows = sorted(snaps, key=lambda s: float(s.get("free") or 0))
    poor = rows[0] if rows else {}
    rich = rows[-1] if rows else {}
    pri = by_id.get(priority) or {}
    if pri and float(pri.get("free") or 0) < floor:
        poor = pri
        others = [s for s in snaps if str(s.get("venue")) != priority]
        rich = max(others, key=lambda s: float(s.get("free") or 0)) if others else rich
    poor_free = float(poor.get("free") or 0)
    rich_free = float(rich.get("free") or 0)
    share_poor = (poor_free / total) if total > 0 else 0.0
    need_floor = max(0.0, floor - poor_free)
    # Aim toward ~45/55 band once total can fund both floors.
    target_poor = max(floor, total * 0.45) if total >= floor * 2 else floor
    need_ratio = max(0.0, target_poor - poor_free)
    move = round(min(max(need_floor, need_ratio), _cfg_float("COURIER_MAX_MOVE_USD", 25.0)), 2)
    skewed = poor_free < floor or (total >= floor * 2 and share_poor < 0.35)
    return {
        "skewed": skewed,
        "total_free_usd": round(total, 4),
        "poor": poor,
        "rich": rich,
        "share_poor": round(share_poor, 4),
        "move_usd": move,
        "floor_usd": floor,
        "priority_venue": priority,
        "keep_binance": priority == "binance" and float((by_id.get("binance") or {}).get("free") or 0) < floor,
    }


def run_courier_tick(*, force: bool = False) -> Dict[str, Any]:
    """One courier tick: measure imbalance → raise quote on starved venue."""
    if not courier_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "courier"}

    floor = _cfg_float("COURIER_FLOOR_USD", 12.0)
    snaps = _quote_snaps()
    imb = _imbalance(snaps, floor=floor)
    out: Dict[str, Any] = {
        "success": True,
        "limb": "courier",
        "name": "courier",
        "scanned_at": _iso(),
        "quotes": snaps,
        "imbalance": imb,
        "moved": False,
        "action": None,
        "skip_reason": None,
    }

    if not imb.get("skewed"):
        out["skip_reason"] = "balanced"
        _persist(out)
        return out

    poor = imb.get("poor") or {}
    venue = str(poor.get("venue") or "")
    move = float(imb.get("move_usd") or 0)
    if not venue or move < _cfg_float("COURIER_MIN_MOVE_USD", 3.0):
        out["skip_reason"] = "gap_too_small"
        _persist(out)
        return out

    # Prefer head prefund symbol as raise inventory.
    preferred: List[str] = []
    try:
        from backend.services.exchange_profit_head_service import get_prefund_hint

        hint = get_prefund_hint()
        if hint and hint.get("symbol"):
            preferred.append(str(hint["symbol"]).upper())
    except Exception:
        pass

    from backend.services.exchange_spread_hunter_arm_service import _raise_quote_on_buy_venue

    need = float(poor.get("free") or 0) + move
    action = _raise_quote_on_buy_venue(
        venue,
        need_usd=need,
        raise_symbols=preferred or None,
        min_sell_usd=_cfg_float("COURIER_MIN_MOVE_USD", 3.0),
        max_fraction=_cfg_float("COURIER_MAX_FRACTION", 0.5),
        scan_all_balances=True,
    )
    out["action"] = action
    out["moved"] = bool(action.get("success")) and not action.get("skipped")
    if not out["moved"]:
        out["skip_reason"] = str(action.get("reason") or "raise_failed")

    # Publish courier hint for the head when still skewed after attempt.
    after = _quote_snaps()
    imb_after = _imbalance(after, floor=floor)
    out["quotes_after"] = after
    out["imbalance_after"] = imb_after
    hint = {
        "from_venue": (imb.get("rich") or {}).get("venue"),
        "to_venue": venue,
        "amount_usd": move,
        "reason": "quote_imbalance",
        "poor_free": (imb.get("poor") or {}).get("free"),
        "rich_free": (imb.get("rich") or {}).get("free"),
    }
    out["courier_hint"] = hint
    try:
        from backend.services.exchange_profit_head_service import set_courier_hint

        set_courier_hint(hint if imb_after.get("skewed") else None)
    except Exception:
        pass

    _append(
        "courier_tick",
        moved=out["moved"],
        venue=venue,
        move_usd=move,
        sell_usd=(action or {}).get("sell_usd"),
        symbol=(action or {}).get("symbol"),
        skip=out.get("skip_reason"),
    )
    _persist(out)
    summary = (
        f"moved={'yes' if out['moved'] else 'no'} "
        f"poor={venue}:${float((imb.get('poor') or {}).get('free') or 0):.2f} "
        f"rich={(imb.get('rich') or {}).get('venue')}:${float((imb.get('rich') or {}).get('free') or 0):.2f} "
        f"need=${move:.2f}"
    )
    if out.get("skip_reason"):
        summary += f" skip={out['skip_reason']}"
    out["summary"] = summary
    return out


def _persist(out: Dict[str, Any]) -> None:
    state = _load_state()
    state.update({
        "updated_at": _iso(),
        "last_tick": {
            "moved": out.get("moved"),
            "skip_reason": out.get("skip_reason"),
            "imbalance": out.get("imbalance"),
            "action": {
                "success": (out.get("action") or {}).get("success"),
                "symbol": (out.get("action") or {}).get("symbol"),
                "sell_usd": (out.get("action") or {}).get("sell_usd"),
                "venue": (out.get("action") or {}).get("venue"),
            } if out.get("action") else None,
            "courier_hint": out.get("courier_hint"),
        },
    })
    if out.get("moved"):
        state["move_count"] = int(state.get("move_count") or 0) + 1
        state["last_move_at"] = out.get("scanned_at")
    _save_state(state)
    if not out.get("summary"):
        out["summary"] = (
            f"moved={'yes' if out.get('moved') else 'no'} "
            f"skip={out.get('skip_reason') or '-'}"
        )
