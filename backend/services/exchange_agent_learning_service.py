"""Adaptive learning ("super intelligence") for trading agents.

Each agent carries a per-skill ``skill_proficiency`` map and an ``intelligence`` (IQ) score
that both grow as the agent books realized profit — reinforcement learning, lightweight and
deterministic. Skills that participate in profitable cycles gain proficiency (saturating toward
a cap), which raises a ``learning_edge_bonus_bps`` added on top of the base blended edge. Super
skills learn faster (configurable multiplier).

This is heuristic/paper learning — it models "the bot gets smarter the more it earns" without
any external ML dependency or network call, so it runs in the 24/7 daemon and in tests.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _cfg(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if cfg is not None:
        return cfg
    try:
        from backend.services.exchange_leveling_service import load_config
        return load_config().get("learning") or {}
    except Exception:
        return {}


def _super_skill_ids() -> set:
    try:
        from backend.services.exchange_bot_skills_service import load_skills
        return {s["id"] for s in load_skills() if s.get("super")}
    except Exception:
        return set()


def _avg_proficiency(prof: Dict[str, float]) -> float:
    vals = [float(v) for v in prof.values()]
    return sum(vals) / len(vals) if vals else 0.0


def learning_edge_bonus_bps(agent: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> float:
    c = _cfg(cfg)
    prof = agent.get("skill_proficiency") or {}
    return round(_avg_proficiency(prof) * float(c.get("max_bonus_bps") or 0), 3)


def agent_intelligence(agent: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> float:
    c = _cfg(cfg)
    prof = agent.get("skill_proficiency") or {}
    base = float(c.get("base_intelligence") or 100)
    per = float(c.get("intelligence_per_proficiency") or 80)
    return round(base + per * _avg_proficiency(prof), 1)


def learn_from_profit(agent: Dict[str, Any], profit_usd: float, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update the agent's skill proficiency + intelligence from a realized profit, in place."""
    c = _cfg(cfg)
    lr = float(c.get("learning_rate") or 0.06)
    cap = float(c.get("proficiency_cap") or 1.0)
    divisor = float(c.get("reward_capital_divisor") or 0.0015)
    super_mult = float(c.get("super_skill_bonus_multiplier") or 1.5)

    capital = float(agent.get("capital_usd") or 0)
    denom = max(1e-9, capital * divisor)
    reward = max(0.0, min(1.0, float(profit_usd or 0) / denom))

    supers = _super_skill_ids()
    prof: Dict[str, float] = dict(agent.get("skill_proficiency") or {})
    for sid in agent.get("skills") or []:
        cur = float(prof.get(sid) or 0.0)
        rate = lr * (super_mult if sid in supers else 1.0)
        cur = cur + rate * reward * (cap - cur)  # saturating growth toward cap
        prof[sid] = round(min(cap, max(0.0, cur)), 5)
    agent["skill_proficiency"] = prof

    agent["intelligence"] = agent_intelligence(agent, c)
    bonus = learning_edge_bonus_bps(agent, c)
    agent["learning_bonus_bps"] = bonus
    agent["mastery_pct"] = round(_avg_proficiency(prof) * 100, 1)
    return {"reward": round(reward, 4), "learning_bonus_bps": bonus,
            "intelligence": agent["intelligence"], "mastery_pct": agent["mastery_pct"]}


def learning_snapshot(agent: Dict[str, Any]) -> Dict[str, Any]:
    prof = agent.get("skill_proficiency") or {}
    top = sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return {
        "intelligence": agent.get("intelligence") or agent_intelligence(agent),
        "mastery_pct": agent.get("mastery_pct") or round(_avg_proficiency(prof) * 100, 1),
        "learning_bonus_bps": agent.get("learning_bonus_bps") or learning_edge_bonus_bps(agent),
        "top_skills": [{"skill_id": k, "proficiency_pct": round(v * 100, 1)} for k, v in top],
    }
