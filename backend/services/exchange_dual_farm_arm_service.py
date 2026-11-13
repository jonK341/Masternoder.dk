"""Dedicated live dual-farm arm: Binance ↔ NonKYC fast arb with micro-size + prefund.

Focused on the path that already prints real fills (``arb_live_dual_farm`` /
``fleet_extended_profit_fast`` / ``fast_arb_rescan``):

* venues locked to ``binance`` + ``nonkyc`` (no XeggeX/OKX noise)
* priority symbols ADA / LINK / BNB (24h live winners) + pair-search hot list
* drops ``internal`` sell-venue marks so paper pegs cannot starve the arm
* sizes to live balances (micro floor)
* optional quote prefund: sell raise inventory on the buy venue when an edge
  qualifies but quote is short

Enable with ``DUAL_FARM_ARM_ENABLED=1`` (default on when live arb is on).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_STATE_PATH = os.path.join(ex._DATA_DIR, "dual_farm_arm_state.json")
_DEFAULT_SYMBOLS = ["ADA", "LINK", "BNB", "XRP", "SOL", "AVAX"]
_EXTERNAL = ("binance", "nonkyc")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def dual_farm_arm_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("dual_farm"):
            return False
    except Exception:
        pass
    raw = os.environ.get("DUAL_FARM_ARM_ENABLED", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    # Default: follow live arb gate so the arm rides with the profit daemon.
    return bool(arb.live_enabled())


def _cfg_float(env_key: str, default: float) -> float:
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _cfg_int(env_key: str, default: int) -> int:
    return int(_cfg_float(env_key, float(default)))


def _priority_symbols() -> List[str]:
    raw = os.environ.get("DUAL_FARM_SYMBOLS", "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    hot: List[str] = []
    try:
        from backend.services.exchange_profit_pair_search_service import enabled, run_profit_pair_search

        if enabled():
            search = run_profit_pair_search(venues=list(_EXTERNAL))
            hot = [str(s).upper() for s in (search.get("hot_symbols") or []) if s]
    except Exception:
        pass
    # Proven live winners first, then hot, then defaults.
    ordered: List[str] = []
    for sym in ["ADA", "LINK", "BNB"] + hot + _DEFAULT_SYMBOLS:
        if sym not in ordered:
            ordered.append(sym)
    return ordered[:12]


def _is_external_opp(opp: Dict[str, Any]) -> bool:
    buy = str(opp.get("buy_venue") or "").lower()
    sell = str(opp.get("sell_venue") or "").lower()
    return buy in _EXTERNAL and sell in _EXTERNAL and buy != sell


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _prefund_enabled() -> bool:
    return os.environ.get("DUAL_FARM_PREFUND", "1").strip().lower() not in ("0", "false", "no", "off")


def _raise_quote_on_buy_venue(
    buy_venue: str,
    *,
    need_usd: float,
    raise_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sell raise inventory on ``buy_venue`` to free quote for the arb buy leg."""
    from backend.services import exchange_venue_api_service as vapi

    quote = vapi.venue_quote_asset(buy_venue)
    bals = vapi.parse_spot_balances(buy_venue, dry_run=False, force_refresh=True) or {}
    free_q = float(bals.get(quote) or 0)
    if free_q >= need_usd:
        return {"success": True, "skipped": True, "reason": "already_funded", "free_quote": free_q}

    gap = max(0.0, need_usd - free_q)
    # Cap prefund — keep micro, don't dump the book.
    max_raise = _cfg_float("DUAL_FARM_PREFUND_MAX_USD", 25.0)
    target = min(gap * 1.05, max_raise)
    if target < 5.0:
        return {"success": False, "reason": "gap_too_small", "gap_usd": round(gap, 2)}

    candidates = raise_symbols or ["ADA", "LINK", "BNB", "XRP", "SOL"]
    for sym in candidates:
        qty_coin = float(bals.get(sym) or 0)
        if qty_coin <= 0:
            continue
        tick = conn.fetch_ticker(buy_venue, sym) or {}
        bid = float(tick.get("bid") or 0)
        if bid <= 0:
            continue
        inv_usd = qty_coin * bid
        # Leave a crumb; don't strip priority inventory bare.
        sell_usd = min(target, inv_usd * 0.45)
        if sell_usd < 5.0:
            continue
        sell_qty = round((sell_usd / bid) * 0.995, 6)
        if sell_qty <= 0:
            continue
        order = vapi.place_market_order(
            buy_venue, sym, "sell", sell_qty, dry_run=False, quote=quote,
        )
        ok = bool(order.get("success"))
        vapi.invalidate_venue_balance_cache(buy_venue)
        return {
            "success": ok,
            "action": "prefund_sell",
            "venue": buy_venue,
            "symbol": sym,
            "sell_qty": sell_qty,
            "sell_usd": round(sell_usd, 2),
            "order_success": ok,
            "error": order.get("error") if not ok else None,
        }
    return {"success": False, "reason": "no_raise_inventory", "need_usd": round(need_usd, 2)}


