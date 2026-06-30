"""AI multi-venue crypto trading: market analysis, skill scoring, and execution.

Combines cross-venue margin scanning with super-skill intelligence (sentiment alpha,
ML forecast, Kelly sizing, latency momentum) and routes orders through
``exchange_venue_api_service`` on all configured major exchanges.

Paper mode is default; live requires ``EXCHANGE_ARBITRAGE_LIVE=1`` + vault API keys.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import exchange_bot_skills_service as skills_svc
from backend.services import external_exchange_connector_service as conn

_AI_CFG_PATH = ex._BASE + "/data/exchange_ai_trading_config.json"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_ai_config() -> Dict[str, Any]:
    cfg = ex._read_json(_AI_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _deterministic_sentiment(symbol: str, buy_venue: str, sell_venue: str) -> float:
    """Deterministic 0..1 sentiment proxy (no external ML dependency)."""
    key = f"{symbol}:{buy_venue}:{sell_venue}".encode("utf-8")
    h = int(hashlib.sha256(key).hexdigest()[:8], 16)
    return round((h % 1000) / 1000.0, 4)


def _volatility_from_opportunities(opportunities: List[Dict[str, Any]]) -> float:
    if not opportunities:
        return float(load_ai_config().get("volatility_default") or 0.35)
    spreads = [max(0.0, float(o.get("gross_bps") or 0)) for o in opportunities]
    avg = sum(spreads) / len(spreads) if spreads else 30.0
    return round(min(1.5, max(0.1, avg / 120.0)), 3)


def _kelly_notional(capital: float, net_bps: float, blended_bps: float) -> float:
    edge = max(0.0, net_bps) / 10000.0
    if edge <= 0:
        return 0.0
    win_prob = min(0.85, 0.45 + blended_bps / 500.0)
    kelly = max(0.0, min(0.25, (win_prob * (1 + edge) - (1 - win_prob)) / max(edge, 1e-9)))
    return round(capital * kelly, 2)


def score_opportunity(
    opp: Dict[str, Any],
    skill_ids: List[str],
    *,
    volatility: float = 0.35,
    agent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rank a spatial-arb opportunity with AI super-skill boosts."""
    net_bps = float(opp.get("net_bps") or 0)
    blended = skills_svc.blended_edge_bps(skill_ids, volatility)
    blended_bps = float(blended.get("blended_edge_bps") or 0)

    spatial_boost = 0.0
    if "spatial_arbitrage" in skill_ids and opp.get("buy_venue") != opp.get("sell_venue"):
        spatial_boost = float(skills_svc.estimate_skill_edge("spatial_arbitrage", volatility)) * 0.15

    sentiment = _deterministic_sentiment(
        str(opp.get("symbol") or ""),
        str(opp.get("buy_venue") or ""),
        str(opp.get("sell_venue") or ""),
    )
    sentiment_boost = 0.0
    if "sentiment_alpha" in skill_ids:
        sentiment_boost = sentiment * float(skills_svc.estimate_skill_edge("sentiment_alpha", volatility)) * 0.2

    ml_boost = 0.0
    if "ml_price_forecast" in skill_ids:
        momentum = min(1.0, max(0.0, net_bps / 80.0))
        ml_boost = momentum * float(skills_svc.estimate_skill_edge("ml_price_forecast", volatility)) * 0.18

    latency_boost = 0.0
    if "latency_momentum" in skill_ids and net_bps > 40:
        latency_boost = float(skills_svc.estimate_skill_edge("latency_momentum", volatility)) * 0.12

    stat_boost = 0.0
    if "statistical_arbitrage" in skill_ids and net_bps > 35:
        stat_boost = float(skills_svc.estimate_skill_edge("statistical_arbitrage", volatility)) * 0.1

    intelligence_mult = 1.0
    if agent:
        try:
            from backend.services.exchange_agent_learning_service import agent_intelligence
            iq = float(agent_intelligence(agent))
            intelligence_mult = 1.0 + max(0.0, (iq - 100.0) / 500.0)
        except Exception:
            pass

    raw_score = (
        net_bps * 0.42
        + blended_bps * 0.22
        + spatial_boost
        + sentiment_boost
        + ml_boost
        + latency_boost
        + stat_boost
    ) * intelligence_mult
    ai_score = round(min(100.0, max(0.0, raw_score)), 2)

    capital = float((agent or {}).get("capital_usd") or load_ai_config().get("capital_usd") or 1000)
    notional = float(opp.get("notional_usd") or load_ai_config().get("paper_trade_usd") or 350)
    if "kelly_sizing" in skill_ids:
        kelly_n = _kelly_notional(capital, net_bps, blended_bps)
        if kelly_n > 0:
            notional = min(notional, kelly_n)

    strategies = []
    if spatial_boost:
        strategies.append("spatial_arbitrage")
    if sentiment_boost:
        strategies.append("sentiment_alpha")
    if ml_boost:
        strategies.append("ml_price_forecast")
    if latency_boost:
        strategies.append("latency_momentum")
    if stat_boost:
        strategies.append("statistical_arbitrage")
    if "kelly_sizing" in skill_ids:
        strategies.append("kelly_sizing")

    return {
        **opp,
        "ai_score": ai_score,
        "ai_strategies": strategies,
        "sentiment": sentiment,
        "blended_skill_bps": blended_bps,
        "skill_breakdown": blended.get("breakdown") or [],
        "sized_notional_usd": round(notional, 2),
        "est_profit_usd": round(notional * net_bps / 10000.0, 4),
        "intelligence_mult": round(intelligence_mult, 3),
    }


