"""Venue funding and agent trade rotation for live spatial arbitrage.

- ``sell_coins_to_fund_venue`` — sell altcoin inventory on a venue to raise USDT/DOGE/etc.
- ``fund_venue_legs_for_symbol`` — prefund buy/sell legs before an arb attempt.
- ``restore_post_trade_inventory`` — unwind legs after a fill so the next agent can trade.
- ``run_agent_trade_rotation_cycle`` — round-robin: one agent per tick, fund → trade → restore → next.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_venue_api_service as vapi
from backend.services.exchange_profit_path_service import load_config
from backend.services.exchange_swap_rotation_service import (
    _external_buy_action,
    _prefund_action_for_short_leg,
    _quote_shortfall_action,
    _venue_rotation_eligible,
    analyze_funding_gaps,
    execute_rotation,
    rotation_auto_execute_enabled,
    rotation_live_enabled,
)

_STATE_PATH = os.path.join(ex._DATA_DIR, "agent_trade_rotation_state.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def agent_rotation_enabled() -> bool:
    cfg = load_config()
    if cfg.get("agent_rotation_enabled") is True:
        return True
    return os.environ.get("EXCHANGE_AGENT_ROTATION", "").strip().lower() in ("1", "true", "yes", "on")


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    state["updated_at"] = _iso()
    ex._write_json(_STATE_PATH, state)


def rotation_agent_ids() -> List[str]:
    """Ordered agent ids participating in round-robin rotation."""
    cfg = load_config()
    env_ids = os.environ.get("EXCHANGE_ROTATION_AGENTS", "").strip()
    if env_ids:
        return [s.strip() for s in env_ids.split(",") if s.strip()]
    configured = cfg.get("rotation_agent_ids")
    if isinstance(configured, list) and configured:
        return [str(a) for a in configured if a]

    from backend.services import external_exchange_connector_service as conn

    ids: List[str] = []
    for agent in conn.load_connectors_config().get("arbitrage_agents") or []:
        if not isinstance(agent, dict) or not agent.get("id"):
            continue
        venues = [str(v).lower() for v in (agent.get("venues") or [])]
        if "binance" in venues and "nonkyc" in venues:
            ids.append(str(agent["id"]))
    return ids or ["arb_live_dual_farm"]


def rotation_status() -> Dict[str, Any]:
    state = _load_state()
    agent_ids = rotation_agent_ids()
    idx = int(state.get("current_index") or 0) % max(len(agent_ids), 1)
    return {
        "success": True,
        "enabled": agent_rotation_enabled(),
        "rotation_live_enabled": rotation_live_enabled(),
        "agent_ids": agent_ids,
        "current_index": idx,
        "current_agent_id": agent_ids[idx] if agent_ids else None,
        "last_trade": state.get("last_trade"),
        "updated_at": state.get("updated_at"),
    }


def sell_coins_to_fund_venue(
    venue_id: str,
    target_asset: str,
    amount_usd: float,
    *,
    dry_run: bool = True,
    reason: str = "",
) -> Dict[str, Any]:
    """Sell altcoins on *venue_id* to raise *target_asset* (USDT, DOGE, USDC, …)."""
    venue = str(venue_id or "").lower()
    target = str(target_asset or vapi.venue_quote_asset(venue)).upper()
    usd = round(max(5.0, float(amount_usd or 0)), 2)
    if not venue:
        return {"success": False, "error": "venue_required"}
    if usd <= 0:
        return {"success": False, "error": "invalid_amount"}
    if not _venue_rotation_eligible(venue):
        return {"success": False, "error": "venue_not_rotation_eligible", "venue_id": venue}

    action = _quote_shortfall_action(
        venue,
        target,
        usd,
        reason=reason or f"Sell coins to fund {venue} {target}",
        priority="high",
        score=12.0,
        top25=["venue_funding", "skip_reason_funding"],
    )
    if not action:
        return {
            "success": False,
            "error": "no_sellable_inventory",
            "venue_id": venue,
            "target_asset": target,
            "amount_usd": usd,
        }

    if not dry_run and str(action.get("type") or "").startswith("external_market") and not rotation_live_enabled():
        return {
            "success": False,
            "error": "rotation_live_off",
            "action": action,
            "hint": "Set EXCHANGE_ROTATION_LIVE=1 or rotation_live_enabled in PPP config.",
        }

    exec_res = execute_rotation(action, dry_run=dry_run)
    return {
        "success": bool(exec_res.get("success") or exec_res.get("already_applied")),
        "dry_run": bool(exec_res.get("dry_run", dry_run)),
        "venue_id": venue,
        "target_asset": target,
        "amount_usd": usd,
        "action": action,
        "execution": exec_res,
    }


def fund_venue_legs_for_symbol(
    agent_id: str,
    symbol: str,
    notional_usd: float = 0,
    *,
    dry_run: bool = True,
    max_actions: int = 2,
) -> Dict[str, Any]:
    """Prefund short buy/sell legs for an agent's arb route."""
    sym = str(symbol or "").upper()
    if not sym:
        return {"success": False, "error": "symbol_required"}

    gaps = analyze_funding_gaps(agent_id, sym, float(notional_usd or 0))
    if gaps.get("funded_ok"):
        return {"success": True, "already_funded": True, "gaps": gaps, "actions": []}

    short_legs = list(gaps.get("short_legs") or [])
    if not short_legs:
        return {"success": False, "error": "no_short_legs", "gaps": gaps}

    executed: List[Dict[str, Any]] = []
    for leg in short_legs[: max(1, int(max_actions))]:
        venue = str(leg.get("venue_id") or "")
        if venue and not _venue_rotation_eligible(venue):
            continue
        action = _prefund_action_for_short_leg(gaps, leg, score=8.0, top25=["venue_funding", "agent_rotation"])
        if not action:
            if str(leg.get("leg") or "") == "buy":
                quote = str(leg.get("asset") or vapi.venue_quote_asset(venue)).upper()
                need = max(5.0, float(leg.get("need") or 0) - float(leg.get("free") or 0))
                sell_res = sell_coins_to_fund_venue(venue, quote, need, dry_run=dry_run)
                executed.append({"leg": leg, "sell_to_fund": sell_res})
            continue

        if not dry_run and str(action.get("type") or "").startswith("external_market") and not rotation_live_enabled():
            executed.append({"leg": leg, "skipped": True, "reason": "rotation_live_off", "action": action})
            continue

        exec_res = execute_rotation(action, dry_run=dry_run)
        executed.append({"leg": leg, "action": action, "execution": exec_res})

    funded_after = analyze_funding_gaps(agent_id, sym, float(gaps.get("notional_usd") or notional_usd or 0))
    ok = bool(funded_after.get("funded_ok")) or any(
        bool(row.get("execution", {}).get("success") or row.get("sell_to_fund", {}).get("success"))
        for row in executed
    )
    return {
        "success": ok,
        "agent_id": agent_id,
        "symbol": sym,
        "funded_ok": bool(funded_after.get("funded_ok")),
        "gaps_before": gaps,
        "gaps_after": funded_after,
        "actions": executed,
    }


