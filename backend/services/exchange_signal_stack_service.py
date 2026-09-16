"""Signal stack trader — pair search + bot skills + stack/learning mechanics across agent lanes."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb

_CFG_KEY = "signal_stack_trader"
_DEFAULT_AGENT = "arb_signal_stack"


def load_config() -> Dict[str, Any]:
    from backend.services.exchange_profit_path_service import load_config as ppp_cfg

    raw = dict((ppp_cfg().get(_CFG_KEY) or {}))
    raw.setdefault("enabled", True)
    raw.setdefault("agent_id", _DEFAULT_AGENT)
    raw.setdefault("skill_set", "ai_daemon")
    raw.setdefault(
        "default_skills",
        ["spatial_arbitrage", "sentiment_alpha", "ml_price_forecast", "kelly_sizing"],
    )
    raw.setdefault("min_search_score", 12.0)
    raw.setdefault("min_net_bps", 10.0)
    raw.setdefault("min_composite_score", 38.0)
    raw.setdefault("max_executions_per_tick", 2)
    raw.setdefault("notional_usd", float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75") or 75))
    raw.setdefault("sync_skills_each_tick", False)
    raw.setdefault("run_dedicated_agent", True)
    raw.setdefault("boost_winnable_with_skills", True)
    raw.setdefault("boost_ai_with_search_hits", True)
    raw.setdefault("boost_arb_paper_learning", True)
    return raw


def enabled() -> bool:
    env = os.environ.get("EXCHANGE_SIGNAL_STACK", "").strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    if env in ("1", "true", "yes", "on"):
        return True
    return bool(load_config().get("enabled", True))


def _skill_ids(cfg: Dict[str, Any]) -> List[str]:
    ss = cfg.get("skill_set")
    if ss:
        try:
            from backend.services.exchange_bot_skills_service import resolve_skill_set

            return list(resolve_skill_set(str(ss)).get("skills") or [])
        except Exception:
            pass
    return list(cfg.get("default_skills") or [])


def _hit_net_bps(hit: Dict[str, Any]) -> float:
    for key in ("avg_net_bps", "live_net_bps", "net_bps"):
        val = hit.get(key)
        if val is not None:
            return float(val)
    return 0.0


def score_search_hit(
    hit: Dict[str, Any],
    *,
    skill_ids: Optional[List[str]] = None,
    agent: Optional[Dict[str, Any]] = None,
    volatility: float = 0.35,
) -> Dict[str, Any]:
    """Blend pair-search score with skill edge + learning bonus bps."""
    sym = str(hit.get("symbol") or "").upper()
    buy_v = str(hit.get("buy_venue") or "").lower()
    sell_v = str(hit.get("sell_venue") or "").lower()
    net_bps = _hit_net_bps(hit)
    search_score = float(hit.get("search_score") or 0)

    opp = {
        "symbol": sym,
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "net_bps": net_bps,
        "profitable": net_bps > 0,
        "notional_usd": float(hit.get("notional_usd") or 0),
    }

    sids = list(skill_ids or [])
    scored: Dict[str, Any] = {"symbol": sym, "buy_venue": buy_v, "sell_venue": sell_v, "search_score": search_score}
    try:
        from backend.services.exchange_ai_trading_service import score_opportunity

        scored = score_opportunity(opp, sids, volatility=volatility, agent=agent)
        scored["search_score"] = search_score
    except Exception as exc:
        scored["score_error"] = str(exc)[:80]

    learning_bps = 0.0
    if agent:
        try:
            from backend.services.exchange_agent_learning_service import learning_edge_bonus_bps

            learning_bps = float(learning_edge_bonus_bps(agent))
        except Exception:
            pass
        try:
            level_bps = float(agent.get("level_edge_bonus_bps") or 0)
            learning_bps += level_bps
        except Exception:
            pass

    composite = round(
        search_score * 0.45
        + float(scored.get("ai_score") or 0) * 0.4
        + min(25.0, net_bps * 0.35)
        + learning_bps * 0.5,
        2,
    )
    scored["learning_bonus_bps"] = round(learning_bps, 3)
    scored["composite_score"] = composite
    scored["net_bps"] = net_bps
    return scored


def rank_search_hits(
    hits: List[Dict[str, Any]],
    *,
    skill_ids: Optional[List[str]] = None,
    agent: Optional[Dict[str, Any]] = None,
    min_composite: float = 0.0,
) -> List[Dict[str, Any]]:
    ranked = [score_search_hit(h, skill_ids=skill_ids, agent=agent) for h in hits if isinstance(h, dict)]
    ranked.sort(key=lambda r: (r.get("composite_score") or 0, r.get("search_score") or 0), reverse=True)
    if min_composite > 0:
        ranked = [r for r in ranked if float(r.get("composite_score") or 0) >= min_composite]
    return ranked


def _ensure_agent(agent_id: str, *, name: str, skills: List[str]) -> Dict[str, Any]:
    acct = arb.read_account(agent_id)
    if not acct.get("agent_id"):
        acct = {
            "agent_id": agent_id,
            "name": name,
            "realized_profit_usd": 0.0,
            "trade_count": 0,
            "notional_traded_usd": 0.0,
            "by_venue": {},
            "skills": skills,
            "skill_proficiency": {s: 0.2 for s in skills},
            "wallet_label": "signal_stack_wallet",
            "last_action": None,
        }
        arb.write_account(acct)
    else:
        from backend.services.exchange_agent_profit_learning_service import merge_skills_into_account

        merge_skills_into_account(acct, skills)
    return acct


def _execute_hit_route(
    hit: Dict[str, Any],
    *,
    agent_id: str,
    notional: float,
    min_bps: float,
    strategy: str = "signal_stack",
) -> Dict[str, Any]:
    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage
    from backend.services.exchange_profit_path_service import record_execution, record_scan

    sym = str(hit.get("symbol") or "").upper()
    buy_v = str(hit.get("buy_venue") or "").lower()
    sell_v = str(hit.get("sell_venue") or "").lower()
    venues = list(dict.fromkeys([buy_v, sell_v]))
    scan = arb.scan_opportunities(symbols=[sym], venues=venues, notional_usd=notional)
    opps = [
        o
        for o in (scan.get("opportunities") or [])
        if str(o.get("buy_venue") or "").lower() == buy_v
        and str(o.get("sell_venue") or "").lower() == sell_v
        and float(o.get("net_bps") or 0) >= min_bps
    ]
    if not opps:
        return {"success": False, "symbol": sym, "error": "no_opp_at_route"}

    opp = max(opps, key=lambda o: float(o.get("net_bps") or 0))
    trade_opp = opp
    tick_mode = "live" if arb.live_enabled() else "paper"
    if arb.live_enabled():
        prepared = arb.prepare_live_opportunity(
            opp, configured_usd=notional, buffer_pct=0.03, min_live_usd=10.0,
        )
        if not prepared.get("ok"):
            return {
                "success": False,
                "symbol": sym,
                "error": prepared.get("reason") or "prepare_failed",
            }
        trade_opp = prepared["opportunity"]

    path_id = record_scan(
        agent_id=agent_id,
        strategy=strategy,
        best=trade_opp,
        threshold_bps=min_bps,
        mode=tick_mode,
        decision="attempt",
        notional_usd=float(trade_opp.get("notional_usd") or notional),
        venues=venues,
    )
    exec_res = execute_spatial_arbitrage(trade_opp, agent_id=agent_id)
    record_execution(
        path_id=path_id,
        agent_id=agent_id,
        opp=trade_opp,
        exec_res=exec_res,
        strategy=strategy,
        threshold_bps=min_bps,
        venues=venues,
    )
    acct = book_agent_profit(agent_id, trade_opp, exec_res)
    return {
        "success": bool(exec_res.get("success")),
        "symbol": sym,
        "route": f"{buy_v}->{sell_v}",
        "mode": exec_res.get("mode"),
        "net_bps": trade_opp.get("net_bps"),
        "composite_score": hit.get("composite_score"),
        "profit_path_id": path_id,
        "account": acct,
    }


def run_signal_stack_agent_tick(
    *,
    pair_search: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Dedicated signal-stack agent: rank PPP search hits with skills, execute top routes."""
    if not enabled():
        return {"success": False, "error": "signal_stack_disabled"}

    cfg = load_config()
    if not cfg.get("run_dedicated_agent", True):
        return {"success": True, "skipped": True, "reason": "dedicated_agent_off"}

    agent_id = str(agent_id or cfg.get("agent_id") or _DEFAULT_AGENT)
    skills = _skill_ids(cfg)
    acct = _ensure_agent(agent_id, name="Signal Stack Trader", skills=skills)

    search = pair_search
    if search is None:
        from backend.services.exchange_profit_pair_search_service import enabled as pps_on, run_profit_pair_search

        if not pps_on():
            return {"success": False, "error": "profit_pair_search_disabled"}
        search = run_profit_pair_search()

    if not search or not search.get("success"):
        return {"success": False, "error": (search or {}).get("error") or "pair_search_failed"}

    hits = list(search.get("hits") or [])
    min_bps = float(cfg.get("min_net_bps") or 10)
    min_search = float(cfg.get("min_search_score") or 12)
    min_comp = float(cfg.get("min_composite_score") or 38)
    max_exec = max(1, int(cfg.get("max_executions_per_tick") or 2))
    notional = float(cfg.get("notional_usd") or 75)

    filtered = [
        h
        for h in hits
        if isinstance(h, dict)
        and _hit_net_bps(h) >= min_bps
        and float(h.get("search_score") or 0) >= min_search
    ]
    ranked = rank_search_hits(filtered, skill_ids=skills, agent=acct, min_composite=min_comp)

    executions: List[Dict[str, Any]] = []
    executed = 0
    for hit in ranked:
        if executed >= max_exec:
            break
        res = _execute_hit_route(
            hit,
            agent_id=agent_id,
            notional=notional,
            min_bps=min_bps,
            strategy="signal_stack",
        )
        executions.append(res)
        if res.get("success"):
            executed += 1

    if cfg.get("sync_skills_each_tick"):
        try:
            from backend.services.exchange_profit_agent_skills_service import sync_from_ledger_research

            sync_from_ledger_research(agent_id=agent_id, limit=30)
        except Exception:
            pass

    ex._audit(
        "signal_stack_tick",
        user_id="owner",
        agent_id=agent_id,
        executed=executed,
        ranked=len(ranked),
    )
    return {
        "success": True,
        "agent_id": agent_id,
        "executed_count": executed,
        "ranked_count": len(ranked),
        "top_ranked": ranked[:5],
        "executions": executions,
        "skills": skills,
    }


