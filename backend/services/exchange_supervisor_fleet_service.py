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
    {"id": "M26", "name": "Fleet XP & levels", "desc": "Per-bot XP from ticks, executions, and profit sync."},
    {"id": "M27", "name": "Fleet reward unlocks", "desc": "Level-gated reward catalog on roster cards."},
]

_EXTENDED_SAME_DIRECTION = "buy_cheap_sell_rich"

_KIND_TO_SUP = {
    "analytics": "sup_profit",
    "extended_profit": "sup_extended",
    "treasury": "sup_treasury",
    "risk": "sup_risk",
    "winnable_pairs": "sup_winnable",
}

_KIND_DISPLAY: Dict[str, Dict[str, str]] = {
    "analytics": {"type_label": "Profit Analyst", "supervisor_name": "Profit Analyst"},
    "extended_profit": {"type_label": "Extended Profit", "supervisor_name": "Extended Profit Director"},
    "treasury": {"type_label": "Treasury", "supervisor_name": "Treasury Manager"},
    "risk": {"type_label": "Risk Officer", "supervisor_name": "Risk Officer"},
    "winnable_pairs": {"type_label": "Winnable Pairs", "supervisor_name": "Winnable Pairs Executor"},
}

_FLEET_BLUEPRINTS: Dict[str, List[Dict[str, Any]]] = {
    "analytics": [
        {"suffix": "alpha", "name": "Profit Analyst Alpha", "label": "PA-α", "role_label": "DOGE · XRP trade lane", "badge": "lane", "symbols": ["DOGE", "XRP"]},
        {"suffix": "beta", "name": "Profit Analyst Beta", "label": "PA-β", "role_label": "LTC · SOL trade lane", "badge": "lane", "symbols": ["LTC", "SOL"]},
        {"suffix": "gamma", "name": "Profit Analyst Gamma", "label": "PA-γ", "role_label": "AVAX · LINK trade lane", "badge": "lane", "symbols": ["AVAX", "LINK"]},
        {"suffix": "delta", "name": "Profit Analyst Delta", "label": "PA-δ", "role_label": "BTC · ETH trade lane", "badge": "lane", "symbols": ["BTC", "ETH"]},
        {"suffix": "epsilon", "name": "Profit Analyst Epsilon", "label": "PA-ε", "role_label": "TRX · SHIB trade lane", "badge": "lane", "symbols": ["TRX", "SHIB"]},
    ],
    "extended_profit": [
        {"suffix": "dual", "name": "Extended Dual-Farm Runner", "label": "EXT-1", "role_label": "Live dual-venue · same direction", "badge": "dual", "strategy": "live_dual_venue"},
        {"suffix": "fast", "name": "Extended Fast-Rescan Scout", "label": "EXT-2", "role_label": "Fast arb rescan · same direction", "badge": "scan", "strategy": "fast_arb_rescan"},
        {"suffix": "peg", "name": "Extended Stablecoin Peg", "label": "EXT-3", "role_label": "USDT/USDC peg capture", "badge": "peg", "strategy": "stablecoin_peg"},
        {"suffix": "meme", "name": "Extended Meme Momentum", "label": "EXT-4", "role_label": "Meme momentum farms", "badge": "meme", "strategy": "meme_momentum"},
        {"suffix": "pay", "name": "Extended Payments Spread", "label": "EXT-5", "role_label": "Payments rail spreads", "badge": "pay", "strategy": "payments_spread"},
        {"suffix": "tri", "name": "Extended Triangular Loop", "label": "EXT-6", "role_label": "Triangular paper loops", "badge": "tri", "strategy": "triangular_paper"},
    ],
    "treasury": [
        {"suffix": "ledger", "name": "Treasury Ledger Sentinel", "label": "TRE-1", "role_label": "Ledger audit & stash totals", "badge": "ledger", "role": "ledger_audit"},
        {"suffix": "payout", "name": "Treasury Payout Watch", "label": "TRE-2", "role_label": "PayPal / sweep readiness", "badge": "payout", "role": "payout_readiness"},
        {"suffix": "sync", "name": "Treasury Price Sync", "label": "TRE-3", "role_label": "Internal ↔ external mid sync", "badge": "sync", "role": "mid_sync"},
    ],
    "risk": [
        {"suffix": "withdraw", "name": "Risk Withdrawal Guard", "label": "RSK-1", "role_label": "Withdrawal risk log", "badge": "withdraw", "role": "withdrawal_risk"},
        {"suffix": "velocity", "name": "Risk Velocity Monitor", "label": "RSK-2", "role_label": "Velocity & frequency caps", "badge": "velocity", "role": "velocity"},
        {"suffix": "caps", "name": "Risk Cap Enforcer", "label": "RSK-3", "role_label": "Position & notional caps", "badge": "caps", "role": "caps"},
        {"suffix": "audit", "name": "Risk Audit Scanner", "label": "RSK-4", "role_label": "Recent risk denials", "badge": "audit", "role": "audit_denials"},
        {"suffix": "steady", "name": "Risk Steady Pulse", "label": "RSK-5", "role_label": "Always-on heartbeat", "badge": "steady", "role": "steady_heartbeat"},
    ],
    "winnable_pairs": [
        {"suffix": "prime", "name": "Winnable Executor Prime", "label": "WIN-A", "role_label": "Pair-search shard A", "badge": "shard", "shard": 0},
        {"suffix": "beta", "name": "Winnable Executor Beta", "label": "WIN-B", "role_label": "Pair-search shard B", "badge": "shard", "shard": 1},
        {"suffix": "gamma", "name": "Winnable Executor Gamma", "label": "WIN-C", "role_label": "Pair-search shard C", "badge": "shard", "shard": 2},
        {"suffix": "delta", "name": "Winnable Executor Delta", "label": "WIN-D", "role_label": "Pair-search shard D", "badge": "shard", "shard": 3},
    ],
}