def restore_post_trade_inventory(
    *,
    symbol: str,
    buy_venue: str,
    sell_venue: str,
    notional_usd: float,
    buy_ask: float = 0,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Return venue inventory to pre-trade shape so another agent can arb."""
    sym = str(symbol or "").upper()
    buy_v = str(buy_venue or "").lower()
    sell_v = str(sell_venue or "").lower()
    notion = round(max(10.0, float(notional_usd or 0)), 2)
    if not sym or not buy_v or not sell_v:
        return {"success": False, "error": "invalid_route"}

    px = float(buy_ask or 0)
    if px <= 0:
        px = float(ex._price_usd(sym) or 0)
    if px <= 0:
        return {"success": False, "error": "no_price", "symbol": sym}

    results: List[Dict[str, Any]] = []

    if buy_v != "internal" and _venue_rotation_eligible(buy_v):
        sell_spec = vapi.market_order_for_leg(buy_v, "sell", sym, notion)
        if sell_spec.get("ok"):
            sell_action = _external_buy_action(
                buy_v,
                sym,
                "sell",
                amount_usd=notion,
                qty=float(sell_spec["quantity"]),
                reason=f"Restore {buy_v} quote after arb ({sym})",
                priority="high",
                score=6.0,
                top25=["agent_rotation", "post_trade_restore"],
                market=sell_spec.get("market"),
                quote=sell_spec.get("quote"),
            )
            sell_action["label"] = f"Restore {buy_v}: sell {sym} ~${notion:.0f}"
            if not dry_run and not rotation_live_enabled():
                results.append({"venue": buy_v, "side": "sell", "skipped": True, "reason": "rotation_live_off"})
            else:
                exec_res = execute_rotation(sell_action, dry_run=dry_run)
                results.append({"venue": buy_v, "side": "sell", "action": sell_action, "execution": exec_res})
        else:
            results.append({"venue": buy_v, "side": "sell", "error": sell_spec.get("error")})

    if sell_v != "internal" and _venue_rotation_eligible(sell_v):
        buy_spec = vapi.market_order_for_leg(sell_v, "buy", sym, notion)
        if buy_spec.get("ok"):
            buy_action = _external_buy_action(
                sell_v,
                sym,
                "buy",
                amount_usd=notion,
                qty=float(buy_spec["quantity"]),
                reason=f"Restore {sell_v} base after arb ({sym})",
                priority="high",
                score=6.0,
                top25=["agent_rotation", "post_trade_restore"],
                market=buy_spec.get("market"),
                quote=buy_spec.get("quote"),
            )
            buy_action["label"] = f"Restore {sell_v}: buy {sym} ~${notion:.0f}"
            if not dry_run and not rotation_live_enabled():
                results.append({"venue": sell_v, "side": "buy", "skipped": True, "reason": "rotation_live_off"})
            else:
                exec_res = execute_rotation(buy_action, dry_run=dry_run)
                results.append({"venue": sell_v, "side": "buy", "action": buy_action, "execution": exec_res})
        else:
            results.append({"venue": sell_v, "side": "buy", "error": buy_spec.get("error")})

    success = all(
        bool(r.get("execution", {}).get("success") or r.get("skipped"))
        for r in results
        if "error" not in r
    ) and bool(results)
    return {
        "success": success,
        "symbol": sym,
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "notional_usd": notion,
        "restored_at": _iso(),
        "legs": results,
    }


def _advance_rotation(state: Dict[str, Any], agent_ids: List[str]) -> None:
    if not agent_ids:
        return
    idx = int(state.get("current_index") or 0)
    state["current_index"] = (idx + 1) % len(agent_ids)
    state.pop("pending_restore", None)


def run_agent_trade_rotation_cycle(
    exchange_res: Optional[Dict[str, Any]] = None,
    *,
    dry_run: Optional[bool] = None,
    force: bool = False,
    hot_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """One round-robin cycle: optional restore → fund → single-agent arb → restore → next agent."""
    if not force and not agent_rotation_enabled():
        return {"skipped": True, "reason": "agent_rotation_disabled"}

    agent_ids = rotation_agent_ids()
    if not agent_ids:
        return {"skipped": True, "reason": "no_rotation_agents"}

    state = _load_state()
    idx = int(state.get("current_index") or 0) % len(agent_ids)
    agent_id = agent_ids[idx]
    live_dry = False if dry_run is False else (dry_run is True or not rotation_live_enabled())

    pending = state.get("pending_restore")
    if isinstance(pending, dict) and pending.get("executed"):
        restore_res = restore_post_trade_inventory(
            symbol=str(pending.get("symbol") or ""),
            buy_venue=str(pending.get("buy_venue") or ""),
            sell_venue=str(pending.get("sell_venue") or ""),
            notional_usd=float(pending.get("notional_usd") or 0),
            buy_ask=float(pending.get("buy_ask") or 0),
            dry_run=live_dry,
        )
        state["last_restore"] = restore_res
        state.pop("pending_restore", None)
        _advance_rotation(state, agent_ids)
        idx = int(state.get("current_index") or 0) % len(agent_ids)
        agent_id = agent_ids[idx]
        _save_state(state)
        if not force and restore_res.get("success"):
            return {
                "phase": "restore",
                "success": True,
                "restored_for_agent": pending.get("agent_id"),
                "next_agent_id": agent_id,
                "restore": restore_res,
            }

    from backend.services.exchange_arbitrage_service import run_paper_tick

    tick_res = run_paper_tick(active_agent_id=agent_id, hot_symbols=hot_symbols)
    arb = tick_res if isinstance(tick_res, dict) else {}
    actions = list(arb.get("actions") or [])
    action = actions[0] if actions else {}
    executed = bool(action.get("executed"))
    best = action.get("best") if isinstance(action.get("best"), dict) else {}

    fund_res: Optional[Dict[str, Any]] = None
    if not executed and best.get("symbol"):
        skip = str(action.get("reason") or "")
        if "insufficient" in skip.lower() or not arb.get("success"):
            fund_res = fund_venue_legs_for_symbol(
                agent_id,
                str(best.get("symbol") or ""),
                float(best.get("notional_usd") or 0),
                dry_run=live_dry,
            )
            if fund_res.get("funded_ok") or fund_res.get("success"):
                tick_res = run_paper_tick(active_agent_id=agent_id, hot_symbols=hot_symbols)
                arb = tick_res if isinstance(tick_res, dict) else {}
                actions = list(arb.get("actions") or [])
                action = actions[0] if actions else {}
                executed = bool(action.get("executed"))
                best = action.get("best") if isinstance(action.get("best"), dict) else {}

    if executed and best:
        restore_res = restore_post_trade_inventory(
            symbol=str(best.get("symbol") or ""),
            buy_venue=str(best.get("buy_venue") or ""),
            sell_venue=str(best.get("sell_venue") or ""),
            notional_usd=float(best.get("notional_usd") or action.get("notional_usd") or 0),
            buy_ask=float(best.get("buy_ask") or 0),
            dry_run=live_dry,
        )
        state["last_trade"] = {
            "agent_id": agent_id,
            "symbol": best.get("symbol"),
            "buy_venue": best.get("buy_venue"),
            "sell_venue": best.get("sell_venue"),
            "notional_usd": best.get("notional_usd"),
            "executed": True,
            "restored": bool(restore_res.get("success")),
            "at": _iso(),
        }
        state["last_restore"] = restore_res
        _advance_rotation(state, agent_ids)
        next_agent = agent_ids[int(state.get("current_index") or 0) % len(agent_ids)]
    else:
        if executed:
            state["pending_restore"] = {
                "agent_id": agent_id,
                "symbol": best.get("symbol"),
                "buy_venue": best.get("buy_venue"),
                "sell_venue": best.get("sell_venue"),
                "notional_usd": best.get("notional_usd"),
                "buy_ask": best.get("buy_ask"),
                "executed": True,
            }
        next_agent = agent_ids[(idx + 1) % len(agent_ids)]
        if not executed and rotation_auto_execute_enabled() and best.get("symbol"):
            sell_coins_to_fund_venue(
                str(best.get("buy_venue") or "binance"),
                vapi.venue_quote_asset(str(best.get("buy_venue") or "binance")),
                float(best.get("notional_usd") or 25),
                dry_run=live_dry,
                reason=f"Rotation fund for {agent_id}",
            )

    state["last_cycle"] = {
        "agent_id": agent_id,
        "executed": executed,
        "reason": action.get("reason"),
        "at": _iso(),
    }
    _save_state(state)

    out: Dict[str, Any] = {
        "success": True,
        "phase": "trade",
        "agent_id": agent_id,
        "executed": executed,
        "next_agent_id": next_agent,
        "arb": arb,
        "rotation_status": rotation_status(),
    }
    if fund_res:
        out["fund"] = fund_res
    if executed and state.get("last_restore"):
        out["restore"] = state.get("last_restore")
    if exchange_res is not None:
        plat = exchange_res.setdefault("platform", {})
        results = plat.setdefault("results", {})
        results["agent_rotation"] = {k: v for k, v in out.items() if k != "arb"}
    return out