def enrich_pair_search_for_ai(
    *,
    hot_symbols: Optional[List[str]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
    base_symbols: Optional[List[str]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Merge hot symbols + ranked hits for AI / arb symbol lists."""
    cfg = load_config()
    symbols: List[str] = []
    seen = set()
    ranked: List[Dict[str, Any]] = []

    ps = pair_search
    if ps is None and enabled():
        try:
            from backend.services.exchange_profit_pair_search_service import read_index

            idx = read_index()
            ps = {"success": True, "hits": idx.get("hits") or [], "hot_symbols": idx.get("hot_symbols") or []}
        except Exception:
            ps = None

    if ps and ps.get("success"):
        for s in ps.get("hot_symbols") or []:
            sym = str(s).upper()
            if sym and sym not in seen:
                seen.add(sym)
                symbols.append(sym)
        hits = list(ps.get("hits") or [])
        if cfg.get("boost_ai_with_search_hits", True) and hits:
            skills = _skill_ids(cfg)
            ranked = rank_search_hits(hits[:24], skill_ids=skills)[:16]
            for row in ranked:
                sym = str(row.get("symbol") or "").upper()
                if sym and sym not in seen:
                    seen.add(sym)
                    symbols.append(sym)

    for s in hot_symbols or []:
        sym = str(s).upper()
        if sym and sym not in seen:
            seen.add(sym)
            symbols.append(sym)

    for s in base_symbols or []:
        sym = str(s).upper()
        if sym and sym not in seen:
            seen.add(sym)
            symbols.append(sym)

    return symbols[:48], ranked


def run_unified_signal_stack(
    *,
    pair_search: Optional[Dict[str, Any]] = None,
    hot_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Orchestrate signal-stack lane + metadata for control board / orchestrator."""
    if not enabled():
        return {"success": False, "error": "signal_stack_disabled", "enabled": False}

    cfg = load_config()
    out: Dict[str, Any] = {"success": True, "enabled": True, "lanes": {}}

    search = pair_search
    if search is None:
        try:
            from backend.services.exchange_profit_pair_search_service import run_profit_pair_search

            search = run_profit_pair_search()
        except Exception as exc:
            search = {"success": False, "error": str(exc)[:200]}

    out["profit_pair_search"] = search
    hs = list(hot_symbols or [])
    if search and search.get("success"):
        hs = list(dict.fromkeys(hs + list(search.get("hot_symbols") or [])))

    merged_syms, ranked = enrich_pair_search_for_ai(
        hot_symbols=hs,
        pair_search=search if (search or {}).get("success") else None,
    )
    out["merged_symbols"] = merged_syms[:24]
    out["ranked_hits"] = ranked[:8]

    if cfg.get("run_dedicated_agent", True):
        out["lanes"]["signal_stack_agent"] = run_signal_stack_agent_tick(pair_search=search)

    try:
        from backend.services.exchange_prediction_service import predict_batch

        pred = predict_batch(symbols=merged_syms[:12])
        out["lanes"]["prediction_batch"] = {
            "count": pred.get("count"),
            "top": (pred.get("predictions") or [])[:5],
        }
    except Exception as exc:
        out["lanes"]["prediction_batch"] = {"skipped": True, "error": str(exc)[:80]}

    return out


def signal_stack_status() -> Dict[str, Any]:
    cfg = load_config()
    idx = {}
    try:
        from backend.services.exchange_profit_pair_search_service import read_index

        idx = read_index()
    except Exception:
        pass
    aid = str(cfg.get("agent_id") or _DEFAULT_AGENT)
    acct = arb.read_account(aid)
    return {
        "success": True,
        "enabled": enabled(),
        "config": {k: cfg.get(k) for k in (
            "agent_id", "skill_set", "min_search_score", "min_net_bps",
            "min_composite_score", "max_executions_per_tick", "run_dedicated_agent",
        )},
        "pair_search_updated_at": idx.get("updated_at"),
        "hot_symbols": list(idx.get("hot_symbols") or [])[:16],
        "agent_account": {
            "agent_id": aid,
            "realized_profit_usd": acct.get("realized_profit_usd"),
            "trade_count": acct.get("trade_count"),
            "learning_bonus_bps": acct.get("learning_bonus_bps"),
            "mastery_pct": acct.get("mastery_pct"),
            "skills": acct.get("skills"),
        },
    }
