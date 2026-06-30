"""Owner-only business control board for all trading bots.

Aggregates profit across every trading bot (internal cross-trade agents + cross-venue
arbitrage paper agents), groups them under supervisor agents, and gives the owner a
single place to calculate profit and control the business (pause/resume bots,
pause supervisors, global kill-switch, run-all tick).

All control writes go through ``/api/exchange/control-board/*`` which is admin-gated.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONTROL_PATH = os.path.join(ex._DATA_DIR, "trading_bots_control.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_controls() -> Dict[str, Any]:
    return {
        "supervisors": [
            {"id": "sup_arbitrage", "name": "Arbitrage Director",
             "role": "Executes cross-venue arbitrage bots when spreads beat fees.",
             "controls_kind": "arbitrage_paper", "enabled": True},
            {"id": "sup_crosstrade", "name": "Cross-Trade Director",
             "role": "Runs internal exchange market-making / rotation bots.",
             "controls_kind": "cross_trade", "enabled": True},
            {"id": "sup_risk", "name": "Risk Officer",
             "role": "Owns caps, velocity, and the global kill-switch.",
             "controls_kind": "risk", "enabled": True},
            {"id": "sup_profit", "name": "Profit Analyst",
             "role": "Aggregates realized/unrealized P&L and projections.",
             "controls_kind": "analytics", "enabled": True},
            {"id": "sup_treasury", "name": "Treasury Manager",
             "role": "Tracks profit accounts, wallet registry, and sweeps.",
             "controls_kind": "treasury", "enabled": True},
        ],
        "bot_overrides": {},
        "kill_switch": False,
        "updated_at": _iso(),
    }


def _load_controls() -> Dict[str, Any]:
    data = ex._read_json(_CONTROL_PATH, None)
    if not isinstance(data, dict) or not data.get("supervisors"):
        data = _default_controls()
        ex._write_json(_CONTROL_PATH, data)
    data.setdefault("bot_overrides", {})
    data.setdefault("kill_switch", False)
    return data


def _save_controls(data: Dict[str, Any]) -> None:
    data["updated_at"] = _iso()
    ex._write_json(_CONTROL_PATH, data)


def _supervisor_for_kind(controls: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    for s in controls.get("supervisors") or []:
        if s.get("controls_kind") == kind:
            return s
    return None


def _arbitrage_bots() -> List[Dict[str, Any]]:
    try:
        from backend.services.exchange_arbitrage_service import agent_accounts
        accts = agent_accounts().get("accounts") or []
    except Exception:
        accts = []
    bots = []
    for a in accts:
        bots.append({
            "id": a.get("agent_id"),
            "name": a.get("name") or a.get("agent_id"),
            "kind": "arbitrage_paper",
            "supervisor": "sup_arbitrage",
            "config_enabled": True,
            "realized_pnl_usd": round(float(a.get("realized_profit_usd") or 0), 4),
            "unrealized_pnl_usd": 0.0,
            "trade_count": int(a.get("trade_count") or 0),
            "notional_traded_usd": round(float(a.get("notional_traded_usd") or 0), 2),
            "wallet_label": a.get("wallet_label") or "",
            "last_action": a.get("last_action"),
        })
    return bots


def _cross_trade_bots() -> List[Dict[str, Any]]:
    try:
        from backend.services.crypto_exchange_agent_service import list_agents
        agents = list_agents().get("agents") or []
    except Exception:
        agents = []
    perf_map: Dict[str, Dict[str, Any]] = {}
    try:
        from backend.services.crypto_exchange_profit_agent_service import _agent_performance, _read_trades
        for row in _agent_performance(_read_trades()):
            perf_map[row.get("agent_id")] = row
    except Exception:
        perf_map = {}
    bots = []
    for ag in agents:
        aid = ag.get("id")
        perf = perf_map.get(aid, {})
        state = ag.get("state") or {}
        bots.append({
            "id": aid,
            "name": ag.get("name") or aid,
            "kind": "cross_trade",
            "supervisor": "sup_crosstrade",
            "strategy": ag.get("strategy"),
            "config_enabled": bool(ag.get("enabled", True)),
            "realized_pnl_usd": round(float(perf.get("realized_pnl_usd") or 0), 4),
            "unrealized_pnl_usd": round(float(perf.get("unrealized_pnl_usd") or 0), 4),
            "trade_count": int(perf.get("trade_count") or 0),
            "portfolio_value_usd": round(float(perf.get("portfolio_value_usd") or 0), 4),
            "last_action": state.get("last_action"),
        })
    return bots


def _effective_enabled(bot: Dict[str, Any], controls: Dict[str, Any]) -> bool:
    if controls.get("kill_switch"):
        return False
    sup = next((s for s in controls.get("supervisors") or [] if s.get("id") == bot.get("supervisor")), None)
    if sup and not sup.get("enabled", True):
        return False
    override = (controls.get("bot_overrides") or {}).get(bot.get("id"))
    if isinstance(override, dict) and "enabled" in override:
        return bool(override["enabled"])
    return bool(bot.get("config_enabled", True))


def list_bots() -> List[Dict[str, Any]]:
    controls = _load_controls()
    bots = _arbitrage_bots() + _cross_trade_bots()
    for b in bots:
        b["enabled"] = _effective_enabled(b, controls)
        b["total_pnl_usd"] = round(float(b.get("realized_pnl_usd") or 0) + float(b.get("unrealized_pnl_usd") or 0), 4)
    return bots


def business_overview() -> Dict[str, Any]:
    controls = _load_controls()
    bots = list_bots()

    total_realized = round(sum(float(b.get("realized_pnl_usd") or 0) for b in bots), 4)
    total_unrealized = round(sum(float(b.get("unrealized_pnl_usd") or 0) for b in bots), 4)
    total_trades = sum(int(b.get("trade_count") or 0) for b in bots)
    active = sum(1 for b in bots if b.get("enabled"))

    by_kind: Dict[str, Dict[str, Any]] = {}
    for b in bots:
        k = by_kind.setdefault(b["kind"], {"bot_count": 0, "profit_usd": 0.0, "trade_count": 0})
        k["bot_count"] += 1
        k["profit_usd"] = round(k["profit_usd"] + b["total_pnl_usd"], 4)
        k["trade_count"] += int(b.get("trade_count") or 0)

    supervisors = []
    for s in controls.get("supervisors") or []:
        sup_bots = [b for b in bots if b.get("supervisor") == s.get("id")]
        supervisors.append({
            **s,
            "bot_count": len(sup_bots),
            "active_bot_count": sum(1 for b in sup_bots if b.get("enabled")),
            "profit_usd": round(sum(b["total_pnl_usd"] for b in sup_bots), 4),
            "trade_count": sum(int(b.get("trade_count") or 0) for b in sup_bots),
            "bot_ids": [b["id"] for b in sup_bots],
        })

    extras: Dict[str, Any] = {}
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        from backend.services.exchange_secrets_vault_service import vault_status
        extras["arbitrage_live"] = live_enabled()
        extras["vault"] = vault_status()
    except Exception:
        pass
    try:
        from backend.services.agent_marketplace_service import sales_summary
        extras["marketplace"] = sales_summary()
    except Exception:
        pass
    try:
        from backend.services.exchange_treasury_service import treasury_status
        from backend.services.exchange_arbitrage_service import live_enabled
        tre = treasury_status()
        extras["treasury"] = tre
        if not live_enabled():
            extras["paper_mode"] = True
            extras["paper_projection_cap_usd"] = round(float(tre.get("ledger_stashed_usd_paper") or 0), 4)
            extras["monthly_projection_note"] = (
                "Paper mode — projections capped to on-ledger paper stash until live gates are on."
            )
    except Exception:
        pass

    monthly_projection = round((total_realized + total_unrealized), 4)
    if extras.get("paper_mode"):
        cap = float(extras.get("paper_projection_cap_usd") or 0)
        if cap > 0:
            monthly_projection = min(monthly_projection, cap)

    return {
        "success": True,
        "generated_at": _iso(),
        "kill_switch": bool(controls.get("kill_switch")),
        "totals": {
            "bot_count": len(bots),
            "active_bots": active,
            "total_realized_pnl_usd": total_realized,
            "total_unrealized_pnl_usd": total_unrealized,
            "total_profit_usd": round(total_realized + total_unrealized, 4),
            "trade_count": total_trades,
            "monthly_projection_usd": monthly_projection,
        },
        "by_kind": by_kind,
        "supervisors": supervisors,
        "bots": sorted(bots, key=lambda b: b["total_pnl_usd"], reverse=True),
        **extras,
    }


def set_bot_enabled(bot_id: str, enabled: bool) -> Dict[str, Any]:
    bot_id = (bot_id or "").strip()
    if not bot_id:
        return {"success": False, "error": "missing_bot_id"}
    controls = _load_controls()
    controls.setdefault("bot_overrides", {})[bot_id] = {"enabled": bool(enabled), "updated_at": _iso()}
    _save_controls(controls)
    ex._audit("control_board_bot_toggle", user_id="owner", bot_id=bot_id, enabled=bool(enabled))
    return {"success": True, "bot_id": bot_id, "enabled": bool(enabled)}


def set_supervisor_enabled(supervisor_id: str, enabled: bool) -> Dict[str, Any]:
    supervisor_id = (supervisor_id or "").strip()
    controls = _load_controls()
    found = False
    for s in controls.get("supervisors") or []:
        if s.get("id") == supervisor_id:
            s["enabled"] = bool(enabled)
            found = True
            break
    if not found:
        return {"success": False, "error": "supervisor_not_found"}
    _save_controls(controls)
    ex._audit("control_board_supervisor_toggle", user_id="owner", supervisor_id=supervisor_id, enabled=bool(enabled))
    return {"success": True, "supervisor_id": supervisor_id, "enabled": bool(enabled)}


def set_kill_switch(on: bool) -> Dict[str, Any]:
    controls = _load_controls()
    controls["kill_switch"] = bool(on)
    _save_controls(controls)
    ex._audit("control_board_kill_switch", user_id="owner", on=bool(on))
    return {"success": True, "kill_switch": bool(on)}


def run_all_bots(force: bool = False) -> Dict[str, Any]:
    controls = _load_controls()
    if controls.get("kill_switch"):
        return {"success": False, "error": "kill_switch_active"}

    results: Dict[str, Any] = {}
    sup_arb = _supervisor_for_kind(controls, "arbitrage_paper")
    sup_cross = _supervisor_for_kind(controls, "cross_trade")

    if sup_arb and sup_arb.get("enabled", True):
        try:
            from backend.services.exchange_arbitrage_service import run_paper_tick
            results["arbitrage"] = run_paper_tick()
        except Exception as exc:
            results["arbitrage"] = {"success": False, "error": str(exc)}
        try:
            from backend.services.exchange_ai_trading_service import run_ai_tick
            results["ai_trading"] = run_ai_tick()
        except Exception as exc:
            results["ai_trading"] = {"success": False, "error": str(exc)}
    else:
        results["arbitrage"] = {"success": False, "error": "supervisor_paused"}

    if sup_cross and sup_cross.get("enabled", True):
        try:
            from backend.services.crypto_exchange_agent_service import tick
            results["cross_trade"] = tick(force=force)
        except Exception as exc:
            results["cross_trade"] = {"success": False, "error": str(exc)}
    else:
        results["cross_trade"] = {"success": False, "error": "supervisor_paused"}

    sup_ext = _supervisor_for_kind(controls, "extended_profit")
    if sup_ext and sup_ext.get("enabled", True):
        try:
            from backend.services.exchange_extended_profit_service import run_extended_profit_tick
            profile = os.environ.get("EXCHANGE_PROFIT_PROFILE", "max")
            results["extended_profit"] = run_extended_profit_tick(profile=profile)
        except Exception as exc:
            results["extended_profit"] = {"success": False, "error": str(exc)}
    else:
        results["extended_profit"] = {"success": False, "error": "supervisor_paused"}

    ex._audit("control_board_run_all", user_id="owner",
              arbitrage_ok=bool(results.get("arbitrage", {}).get("success")),
              cross_trade_ok=bool(results.get("cross_trade", {}).get("success")))
    return {"success": True, "ran_at": _iso(), "results": results}