def run_dual_farm_arm_tick(*, force: bool = False) -> Dict[str, Any]:
    """One dual-farm arm tick: scan → (optional prefund) → prepare → execute."""
    if not dual_farm_arm_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled"}

    min_bps = _cfg_float("DUAL_FARM_MIN_BPS", 12.0)
    notional = _cfg_float("DUAL_FARM_NOTIONAL_USD", 15.0)
    min_live = _cfg_float("DUAL_FARM_MIN_LIVE_USD", 10.0)
    max_exec = _cfg_int("DUAL_FARM_MAX_EXEC", 1)
    agent_id = (os.environ.get("DUAL_FARM_AGENT_ID") or "arb_live_dual_farm").strip()
    symbols = _priority_symbols()
    venues = list(_EXTERNAL)

    from backend.services import exchange_venue_api_service as vapi

    vapi.refresh_venue_balances(venues, force=True)
    scan = arb.scan_opportunities(symbols=symbols, venues=venues, notional_usd=notional)
    opps = [
        o for o in (scan.get("opportunities") or [])
        if _is_external_opp(o)
        and float(o.get("net_bps") or 0) >= min_bps
        and float(o.get("est_profit_usd") or 0) > 0
    ]
    opps.sort(key=lambda o: float(o.get("net_bps") or 0), reverse=True)

    out: Dict[str, Any] = {
        "success": True,
        "arm": "dual_farm",
        "scanned_at": _iso(),
        "min_bps": min_bps,
        "notional_usd": notional,
        "symbols": symbols,
        "opportunity_count": len(scan.get("opportunities") or []),
        "external_qualifying": len(opps),
        "top": None,
        "executed": False,
        "prefund": None,
        "skip_reason": None,
    }
    if opps:
        top = opps[0]
        out["top"] = {
            "symbol": top.get("symbol"),
            "buy_venue": top.get("buy_venue"),
            "sell_venue": top.get("sell_venue"),
            "net_bps": top.get("net_bps"),
            "est_profit_usd": top.get("est_profit_usd"),
        }
    else:
        # Still report best external even if below threshold.
        all_ext = [o for o in (scan.get("opportunities") or []) if _is_external_opp(o)]
        all_ext.sort(key=lambda o: float(o.get("net_bps") or 0), reverse=True)
        if all_ext:
            top = all_ext[0]
            out["top"] = {
                "symbol": top.get("symbol"),
                "buy_venue": top.get("buy_venue"),
                "sell_venue": top.get("sell_venue"),
                "net_bps": top.get("net_bps"),
                "est_profit_usd": top.get("est_profit_usd"),
                "below_threshold": True,
            }
        out["skip_reason"] = "no_qualifying_external_edge"
        _persist_tick(out)
        return out

    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage
    from backend.services.exchange_profit_path_service import record_execution, record_scan

    for opp in opps[: max(1, max_exec)]:
        try:
            from backend.services.exchange_technique_executor_service import residual_edge_ok

            edge = residual_edge_ok(
                net_bps=float(opp.get("net_bps") or 0),
                mid_skew_bps=float(opp.get("mid_skew_bps") or 0),
            )
            if not edge["ok"]:
                out["skip_reason"] = "phantom_skew_no_residual"
                out["residual_edge"] = edge
                continue
        except Exception:
            pass
        prepared = arb.prepare_live_opportunity(
            opp, configured_usd=notional, buffer_pct=0.03, min_live_usd=min_live,
        )
        if not prepared.get("ok") and _prefund_enabled():
            need = max(min_live, float(prepared.get("requested_usd") or notional))
            buy_v = str(opp.get("buy_venue") or "")
            # Prefund only helps the buy-venue quote leg.
            pref = _raise_quote_on_buy_venue(buy_v, need_usd=need, raise_symbols=symbols)
            out["prefund"] = pref
            if pref.get("success") and not pref.get("skipped"):
                time.sleep(1.0)
                vapi.refresh_venue_balances(venues, force=True)
                prepared = arb.prepare_live_opportunity(
                    opp, configured_usd=notional, buffer_pct=0.03, min_live_usd=min_live,
                )

        if not prepared.get("ok"):
            out["skip_reason"] = str(prepared.get("reason") or "insufficient_venue_balance")
            out["max_funded_usd"] = prepared.get("max_funded_usd")
            continue

        trade_opp = prepared["opportunity"]
        path_id = record_scan(
            agent_id=agent_id,
            strategy="dual_farm_arm",
            best=trade_opp,
            threshold_bps=min_bps,
            mode="live" if arb.live_enabled() else "paper",
            decision="attempt",
            notional_usd=float(trade_opp.get("notional_usd") or notional),
            venues=venues,
        )
        exec_res = execute_spatial_arbitrage(trade_opp, agent_id=agent_id)
        try:
            from backend.services.exchange_closer_claw_service import note_execution_legs

            note_execution_legs(trade_opp, exec_res, source="dual_farm")
        except Exception:
            pass
        record_execution(
            path_id=path_id,
            agent_id=agent_id,
            opp=trade_opp,
            exec_res=exec_res,
            strategy="dual_farm_arm",
            threshold_bps=min_bps,
            venues=venues,
        )
        try:
            from backend.services.exchange_profit_baseline_service import record_arb_baseline

            record_arb_baseline(trade_opp, exec_res, source="dual_farm_arm", agent_id=agent_id)
        except Exception:
            pass
        book_agent_profit(agent_id, trade_opp, exec_res)
        # Also credit extended-fast fleet id when configured (same sleeve).
        fleet_id = (os.environ.get("DUAL_FARM_FLEET_AGENT_ID") or "fleet_extended_profit_fast").strip()
        if fleet_id and fleet_id != agent_id and exec_res.get("success"):
            try:
                book_agent_profit(fleet_id, trade_opp, exec_res)
            except Exception:
                pass

        out["executed"] = bool(exec_res.get("success"))
        out["mode"] = exec_res.get("mode")
        out["profit_path_id"] = path_id
        out["trade"] = {
            "symbol": trade_opp.get("symbol"),
            "net_bps": trade_opp.get("net_bps"),
            "notional_usd": trade_opp.get("notional_usd"),
            "buy_venue": trade_opp.get("buy_venue"),
            "sell_venue": trade_opp.get("sell_venue"),
        }
        if exec_res.get("success"):
            out["skip_reason"] = None
            _persist_tick(out)
            return out
        out["skip_reason"] = str(exec_res.get("error") or "execution_failed")

    _persist_tick(out)
    return out


def _persist_tick(out: Dict[str, Any]) -> None:
    state = _load_state()
    state.update({
        "updated_at": _iso(),
        "last_tick": {
            "scanned_at": out.get("scanned_at"),
            "external_qualifying": out.get("external_qualifying"),
            "top": out.get("top"),
            "executed": out.get("executed"),
            "skip_reason": out.get("skip_reason"),
            "prefund": out.get("prefund"),
            "trade": out.get("trade"),
        },
    })
    if out.get("executed"):
        state["last_exec_at"] = out.get("scanned_at")
        state["last_exec"] = out.get("trade")
        state["exec_count"] = int(state.get("exec_count") or 0) + 1
    _save_state(state)


def dual_farm_arm_status() -> Dict[str, Any]:
    state = _load_state()
    return {
        "success": True,
        "enabled": dual_farm_arm_enabled(),
        "live": arb.live_enabled(),
        "min_bps": _cfg_float("DUAL_FARM_MIN_BPS", 12.0),
        "notional_usd": _cfg_float("DUAL_FARM_NOTIONAL_USD", 15.0),
        "prefund": _prefund_enabled(),
        "symbols": _priority_symbols(),
        "state": state,
    }