def _iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_fleet_bots() -> List[Dict[str, Any]]:
    bots: List[Dict[str, Any]] = []
    for kind, rows in _FLEET_BLUEPRINTS.items():
        sup = _KIND_TO_SUP[kind]
        meta = _KIND_DISPLAY.get(kind) or {}
        for row in rows:
            if not row.get("suffix"):
                continue
            suffix = row["suffix"]
            bid = f"fleet_{kind}_{suffix}".replace("winnable_pairs", "winnable")
            name = row.get("name") or f"Fleet {kind} {suffix}"
            label = row.get("label") or suffix.upper()
            bots.append({
                "id": bid,
                "name": name,
                "label": label,
                "type_label": meta.get("type_label") or kind,
                "supervisor_name": meta.get("supervisor_name") or sup,
                "role_label": row.get("role_label") or "",
                "wallet_label": label,
                "badge": row.get("badge") or "fleet",
                "kind": kind,
                "supervisor": sup,
                "enabled": True,
                "fleet": True,
                "config": dict(row),
            })
    return bots


def fleet_bot_as_trading_row(fb: Dict[str, Any], acct: Dict[str, Any]) -> Dict[str, Any]:
    """Shape fleet bot for control-board bot table (names/labels like arb agents)."""
    from backend.services.exchange_fleet_progression_service import enrich_fleet_bot, progression_view

    enrich_fleet_bot(fb, acct)
    return {
        "id": fb.get("id"),
        "name": fb.get("name") or fb.get("id"),
        "label": fb.get("label"),
        "type_label": fb.get("type_label"),
        "supervisor_name": fb.get("supervisor_name"),
        "role_label": fb.get("role_label"),
        "kind": fb.get("kind") or "fleet",
        "supervisor": fb.get("supervisor"),
        "config_enabled": bool(fb.get("enabled", True)),
        "fleet": True,
        "wallet_label": fb.get("wallet_label") or fb.get("label") or "",
        "realized_pnl_usd": round(float(acct.get("realized_profit_usd") or 0), 4),
        "unrealized_pnl_usd": 0.0,
        "trade_count": int(acct.get("trade_count") or 0),
        "notional_traded_usd": round(float(acct.get("notional_traded_usd") or 0), 2),
        "last_action": acct.get("last_action"),
        "last_run_at": fb.get("last_run_at"),
        "last_run_ok": fb.get("last_run_ok"),
        "progression": progression_view(fb),
    }