def analyze_market(
    *,
    symbols: Optional[List[str]] = None,
    venues: Optional[List[str]] = None,
    skill_ids: Optional[List[str]] = None,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    probe_venues: Optional[bool] = None,
) -> Dict[str, Any]:
    """Scan all major venues, score opportunities with AI super-skills."""
    cfg = load_ai_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "ai_trading_disabled"}

    skill_ids = list(skill_ids or cfg.get("default_skills") or [])
    symbols = symbols or cfg.get("symbols")
    venues = venues or cfg.get("venues")

    scan = arb.scan_opportunities(symbols, venues, injected=injected)
    opportunities = scan.get("opportunities") or []
    volatility = _volatility_from_opportunities(opportunities)

    agent = {
        "capital_usd": float(cfg.get("capital_usd") or 1000),
        "skills": skill_ids,
        "skill_proficiency": {s: 0.35 for s in skill_ids},
    }

    ranked: List[Dict[str, Any]] = []
    for opp in opportunities:
        scored = score_opportunity(opp, skill_ids, volatility=volatility, agent=agent)
        scored["actionable"] = (
            scored.get("profitable")
            and scored["ai_score"] >= float(cfg.get("min_ai_score") or 52)
            and float(scored.get("net_bps") or 0) >= float(cfg.get("min_net_bps") or 25)
        )
        ranked.append(scored)
    ranked.sort(key=lambda o: o.get("ai_score", 0), reverse=True)

    venue_probe = None
    if probe_venues if probe_venues is not None else cfg.get("probe_venues_on_analyze", True):
        try:
            from backend.services import exchange_venue_api_service as vapi
            venue_probe = vapi.probe_all_venues()
        except Exception as exc:
            venue_probe = {"success": False, "error": str(exc)}

    return {
        "success": True,
        "analyzed_at": _iso(),
        "mode": "live" if arb.live_enabled() else "paper",
        "skill_ids": skill_ids,
        "volatility": volatility,
        "scan": {
            "source": scan.get("source"),
            "opportunity_count": scan.get("opportunity_count"),
            "profitable_count": scan.get("profitable_count"),
            "min_margin_bps": scan.get("min_margin_bps"),
        },
        "actionable_count": sum(1 for o in ranked if o.get("actionable")),
        "ranked_opportunities": ranked,
        "top_pick": ranked[0] if ranked else None,
        "venue_probe": venue_probe,
    }


