"""Latch sniper — wait for mid-skew to compress, then strike.

Arms a pending latch when hunter/pbook sees a real edge but
``regime_skew_too_wide`` / phantom residual. Rechecks until skew clears or TTL
expires, then executes spatial arb once.

Maker mode (``LATCH_MAKER=1``, default on): while waiting, park a limit sell on
the rich venue at residual-safe price so we capture edge as maker if the book
comes to us.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_STATE_PATH = os.path.join(ex._DATA_DIR, "latch_sniper_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "latch_sniper_ledger.jsonl")


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


def latch_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("latch"):
            return False
    except Exception:
        pass
    raw = os.environ.get("LATCH_SNIPER_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "latch"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def arm_latch(
    *,
    symbol: str,
    buy_venue: str,
    sell_venue: str,
    net_bps: float,
    mid_skew_bps: float,
    est_profit_usd: float = 0.0,
    notional_usd: float = 15.0,
    source: str = "hunter",
) -> Dict[str, Any]:
    """Register or refresh a pending latch for a skewed edge."""
    state = _load_state()
    pending: List[Dict[str, Any]] = list(state.get("pending") or [])
    sym = str(symbol or "").upper()
    buy_v = str(buy_venue or "").lower()
    sell_v = str(sell_venue or "").lower()
    if not sym or not buy_v or not sell_v:
        return {"success": False, "reason": "invalid_route"}

    max_pending = _cfg_int("LATCH_MAX_PENDING", 3)
    now = _iso()
    existing = None
    for row in pending:
        if (
            str(row.get("symbol") or "").upper() == sym
            and str(row.get("buy_venue") or "").lower() == buy_v
            and str(row.get("sell_venue") or "").lower() == sell_v
        ):
            existing = row
            break
    payload = {
        "symbol": sym,
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "net_bps_armed": round(float(net_bps or 0), 2),
        "mid_skew_armed": round(float(mid_skew_bps or 0), 2),
        "est_profit_usd": round(float(est_profit_usd or 0), 4),
        "notional_usd": round(float(notional_usd or 15.0), 2),
        "source": source,
        "armed_at": (existing or {}).get("armed_at") or now,
        "updated_at": now,
        "status": "armed",
    }
    if existing:
        pending = [payload if r is existing else r for r in pending]
    else:
        pending.append(payload)
        pending = pending[-max_pending:]
    state["pending"] = pending
    state["updated_at"] = now
    _save_state(state)
    _append("arm", **payload)
    return {"success": True, "latch": payload, "pending_count": len(pending)}


def _expire_pending(pending: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ttl = _cfg_float("LATCH_TTL_SEC", 600.0)
    keep: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for row in pending:
        try:
            armed = datetime.fromisoformat(str(row.get("armed_at") or "").replace("Z", "+00:00"))
            age = (now - armed).total_seconds()
        except Exception:
            age = 0.0
        if age > ttl:
            _append("expire", symbol=row.get("symbol"), age_sec=round(age, 1))
            continue
        keep.append(row)
    return keep


def _candidate_from_hunter() -> Optional[Dict[str, Any]]:
    board = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_board.json"), {})
    state = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_arm_state.json"), {})
    last = state.get("last_tick") if isinstance(state, dict) else {}
    skip = str((last or {}).get("skip_reason") or "")
    top = (last or {}).get("top") if isinstance(last, dict) else None
    if skip == "regime_skew_too_wide" and isinstance(top, dict) and top.get("symbol"):
        recheck = (last or {}).get("recheck") if isinstance(last, dict) else {}
        opp = (recheck or {}).get("opportunity") if isinstance(recheck, dict) else {}
        return {
            "symbol": top.get("symbol"),
            "buy_venue": top.get("buy_venue"),
            "sell_venue": top.get("sell_venue"),
            "net_bps": float(top.get("net_bps") or opp.get("net_bps") or 0),
            "mid_skew_bps": float(opp.get("mid_skew_bps") or 0),
            "est_profit_usd": float(top.get("est_profit_usd") or 0),
            "notional_usd": float(top.get("notional_usd") or _cfg_float("LATCH_NOTIONAL_USD", 15.0)),
            "source": "hunter_skip",
        }
    gaps = (board or {}).get("gaps") if isinstance(board, dict) else None
    if isinstance(gaps, list) and gaps:
        g0 = gaps[0] if isinstance(gaps[0], dict) else None
        if g0 and float(g0.get("net_bps") or 0) >= _cfg_float("LATCH_MIN_BPS", 20.0):
            return {
                "symbol": g0.get("symbol"),
                "buy_venue": g0.get("buy_venue"),
                "sell_venue": g0.get("sell_venue"),
                "net_bps": float(g0.get("net_bps") or 0),
                "mid_skew_bps": float(g0.get("mid_skew_bps") or 999),
                "est_profit_usd": float(g0.get("est_profit_usd") or 0),
                "notional_usd": float(g0.get("notional_usd") or 15.0),
                "source": "hunter_board",
            }
    return None


def _recheck_latch(row: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.exchange_spread_hunter_arm_service import (
        _annotate_opportunity,
        mid_skew_bps,
        regime_deweight_factor,
    )

    sym = str(row.get("symbol") or "").upper()
    buy_v = str(row.get("buy_venue") or "")
    sell_v = str(row.get("sell_venue") or "")
    buy_tick = conn.fetch_ticker(buy_v, sym) or {}
    sell_tick = conn.fetch_ticker(sell_v, sym) or {}
    buy_ask = float(buy_tick.get("ask") or 0)
    buy_bid = float(buy_tick.get("bid") or 0)
    sell_ask = float(sell_tick.get("ask") or 0)
    sell_bid = float(sell_tick.get("bid") or 0)
    if buy_ask <= 0 or sell_bid <= 0:
        return {"ok": False, "reason": "stale_book"}

    cfg = conn.load_connectors_config()
    xfer = float(arb._effective_transfer_cost_bps(cfg))
    notional = float(row.get("notional_usd") or 15.0)
    opp = _annotate_opportunity(
        {
            "symbol": sym,
            "buy_venue": buy_v,
            "sell_venue": sell_v,
            "buy_ask": buy_ask,
            "sell_bid": sell_bid,
            "buy_bid": buy_bid,
            "sell_ask": sell_ask,
            "notional_usd": notional,
        },
        notional_usd=notional,
        cfg=cfg,
        xfer_bps=xfer,
    )
    skew = mid_skew_bps(buy_ask, buy_bid, sell_ask, sell_bid)
    max_skew = _cfg_float("LATCH_MAX_MID_SKEW_BPS", 80.0)
    min_bps = _cfg_float("LATCH_MIN_BPS", 12.0)
    factor, reason = regime_deweight_factor(
        net_bps=float(opp.get("net_bps") or 0),
        mid_skew=skew,
        max_skew_bps=max_skew,
        collapse_bps=max(0.0, min_bps - 3.0),
    )
    opp["mid_skew_bps"] = round(skew, 2)
    opp["regime_factor"] = factor
    opp["regime_reason"] = reason
    if factor <= 0:
        return {"ok": False, "reason": reason or "still_skewed", "opportunity": opp, "mid_skew_bps": skew}
    if float(opp.get("net_bps") or 0) < min_bps:
        return {"ok": False, "reason": "edge_faded", "opportunity": opp, "mid_skew_bps": skew}
    from backend.services.exchange_technique_executor_service import residual_edge_ok

    edge = residual_edge_ok(
        net_bps=float(opp.get("net_bps") or 0),
        mid_skew_bps=float(skew or 0),
        floor_bps=_cfg_float("TECH_RESIDUAL_EDGE_BPS", 15.0),
    )
    opp["residual_bps"] = edge["residual_bps"]
    if not edge["ok"]:
        return {
            "ok": False,
            "reason": "phantom_skew_no_residual",
            "opportunity": opp,
            "mid_skew_bps": skew,
            "residual_edge": edge,
        }
    return {"ok": True, "opportunity": opp, "mid_skew_bps": skew}


def _maker_enabled() -> bool:
    return os.environ.get("LATCH_MAKER", "1").strip().lower() not in ("0", "false", "no", "off")


def _place_maker_latch(row: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
    """Park a maker sell on the rich venue while skew is still wide."""
    if not _maker_enabled():
        return {"success": False, "skipped": True, "reason": "maker_disabled"}
    if row.get("maker_order_id"):
        return {"success": True, "skipped": True, "reason": "maker_already_armed", "order_id": row.get("maker_order_id")}

    from backend.services import exchange_venue_api_service as vapi

    opp = check.get("opportunity") or {}
    sell_v = str(row.get("sell_venue") or opp.get("sell_venue") or "").lower()
    buy_v = str(row.get("buy_venue") or opp.get("buy_venue") or "").lower()
    sym = str(row.get("symbol") or opp.get("symbol") or "").upper()
    if not sell_v or not sym:
        return {"success": False, "skipped": True, "reason": "bad_route"}

    sell_bid = float(opp.get("sell_bid") or 0)
    buy_ask = float(opp.get("buy_ask") or 0)
    if sell_bid <= 0 or buy_ask <= 0:
        return {"success": False, "skipped": True, "reason": "no_price"}

    # Maker target: still above buy ask by residual floor + fee pad.
    pad_bps = _cfg_float("LATCH_MAKER_PAD_BPS", 25.0)
    target = buy_ask * (1.0 + pad_bps / 10_000.0)
    # Never chase above the current bid; sit inside the spread if possible.
    px = min(sell_bid * 0.9995, max(target, buy_ask * 1.001))
    if px <= buy_ask:
        return {"success": False, "skipped": True, "reason": "no_maker_edge"}

    bals = vapi.parse_spot_balances(sell_v, dry_run=False, force_refresh=True) or {}
    qty = float(bals.get(sym) or 0)
    notional = float(row.get("notional_usd") or 15.0)
    need_qty = notional / max(px, 1e-9)
    if qty < need_qty * 0.5:
        return {"success": False, "skipped": True, "reason": "no_sell_inventory", "have": qty, "need": need_qty}

    use_qty = min(qty * 0.95, need_qty)
    quote = vapi.venue_quote_asset(sell_v)
    order = vapi.place_limit_order(
        sell_v, sym, "sell", use_qty, px,
        dry_run=False, quote=quote,
        client_order_id=f"latch-mkr-{sym[:6]}-{int(time.time())}",
    )
    ok = bool(order.get("success"))
    _append(
        "maker_place",
        symbol=sym,
        sell_venue=sell_v,
        buy_venue=buy_v,
        price=round(px, 8),
        qty=use_qty,
        success=ok,
        error=order.get("error"),
        order_id=order.get("order_id") or order.get("id"),
    )
    return {
        "success": ok,
        "skipped": False,
        "price": round(px, 8),
        "qty": use_qty,
        "order_id": order.get("order_id") or order.get("id") or order.get("clientOrderId"),
        "error": order.get("error"),
        "raw": {k: order.get(k) for k in ("order_id", "id", "status", "error") if k in order},
    }


def run_latch_tick(*, force: bool = False) -> Dict[str, Any]:
    """Arm from hunter skew skips, then fire any latch whose skew cleared."""
    if not latch_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "latch"}

    state = _load_state()
    pending = _expire_pending(list(state.get("pending") or []))

    cand = _candidate_from_hunter()
    armed = None
    if cand and float(cand.get("mid_skew_bps") or 0) >= _cfg_float("LATCH_ARM_SKEW_BPS", 80.0):
        armed = arm_latch(**{k: cand[k] for k in (
            "symbol", "buy_venue", "sell_venue", "net_bps", "mid_skew_bps",
            "est_profit_usd", "notional_usd", "source",
        ) if k in cand})
        pending = list(_load_state().get("pending") or [])
    elif cand and float(cand.get("net_bps") or 0) >= _cfg_float("LATCH_MIN_BPS", 20.0):
        # Board candidate without skew yet — arm softly so we can wait.
        if float(cand.get("mid_skew_bps") or 0) >= _cfg_float("LATCH_SOFT_ARM_SKEW_BPS", 40.0):
            armed = arm_latch(**{k: cand[k] for k in (
                "symbol", "buy_venue", "sell_venue", "net_bps", "mid_skew_bps",
                "est_profit_usd", "notional_usd", "source",
            ) if k in cand})
            pending = list(_load_state().get("pending") or [])

    out: Dict[str, Any] = {
        "success": True,
        "limb": "latch",
        "name": "latch",
        "scanned_at": _iso(),
        "pending": len(pending),
        "armed": bool(armed and armed.get("success")),
        "fired": False,
        "maker": None,
        "skip_reason": None,
        "top": pending[0] if pending else None,
    }

    if not pending:
        out["skip_reason"] = "no_pending"
        state["pending"] = []
        state["updated_at"] = _iso()
        state["last_tick"] = {"pending": 0, "fired": False, "skip_reason": "no_pending"}
        _save_state(state)
        out["summary"] = "pending=0 fired=no skip=no_pending"
        return out

    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage
    from backend.services.exchange_profit_path_service import record_execution, record_scan
    from backend.services.exchange_closer_claw_service import note_execution_legs

    agent_id = (os.environ.get("LATCH_AGENT_ID") or "arb_latch_sniper").strip()
    min_live = _cfg_float("LATCH_MIN_LIVE_USD", 10.0)
    remaining: List[Dict[str, Any]] = []
    fired_row = None

    for row in pending:
        check = _recheck_latch(row)
        if not check.get("ok"):
            row = dict(row)
            row["last_check"] = {
                "ts": _iso(),
                "reason": check.get("reason"),
                "mid_skew_bps": check.get("mid_skew_bps"),
                "net_bps": (check.get("opportunity") or {}).get("net_bps"),
                "residual_bps": (check.get("opportunity") or {}).get("residual_bps"),
            }
            # While skewed / residual-blocked, try a maker rest on the rich venue.
            if check.get("reason") in ("still_skewed", "regime_skew_too_wide", "phantom_skew_no_residual", "regime_deweight"):
                maker = _place_maker_latch(row, check)
                row["maker"] = {
                    "ts": _iso(),
                    "success": maker.get("success"),
                    "skipped": maker.get("skipped"),
                    "reason": maker.get("reason"),
                    "price": maker.get("price"),
                    "order_id": maker.get("order_id"),
                }
                if maker.get("order_id"):
                    row["maker_order_id"] = maker.get("order_id")
                out["maker"] = row["maker"]
            remaining.append(row)
            continue

        trade_opp = check["opportunity"]
        prepared = arb.prepare_live_opportunity(
            trade_opp, configured_usd=float(trade_opp.get("notional_usd") or 15.0),
            buffer_pct=0.03, min_live_usd=min_live,
        )
        if not prepared.get("ok"):
            row = dict(row)
            row["last_check"] = {
                "ts": _iso(),
                "reason": prepared.get("reason") or "insufficient_venue_balance",
                "mid_skew_bps": check.get("mid_skew_bps"),
            }
            remaining.append(row)
            continue

        ready = prepared["opportunity"]
        path_id = record_scan(
            agent_id=agent_id,
            strategy="latch_sniper",
            best=ready,
            threshold_bps=_cfg_float("LATCH_MIN_BPS", 12.0),
            mode="live" if arb.live_enabled() else "paper",
            decision="attempt",
            notional_usd=float(ready.get("notional_usd") or 15.0),
        )
        exec_res = execute_spatial_arbitrage(ready, agent_id=agent_id)
        note_execution_legs(ready, exec_res, source="latch")
        record_execution(
            path_id=path_id,
            agent_id=agent_id,
            opp=ready,
            exec_res=exec_res,
            strategy="latch_sniper",
            threshold_bps=_cfg_float("LATCH_MIN_BPS", 12.0),
        )
        book_agent_profit(agent_id, ready, exec_res)
        _append(
            "fire",
            symbol=ready.get("symbol"),
            success=bool(exec_res.get("success")),
            net_bps=ready.get("net_bps"),
            mid_skew_bps=check.get("mid_skew_bps"),
            error=exec_res.get("error"),
        )
        if exec_res.get("success"):
            out["fired"] = True
            fired_row = {
                "symbol": ready.get("symbol"),
                "net_bps": ready.get("net_bps"),
                "mid_skew_bps": check.get("mid_skew_bps"),
                "buy_venue": ready.get("buy_venue"),
                "sell_venue": ready.get("sell_venue"),
            }
            out["trade"] = fired_row
            # Drop fired latch; keep the rest.
            continue
        row = dict(row)
        row["last_check"] = {"ts": _iso(), "reason": exec_res.get("error") or "exec_failed"}
        remaining.append(row)

    state["pending"] = remaining
    state["updated_at"] = _iso()
    state["last_tick"] = {
        "pending": len(remaining),
        "fired": out["fired"],
        "trade": fired_row,
        "armed": out["armed"],
        "skip_reason": None if out["fired"] else (remaining[0].get("last_check", {}) or {}).get("reason") if remaining else "cleared",
    }
    if out["fired"]:
        state["fire_count"] = int(state.get("fire_count") or 0) + 1
        state["last_fire_at"] = out["scanned_at"]
    _save_state(state)

    out["pending"] = len(remaining)
    out["skip_reason"] = state["last_tick"].get("skip_reason")
    out["summary"] = (
        f"pending={len(remaining)} fired={'yes' if out['fired'] else 'no'} "
        f"armed={'yes' if out['armed'] else 'no'}"
    )
    if fired_row:
        out["summary"] += f" sym={fired_row.get('symbol')} net={fired_row.get('net_bps')}"
    elif out.get("skip_reason"):
        out["summary"] += f" skip={out['skip_reason']}"
    return out
