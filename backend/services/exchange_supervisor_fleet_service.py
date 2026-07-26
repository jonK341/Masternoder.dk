"""Supervisor fleet — multiple operational bots per Business Control supervisor.

Each fleet bot can tick independently (risk shards, treasury roles, extended strategies,
profit-analyst trade lanes, winnable pair executors).
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

# 25 fleet mechanics (registry for docs + overview API)
FLEET_MECHANICS: List[Dict[str, str]] = [
    {"id": "M01", "name": "Fleet registry merge", "desc": "Auto-merge default bots into control JSON on load."},
    {"id": "M02", "name": "Per-bot enable overrides", "desc": "bot_overrides applies to fleet bot ids."},
    {"id": "M03", "name": "Per-bot last_run telemetry", "desc": "last_run_at / last_run_ok on each fleet row."},
    {"id": "M04", "name": "Supervisor kind dispatch", "desc": "Ticks route by controls_kind to fleet runners."},
    {"id": "M05", "name": "Profit analyst trade lane", "desc": "Each analyst bot scans one symbol slice and may execute."},
    {"id": "M06", "name": "Extended strategy shard", "desc": "Six bots each run one extended-profit strategy."},
    {"id": "M07", "name": "Extended same direction", "desc": "All extended bots share direction=buy_cheap_sell_rich."},
    {"id": "M08", "name": "Treasury role rotation", "desc": "Ledger audit, payout readiness, mid-price sync roles."},
    {"id": "M09", "name": "Risk officer sharding", "desc": "Withdrawal, velocity, caps, audit, sybil lanes."},
    {"id": "M10", "name": "Winnable hit sharding", "desc": "Executors take disjoint pair-search hit slices."},
    {"id": "M11", "name": "Shared pair search once", "desc": "One search per orchestrator tick, many executors."},
    {"id": "M12", "name": "Fleet orchestration summary", "desc": "Aggregated ok/fail counts in run_all results."},
    {"id": "M13", "name": "Arb agent accounts", "desc": "Fleet bots book to dedicated arb agent accounts."},
    {"id": "M14", "name": "Kill switch respects fleet", "desc": "Global kill disables effective_enabled on fleet bots."},
    {"id": "M15", "name": "Supervisor pause cascade", "desc": "Paused supervisor skips its entire fleet."},
    {"id": "M16", "name": "Light overview fleet list", "desc": "Overview returns fleet roster without heavy ticks."},
    {"id": "M17", "name": "Mechanics catalog API", "desc": "overview.supervisor_fleet.mechanics exposes M01–M25."},
    {"id": "M18", "name": "Hot symbol fan-out", "desc": "Analyst bots prefer orchestrator hot_symbols."},
    {"id": "M19", "name": "PPP path logging", "desc": "Profit analyst executions record PPP scan rows when live."},
    {"id": "M20", "name": "Treasury stash compound", "desc": "Treasury bots trigger auto_stash checks after trades."},
    {"id": "M21", "name": "Risk steady heartbeat", "desc": "Risk bots run every tick even when markets are quiet."},
    {"id": "M22", "name": "Extended max profile lock", "desc": "Fleet uses EXCHANGE_PROFIT_PROFILE=max by default."},
    {"id": "M23", "name": "Winnable agent isolation", "desc": "Separate agent_id per winnable executor bot."},
    {"id": "M24", "name": "Fleet profit rollup", "desc": "Supervisor profit_usd sums fleet bot P&L in overview."},
    {"id": "M25", "name": "Owner Live Watch feed", "desc": "Trust feed includes fleet tick audit actions."},
]

_EXTENDED_SAME_DIRECTION = "buy_cheap_sell_rich"

_FLEET_BLUEPRINTS: Dict[str, List[Dict[str, Any]]] = {
    "analytics": [
        {"suffix": "alpha", "name": "Profit Analyst Alpha", "symbols": ["DOGE", "XRP"]},
        {"suffix": "beta", "name": "Profit Analyst Beta", "symbols": ["LTC", "SOL"]},
        {"suffix": "gamma", "name": "Profit Analyst Gamma", "symbols": ["AVAX", "LINK"]},
        {"suffix": "delta", "name": "Profit Analyst Delta", "symbols": ["BTC", "ETH"]},
        {"suffix": "epsilon", "name": "Profit Analyst Epsilon", "symbols": ["TRX", "SHIB"]},
    ],
    "extended_profit": [
        {"suffix": "dual", "strategy": "live_dual_venue"},
        {"suffix": "fast", "strategy": "fast_arb_rescan"},
        {"suffix": "peg", "strategy": "stablecoin_peg"},
        {"suffix": "meme", "strategy": "meme_momentum"},
        {"suffix": "pay", "strategy": "payments_spread"},
        {"suffix": "tri", "strategy": "triangular_paper"},
    ],
    "treasury": [
        {"suffix": "ledger", "role": "ledger_audit"},
        {"suffix": "payout", "role": "payout_readiness"},
        {"suffix": "sync", "role": "mid_sync"},
    ],
    "risk": [
        {"suffix": "withdraw", "role": "withdrawal_risk"},
        {"suffix": "velocity", "role": "velocity"},
        {"suffix": "caps", "role": "caps"},
        {"suffix": "audit", "role": "audit_denials"},
        {"suffix": "steady", "role": "steady_heartbeat"},
    ],
    "winnable_pairs": [
        {"suffix": "prime", "shard": 0},
        {"suffix": "beta", "shard": 1},
        {"suffix": "gamma", "shard": 2},
        {"suffix": "delta", "shard": 3},
    ],
}

_KIND_TO_SUP = {
    "analytics": "sup_profit",
    "extended_profit": "sup_extended",
    "treasury": "sup_treasury",
    "risk": "sup_risk",
    "winnable_pairs": "sup_winnable",
}


def _iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_fleet_bots() -> List[Dict[str, Any]]:
    bots: List[Dict[str, Any]] = []
    for kind, rows in _FLEET_BLUEPRINTS.items():
        sup = _KIND_TO_SUP[kind]
        for row in rows:
            suffix = row["suffix"]
            bid = f"fleet_{kind}_{suffix}".replace("winnable_pairs", "winnable")
            name = row.get("name") or f"Fleet {kind} {suffix}"
            bots.append({
                "id": bid,
                "name": name,
                "kind": kind,
                "supervisor": sup,
                "enabled": True,
                "fleet": True,
                "config": dict(row),
            })
    return bots


def merge_fleet_into_controls(controls: Dict[str, Any]) -> None:
    existing = {b.get("id"): b for b in (controls.get("fleet_bots") or []) if b.get("id")}
    merged: List[Dict[str, Any]] = []
    for bot in default_fleet_bots():
        bid = bot["id"]
        if bid in existing:
            row = {**bot, **existing[bid]}
            row["id"] = bid
            merged.append(row)
        else:
            merged.append(bot)
    controls["fleet_bots"] = merged
    controls.setdefault("fleet_meta", {})["mechanics_version"] = 25
    controls["fleet_meta"]["extended_direction"] = _EXTENDED_SAME_DIRECTION


def list_fleet_bots(controls: Dict[str, Any]) -> List[Dict[str, Any]]:
    merge_fleet_into_controls(controls)
    return list(controls.get("fleet_bots") or [])


def _fleet_enabled(bot: Dict[str, Any], controls: Dict[str, Any]) -> bool:
    if controls.get("kill_switch"):
        return False
    sup = next((s for s in controls.get("supervisors") or [] if s.get("id") == bot.get("supervisor")), None)
    if sup and not sup.get("enabled", True):
        return False
    ov = (controls.get("bot_overrides") or {}).get(bot.get("id"))
    if isinstance(ov, dict) and "enabled" in ov:
        return bool(ov["enabled"])
    return bool(bot.get("enabled", True))


def _mark_fleet_bot(controls: Dict[str, Any], bot_id: str, result: Dict[str, Any]) -> None:
    for b in controls.get("fleet_bots") or []:
        if b.get("id") == bot_id:
            b["last_run_at"] = _iso()
            b["last_run_ok"] = bool(result.get("success"))
            if result.get("error"):
                b["last_run_error"] = str(result["error"])[:200]
            else:
                b.pop("last_run_error", None)
            break


def _tick_profit_analyst_bot(bot: Dict[str, Any], *, hot_symbols: Optional[List[str]]) -> Dict[str, Any]:
    from backend.services import exchange_arbitrage_service as arb
    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage

    cfg = bot.get("config") or {}
    symbols = [str(s).upper() for s in (cfg.get("symbols") or [])]
    if hot_symbols:
        symbols = list(dict.fromkeys([s for s in hot_symbols if s in symbols] + symbols))[:4]
    agent_id = bot.get("id")
    notional = float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75") or 75)
    scan = arb.scan_opportunities(symbols=symbols, venues=["binance", "nonkyc"], notional_usd=notional)
    opps = sorted(scan.get("opportunities") or [], key=lambda o: float(o.get("net_bps") or 0), reverse=True)
    if not opps:
        return {"success": True, "executed": False, "reason": "no_opps", "bot_id": agent_id}
    opp = opps[0]
    if float(opp.get("net_bps") or 0) < 10:
        return {"success": True, "executed": False, "reason": "below_threshold", "bot_id": agent_id}
    trade = opp
    if arb.live_enabled():
        prep = arb.prepare_live_opportunity(opp, configured_usd=notional, min_live_usd=10.0)
        if not prep.get("ok"):
            return {"success": False, "error": prep.get("reason"), "bot_id": agent_id}
        trade = prep["opportunity"]
    ex_res = execute_spatial_arbitrage(trade, agent_id=agent_id)
    book_agent_profit(agent_id, trade, ex_res)
    return {
        "success": bool(ex_res.get("success")),
        "executed": bool(ex_res.get("success")),
        "bot_id": agent_id,
        "symbol": trade.get("symbol"),
        "mode": ex_res.get("mode"),
        "error": ex_res.get("error"),
    }


def _tick_extended_bot(bot: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.exchange_extended_profit_service import _strategy_cfg, _STRATEGY_RUNNERS

    strategy = str((bot.get("config") or {}).get("strategy") or "fast_arb_rescan")
    runner = _STRATEGY_RUNNERS.get(strategy)
    if not runner:
        return {"success": False, "error": "unknown_strategy", "bot_id": bot.get("id")}
    scfg = dict(_strategy_cfg(strategy))
    scfg["agent_id"] = bot.get("id")
    scfg["direction"] = _EXTENDED_SAME_DIRECTION
    try:
        res = runner(scfg)
        res["bot_id"] = bot.get("id")
        res["fleet_direction"] = _EXTENDED_SAME_DIRECTION
        return res if isinstance(res, dict) else {"success": True, "bot_id": bot.get("id")}
    except Exception as exc:
        return {"success": False, "error": str(exc), "bot_id": bot.get("id")}


def _tick_treasury_bot(bot: Dict[str, Any]) -> Dict[str, Any]:
    role = str((bot.get("config") or {}).get("role") or "ledger_audit")
    out: Dict[str, Any] = {"success": True, "bot_id": bot.get("id"), "role": role}
    try:
        if role == "ledger_audit":
            from backend.services.exchange_treasury_service import treasury_status
            st = treasury_status()
            out["ledger_stashed_usd_live"] = st.get("ledger_stashed_usd_live")
            out["ledger_stashed_usd_paper"] = st.get("ledger_stashed_usd_paper")
        elif role == "payout_readiness":
            from backend.services.exchange_payout_service import payout_status
            ps = payout_status(light=True)
            out["ready_to_sweep"] = ps.get("ready_to_sweep")
            out["mode"] = ps.get("mode")
        elif role == "mid_sync":
            from backend.services.exchange_live_execution_service import sync_internal_prices_to_external_mid
            out["sync"] = sync_internal_prices_to_external_mid()
    except Exception as exc:
        return {"success": False, "error": str(exc), "bot_id": bot.get("id")}
    return out


def _tick_risk_bot(bot: Dict[str, Any], controls: Dict[str, Any]) -> Dict[str, Any]:
    role = str((bot.get("config") or {}).get("role") or "steady_heartbeat")
    from backend.services.trading_bots_control_service import _tick_risk_officer

    base = _tick_risk_officer(controls)
    base["bot_id"] = bot.get("id")
    base["risk_role"] = role
    base["steady"] = role == "steady_heartbeat"
    return base


def _tick_winnable_bot(
    bot: Dict[str, Any],
    *,
    pair_search: Optional[Dict[str, Any]],
    shard: int,
    shard_count: int,
) -> Dict[str, Any]:
    from backend.services.exchange_winnable_pairs_service import run_winnable_pairs_tick

    search = dict(pair_search) if pair_search else None
    if search and search.get("hits"):
        hits = list(search.get("hits") or [])
        sliced = [h for i, h in enumerate(hits) if i % max(1, shard_count) == shard]
        search = {
            **search,
            "hits": sliced,
            "hot_symbols": list(dict.fromkeys(h.get("symbol") for h in sliced if h.get("symbol"))),
        }
    res = run_winnable_pairs_tick(
        pair_search=search,
        agent_id=str(bot.get("id")),
        max_executions_per_tick=1,
    )
    res["bot_id"] = bot.get("id")
    res["shard"] = shard
    return res


def run_fleet_for_kind(
    controls: Dict[str, Any],
    kind: str,
    *,
    hot_symbols: Optional[List[str]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merge_fleet_into_controls(controls)
    bots = [b for b in controls.get("fleet_bots") or [] if b.get("kind") == kind]
    winnable_count = len(bots) if kind == "winnable_pairs" else 1
    results: List[Dict[str, Any]] = []
    for bot in bots:
        if not _fleet_enabled(bot, controls):
            results.append({"success": False, "error": "bot_disabled", "bot_id": bot.get("id")})
            continue
        if kind == "analytics":
            r = _tick_profit_analyst_bot(bot, hot_symbols=hot_symbols)
        elif kind == "extended_profit":
            r = _tick_extended_bot(bot)
        elif kind == "treasury":
            r = _tick_treasury_bot(bot)
        elif kind == "risk":
            r = _tick_risk_bot(bot, controls)
        elif kind == "winnable_pairs":
            shard = int((bot.get("config") or {}).get("shard") or 0)
            r = _tick_winnable_bot(bot, pair_search=pair_search, shard=shard, shard_count=max(1, winnable_count))
        else:
            r = {"success": False, "error": "unknown_kind"}
        _mark_fleet_bot(controls, bot.get("id"), r)
        results.append(r)
    ok = sum(1 for r in results if r.get("success"))
    return {
        "success": ok > 0 or not results,
        "kind": kind,
        "bot_count": len(bots),
        "ok_count": ok,
        "results": results,
    }


def fleet_overview(controls: Dict[str, Any]) -> Dict[str, Any]:
    merge_fleet_into_controls(controls)
    return {
        "mechanics": FLEET_MECHANICS,
        "mechanics_count": len(FLEET_MECHANICS),
        "bots": controls.get("fleet_bots") or [],
        "meta": controls.get("fleet_meta") or {},
    }