def execute_opportunity(
    opp: Dict[str, Any],
    *,
    agent_id: str = "ai_market_trader",
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Execute buy + sell legs; stash profit on MasterNoder treasury."""
    from backend.services.exchange_live_execution_service import execute_spatial_arbitrage
    return execute_spatial_arbitrage(opp, agent_id=agent_id, dry_run=dry_run)


def run_ai_tick(
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    force_execute: bool = False,
) -> Dict[str, Any]:
    """Full AI trading cycle: analyze → pick best → execute → book P&L."""
    cfg = load_ai_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "ai_trading_disabled"}

    agent_id = str(cfg.get("agent_id") or "ai_market_trader")
    analysis = analyze_market(injected=injected, probe_venues=False)
    ranked = analysis.get("ranked_opportunities") or []
    min_score = float(cfg.get("min_ai_score") or 52)
    min_net = float(cfg.get("min_net_bps") or 25)

    best = next(
        (o for o in ranked if o.get("actionable") and float(o.get("net_bps") or 0) >= min_net),
        None,
    )
    if not best and ranked and force_execute:
        best = ranked[0]

    acct = arb.read_account(agent_id)
    acct.setdefault("agent_id", agent_id)
    acct["name"] = cfg.get("name") or agent_id
    acct["ticks"] = int(acct.get("ticks") or 0) + 1
    acct["game_time_sec"] = int(acct.get("game_time_sec") or 0) + 3600
    acct["agent_level"] = 1 + int(acct.get("ticks") or 0) // 40
    acct["skills"] = list(cfg.get("default_skills") or [])

    if not best or float(best.get("ai_score") or 0) < min_score:
        action = {
            "agent_id": agent_id,
            "executed": False,
            "reason": "no_actionable_ai_signal",
            "best": best,
            "analysis_summary": analysis.get("scan"),
        }
        acct["last_action"] = action
        arb.write_account(acct)
        return {
            "success": True,
            "executed": False,
            "analysis": analysis,
            "action": action,
            "account": acct,
        }

    exec_res = execute_opportunity(best, agent_id=agent_id)
    profit = float(exec_res.get("est_profit_usd") or 0) if exec_res.get("success") else 0.0

    if exec_res.get("success") and profit > 0:
        acct["realized_profit_usd"] = round(float(acct.get("realized_profit_usd") or 0) + profit, 6)
        acct["trade_count"] = int(acct.get("trade_count") or 0) + 1
        acct["notional_traded_usd"] = round(
            float(acct.get("notional_traded_usd") or 0) + float(best.get("sized_notional_usd") or 0), 2
        )
        by_venue = acct.setdefault("by_venue", {})
        for vid in (best.get("buy_venue"), best.get("sell_venue")):
            by_venue[str(vid)] = round(float(by_venue.get(vid) or 0) + float(best.get("sized_notional_usd") or 0), 2)

        try:
            from backend.services.exchange_agent_learning_service import learn_from_profit
            learn_from_profit(acct, profit)
        except Exception:
            pass

        ex._audit(
            "ai_trading_execute",
            user_id=agent_id,
            amount_usd=profit,
            symbol=best.get("symbol"),
            buy_venue=best.get("buy_venue"),
            sell_venue=best.get("sell_venue"),
            ai_score=best.get("ai_score"),
            mode=exec_res.get("mode"),
        )

    action = {
        "agent_id": agent_id,
        "executed": bool(exec_res.get("success") and profit > 0),
        "mode": exec_res.get("mode"),
        "ai_score": best.get("ai_score"),
        "ai_strategies": best.get("ai_strategies"),
        **best,
        "execution": exec_res,
    }
    acct["last_action"] = action
    arb.write_account(acct)

    return {
        "success": True,
        "executed": action["executed"],
        "ticked_at": _iso(),
        "live": arb.live_enabled(),
        "analysis": analysis,
        "execution": exec_res,
        "action": action,
        "account": acct,
    }


def ai_trading_status() -> Dict[str, Any]:
    """Overview for UI: mode, venue API readiness, agent P&L."""
    cfg = load_ai_config()
    agent_id = str(cfg.get("agent_id") or "ai_market_trader")
    acct = arb.read_account(agent_id)

    venue_caps = None
    try:
        from backend.services import exchange_venue_api_service as vapi
        venue_caps = vapi.list_venue_capabilities()
    except Exception as exc:
        venue_caps = {"success": False, "error": str(exc)}

    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "mode": "live" if arb.live_enabled() else "paper",
        "agent_id": agent_id,
        "name": cfg.get("name"),
        "skills": cfg.get("default_skills") or [],
        "min_ai_score": cfg.get("min_ai_score"),
        "account": acct,
        "venue_capabilities": venue_caps,
    }