def merge_fleet_into_controls(controls: Dict[str, Any]) -> None:
    existing = {b.get("id"): b for b in (controls.get("fleet_bots") or []) if b.get("id")}
    merged: List[Dict[str, Any]] = []
    for bot in default_fleet_bots():
        bid = bot["id"]
        if bid in existing:
            row = {**bot, **existing[bid]}
            row["id"] = bid
            for key in ("name", "label", "type_label", "supervisor_name", "role_label", "wallet_label", "badge"):
                if bot.get(key):
                    row[key] = bot[key]
            merged.append(row)
        else:
            merged.append(bot)
    controls["fleet_bots"] = merged
    controls.setdefault("fleet_meta", {})["mechanics_version"] = 27
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
    from backend.services.exchange_fleet_progression_service import apply_tick_progression

    for b in controls.get("fleet_bots") or []:
        if b.get("id") == bot_id:
            b["last_run_at"] = _iso()
            b["last_run_ok"] = bool(result.get("success"))
            if result.get("error"):
                b["last_run_error"] = str(result["error"])[:200]
            else:
                b.pop("last_run_error", None)
            prog_delta = apply_tick_progression(b, result)
            result["xp_gain"] = prog_delta.get("xp_gain")
            result["fleet_level"] = prog_delta.get("level")
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


def _record_fleet_ops(
    controls: Dict[str, Any],
    results: Dict[str, Any],
    *,
    kind: Optional[str],
    ok: bool,
    ran_at: str,
) -> None:
    """Persist last fleet-only tick for Business Control Phase 5 ops console."""
    meta = controls.setdefault("fleet_meta", {})
    meta["last_run_at"] = ran_at
    meta["last_run_kind"] = kind or "all"
    meta["last_run_ok"] = bool(ok)
    per_kind: Dict[str, Any] = {}
    for key, res in results.items():
        if not isinstance(res, dict):
            continue
        per_kind[key] = {
            "success": bool(res.get("success")),
            "ok_count": res.get("ok_count"),
            "bot_count": res.get("bot_count"),
            "error": res.get("error"),
        }
    meta["last_results"] = per_kind
    history = list(meta.get("history") or [])
    history.append({
        "ran_at": ran_at,
        "kind": kind or "all",
        "ok": bool(ok),
        "kinds": list(per_kind.keys()),
    })
    meta["history"] = history[-30:]


def run_fleet_tick(
    controls: Dict[str, Any],
    *,
    kind: Optional[str] = None,
    hot_symbols: Optional[List[str]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run one or all supervisor fleet kinds (Phase 4 — lighter than full run_all)."""
    kinds = [kind] if kind else list(_FLEET_BLUEPRINTS.keys())
    results: Dict[str, Any] = {}
    for k in kinds:
        if k not in _FLEET_BLUEPRINTS:
            results[k] = {"success": False, "error": "unknown_fleet_kind"}
            continue
        results[k] = run_fleet_for_kind(
            controls, k, hot_symbols=hot_symbols, pair_search=pair_search,
        )
    ran_at = _iso()
    ok = all((r or {}).get("success") for r in results.values())
    _record_fleet_ops(controls, results, kind=kind, ok=ok, ran_at=ran_at)
    _save_fleet_controls(controls)
    return {"success": ok, "results": results, "ran_at": ran_at}


def _save_fleet_controls(controls: Dict[str, Any]) -> None:
    from backend.services.trading_bots_control_service import _save_controls

    merge_fleet_into_controls(controls)
    _save_controls(controls)


def fleet_overview(controls: Dict[str, Any], *, persist_sync: bool = True) -> Dict[str, Any]:
    from backend.services import exchange_arbitrage_service as arb_svc
    from backend.services.exchange_fleet_progression_service import (
        enrich_fleet_bot,
        fleet_progression_summary,
        progression_view,
        reward_catalog,
    )

    merge_fleet_into_controls(controls)
    bots = list(controls.get("fleet_bots") or [])
    dirty = False
    api_bots: List[Dict[str, Any]] = []
    for b in bots:
        acct = arb_svc.read_account(b.get("id"))
        if enrich_fleet_bot(b, acct):
            dirty = True
        row = dict(b)
        row["progression"] = progression_view(b)
        api_bots.append(row)

    if dirty and persist_sync:
        _save_fleet_controls(controls)

    failing = sum(1 for b in bots if b.get("last_run_at") and b.get("last_run_ok") is False)
    never = sum(1 for b in bots if not b.get("last_run_at"))
    meta = dict(controls.get("fleet_meta") or {})
    prog_summary = fleet_progression_summary(api_bots)
    return {
        "mechanics": FLEET_MECHANICS,
        "mechanics_count": len(FLEET_MECHANICS),
        "bots": api_bots,
        "meta": meta,
        "progression_summary": prog_summary,
        "rewards": reward_catalog(),
        "health": {
            "bot_count": len(bots),
            "last_tick_failed_bots": failing,
            "never_ran_bots": never,
            "last_fleet_run_at": meta.get("last_run_at"),
            "last_fleet_run_ok": meta.get("last_run_ok"),
        },
    }
