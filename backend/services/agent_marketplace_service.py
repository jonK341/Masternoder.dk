"""Agent marketplace: users purchase generated trading bots that earn into their own accounts.

Buying an agent debits the buyer's MN2 (platform credit) to the owner treasury and mints a
user-owned bot instance with a skill set. Each tick estimates paper profit from the bot's
blended skill edge and capital (via the profit calculator) and accrues it to that user's
own agent profit account. Real-fund execution stays gated behind EXCHANGE_ARBITRAGE_LIVE.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_bot_skills_service as skills_svc
from backend.services import exchange_profit_calculator_service as calc

_CONFIG_PATH = os.path.join(ex._BASE, "data", "agent_marketplace_config.json")
_USER_AGENTS_DIR = os.path.join(ex._DATA_DIR, "user_agents")
_SALES_PATH = os.path.join(ex._DATA_DIR, "agent_sales.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _agent_skills(agent: Dict[str, Any]) -> List[str]:
    try:
        from backend.services.exchange_rental_service import effective_skills
        return effective_skills(agent)
    except Exception:
        return list(agent.get("skills") or [])


def _project(item: Dict[str, Any], volatility: float, *, extra_edge_bps: float = 0.0) -> Dict[str, Any]:
    """Cross-trade projection for a template or owned agent, applying premium + level boosts."""
    work = dict(item)
    if item.get("rental_skills") or item.get("extra_skills") or item.get("rented"):
        work["skills"] = _agent_skills(item)
    is_premium = bool(work.get("premium"))
    base_cycles = float(work.get("cycles_per_day") or 24)
    bonus, cycles = 0.0, base_cycles
    if is_premium:
        try:
            from backend.services.exchange_premium_service import edge_bonus_and_cycles
            from backend.services.exchange_prediction_service import market_uplift_bps
            bonus, cycles = edge_bonus_and_cycles(True, market_uplift_bps=market_uplift_bps(),
                                                  base_cycles_per_day=base_cycles)
        except Exception:
            bonus, cycles = 0.0, base_cycles
    bonus += float(extra_edge_bps or 0)
    return calc.cross_trade_projection(
        float(work.get("capital_usd") or 0),
        list(work.get("skills") or []),
        volatility=volatility,
        cycles_per_day=cycles,
        risk_level=str(work.get("risk") or item.get("risk") or "medium"),
        edge_bonus_bps=bonus,
    )


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _template_map(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    cfg = cfg or load_config()
    return {t["id"]: t for t in (cfg.get("templates") or []) if isinstance(t, dict) and t.get("id")}


def _sync_exchange_skills_to_profile(user_id: str, agent: Dict[str, Any]) -> None:
    """Mirror exchange bot skills into logs/user_agent_skills without heavy imports."""
    try:
        skills_dir = os.path.join(ex._BASE, "logs", "user_agent_skills")
        os.makedirs(skills_dir, exist_ok=True)
        path = os.path.join(skills_dir, f"{user_id}.json")
        data = ex._read_json(path, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("user_id", user_id)
        data.setdefault("assigned_agents", [])
        data.setdefault("skills", [])
        data.setdefault("skill_path", data.get("skill_path") or "exchange_trader")
        profile_agent = f"exchange_bot_{agent.get('agent_id')}"
        seen = {(s.get("agent_id"), s.get("skill")) for s in data.get("skills") or []}
        for sid in _agent_skills(agent):
            key = (profile_agent, sid)
            if key in seen:
                continue
            data["skills"].append({
                "agent_id": profile_agent,
                "skill": sid,
                "level": 1,
                "unlocked_at": _iso(),
                "source": "exchange_marketplace",
            })
            seen.add(key)
        if profile_agent not in data["assigned_agents"]:
            data["assigned_agents"].append(profile_agent)
        data["updated_at"] = _iso()
        ex._write_json(path, data)
    except Exception:
        pass


def get_catalog() -> Dict[str, Any]:
    cfg = load_config()
    vol = float(cfg.get("default_volatility") or 0.35)
    templates = []
    for t in cfg.get("templates") or []:
        if not isinstance(t, dict):
            continue
        enriched = skills_svc.enrich_agent_offer(t, volatility=vol)
        proj = _project(enriched, vol)
        templates.append({
            **enriched,
            "projection": {
                "blended_edge_bps": proj["blended_edge_bps"],
                "edge_bonus_bps": proj.get("edge_bonus_bps", 0),
                "daily_profit_usd": proj["daily_profit_usd"],
                "monthly_profit_usd": proj["monthly_profit_usd"],
                "monthly_roi_pct": proj["monthly_roi_pct"],
            },
        })
    return {"success": True, "enabled": bool(cfg.get("enabled", True)),
            "currency": cfg.get("currency", "MN2"), "template_count": len(templates), "templates": templates}


def _user_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_USER_AGENTS_DIR, f"{safe}.json")


def _read_user_agents(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_user_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("agents", {})
    return data


def _write_user_agents(user_id: str, data: Dict[str, Any]) -> None:
    ex._write_json(_user_path(user_id), data)


def purchase_agent(user_id: str, template_id: str, *, prepaid: bool = False) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id_required"}
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "marketplace_disabled"}
    tmpl = _template_map(cfg).get((template_id or "").strip())
    if not tmpl:
        return {"success": False, "error": "unknown_template"}

    price_mn2 = float(tmpl.get("price_mn2") or 0)
    balance = ex._get_quote_balance(user_id, "MN2")
    if not prepaid and price_mn2 > 0 and balance < price_mn2:
        return {"success": False, "error": "insufficient_mn2", "needed_mn2": price_mn2, "balance_mn2": round(balance, 6)}

    agent_id = f"ua_{uuid.uuid4().hex[:12]}"
    ref = f"agent-purchase:{agent_id}"
    if not prepaid and price_mn2 > 0:
        ex._adjust_quote_balance(user_id, "MN2", -price_mn2, "agent_marketplace_purchase",
                                 {"reference": ref, "template_id": tmpl["id"]})
        try:
            ex._collect_fee(price_mn2)  # route sale proceeds to owner treasury
        except Exception:
            pass

    agent = {
        "agent_id": agent_id,
        "template_id": tmpl["id"],
        "name": tmpl.get("name") or tmpl["id"],
        "tier": tmpl.get("tier"),
        "skill_set": tmpl.get("skill_set"),
        "owner": user_id,
        "skills": list(tmpl.get("skills") or []),
        "capital_usd": float(tmpl.get("capital_usd") or 0),
        "risk": str(tmpl.get("risk") or "medium"),
        "cycles_per_day": float(tmpl.get("cycles_per_day") or cfg.get("default_cycles_per_day") or 24),
        "premium": bool(tmpl.get("premium")),
        "realized_profit_usd": 0.0,
        "trade_count": 0,
        "game_time_sec": 0,
        "ticks": 0,
        "agent_xp": 0.0,
        "agent_level": 1,
        "super": bool(tmpl.get("super")),
        "skill_proficiency": {},
        "intelligence": 100.0,
        "learning_bonus_bps": 0.0,
        "mastery_pct": 0.0,
        "enabled": True,
        "created_at": _iso(),
        "last_action": None,
    }
    try:
        from backend.services import exchange_trust_service as trust_svc
        trust_svc.enrich_agent_on_purchase(agent)
    except Exception:
        agent.setdefault("activation", "pending")
    data = _read_user_agents(user_id)
    data["agents"][agent_id] = agent
    _write_user_agents(user_id, data)
    _sync_exchange_skills_to_profile(user_id, agent)

    try:
        from backend.services import exchange_leveling_service as lvl
        lvl.record_agent_purchase(user_id, premium=bool(tmpl.get("premium")))
    except Exception:
        pass

    ex._append_jsonl(_SALES_PATH, {
        "ts": _iso(), "user_id": user_id, "agent_id": agent_id,
        "template_id": tmpl["id"], "price_mn2": price_mn2, "price_usd": float(tmpl.get("price_usd") or 0),
    })
    ex._audit("agent_purchased", user_id=user_id, amount_usd=float(tmpl.get("price_usd") or 0),
              agent_id=agent_id, template_id=tmpl["id"], price_mn2=price_mn2)
    return {"success": True, "agent": agent, "spent_mn2": price_mn2, "balance_mn2": round(ex._get_quote_balance(user_id, "MN2"), 6)}


def list_user_agents(user_id: str) -> Dict[str, Any]:
    data = _read_user_agents(user_id)
    cfg = load_config()
    vol = float(cfg.get("default_volatility") or 0.35)
    agents = []
    for a in data.get("agents", {}).values():
        work = dict(a)
        work["skills"] = _agent_skills(a)
        agents.append(skills_svc.enrich_agent_offer(work, volatility=vol))
    return {"success": True, "user_id": user_id, "agent_count": len(agents),
            "agents": sorted(agents, key=lambda a: a.get("created_at") or "", reverse=True)}


def run_user_agent_tick(user_id: str, agent_id: str, *, volatility: Optional[float] = None) -> Dict[str, Any]:
    data = _read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent:
        return {"success": False, "error": "agent_not_found"}
    if not agent.get("enabled", True):
        return {"success": False, "error": "agent_disabled"}

    try:
        from backend.services.exchange_rental_service import rental_gate
        rg = rental_gate(agent)
        if rg:
            return {"success": False, "error": rg}
    except Exception:
        pass

    try:
        from backend.services import exchange_trust_service as trust_svc
        gate = trust_svc.check_activation(user_id, "run_bots", agent=agent)
        if not gate.get("allowed"):
            return {"success": False, "error": gate.get("error", "trust_gate"), "trust_gate": gate}
        if agent.get("super"):
            gate2 = trust_svc.check_activation(user_id, "super_agents", agent=agent)
            if not gate2.get("allowed"):
                return {"success": False, "error": gate2.get("error", "trust_gate"), "trust_gate": gate2}
    except Exception:
        trust_svc = None

    cfg = load_config()
    vol = float(volatility if volatility is not None else cfg.get("default_volatility") or 0.35)

    level_bonus = 0.0
    tick_seconds = 3600.0
    try:
        from backend.services import exchange_leveling_service as lvl
        lcfg = lvl.load_config()
        al = lcfg.get("agent_levels") or {}
        tick_seconds = float(al.get("tick_seconds") or 3600)
        level_bonus = lvl.agent_edge_bonus_bps(int(agent.get("agent_level") or 1), lcfg)
    except Exception:
        lvl = None

    try:
        from backend.services import exchange_agent_learning_service as learn
        learn_bonus = learn.learning_edge_bonus_bps(agent)
    except Exception:
        learn = None
        learn_bonus = 0.0

    try:
        from backend.services.exchange_live_execution_service import try_farm_execution_for_agent
        from backend.services.exchange_user_daemon_service import _defaults as daemon_defaults
        live_hit = try_farm_execution_for_agent(
            user_id, agent_id, agent, daemon_cfg=daemon_defaults(),
        )
    except Exception:
        live_hit = None

    if live_hit and float(live_hit.get("profit_usd") or 0) > 0:
        profit = float(live_hit["profit_usd"])
        if learn is not None:
            try:
                learn.learn_from_profit(agent, profit)
            except Exception:
                pass
        agent["realized_profit_usd"] = round(float(agent.get("realized_profit_usd") or 0) + profit, 6)
        if profit > 0:
            try:
                from backend.services.exchange_casino_leaderboard_service import record_trader_profit
                record_trader_profit(user_id, profit)
            except Exception:
                pass
        agent["trade_count"] = int(agent.get("trade_count") or 0) + 1
        agent["ticks"] = int(agent.get("ticks") or 0) + 1
        agent["game_time_sec"] = int(agent.get("game_time_sec") or 0) + int(tick_seconds)
        action = {
            "executed": True,
            "profit_usd": round(profit, 4),
            "mode": live_hit.get("mode"),
            "live_execution": True,
            "best_spread": live_hit.get("best"),
            "at": _iso(),
        }
        agent["last_action"] = action
        _write_user_agents(user_id, data)
        audit_action = "agent_live_trade" if live_hit.get("mode") == "live" else "agent_paper_profit"
        ex._audit(audit_action, user_id=user_id, amount_usd=profit, agent_id=agent_id, mode=live_hit.get("mode"))
        return {
            "success": True,
            "agent_id": agent_id,
            "action": action,
            "realized_profit_usd": agent["realized_profit_usd"],
            "agent_level": agent.get("agent_level"),
            "game_time_sec": agent.get("game_time_sec"),
        }

    trust_bonus = 0.0
    if trust_svc is not None:
        try:
            trust_bonus = trust_svc.trust_edge_for_agent(user_id, agent)
        except Exception:
            trust_bonus = 0.0

    proj = _project(agent, vol, extra_edge_bps=level_bonus + learn_bonus + trust_bonus)
    profit = float(proj.get("profit_per_cycle_usd") or 0)
    try:
        from backend.services.exchange_shop_service import profit_multiplier
        profit *= profit_multiplier(user_id)
    except Exception:
        pass

    if learn is not None:
        try:
            learn.learn_from_profit(agent, profit)
        except Exception:
            pass
    agent["realized_profit_usd"] = round(float(agent.get("realized_profit_usd") or 0) + profit, 6)
    if profit > 0:
        try:
            from backend.services.exchange_casino_leaderboard_service import record_trader_profit

            record_trader_profit(user_id, profit)
        except Exception:
            pass
    agent["trade_count"] = int(agent.get("trade_count") or 0) + 1
    agent["ticks"] = int(agent.get("ticks") or 0) + 1
    agent["game_time_sec"] = int(agent.get("game_time_sec") or 0) + int(tick_seconds)

    if lvl is not None:
        al = (lvl.load_config().get("agent_levels") or {})
        agent["agent_xp"] = round(float(agent.get("agent_xp") or 0)
                                  + max(0.0, profit) * float(al.get("xp_per_profit_usd") or 4)
                                  + float(al.get("xp_per_tick") or 2), 4)
        agent["agent_level"] = lvl.agent_level_for_xp(
            agent["agent_xp"], base=float(al.get("base_cost") or 60), growth=float(al.get("growth") or 1.2))

    action = {"executed": profit > 0, "profit_usd": round(profit, 4),
              "edge_bps": proj["blended_edge_bps"], "level_bonus_bps": round(level_bonus, 3),
              "learning_bonus_bps": round(learn_bonus, 3), "trust_bonus_bps": round(trust_bonus, 3),
              "volatility": vol, "at": _iso()}
    agent["last_action"] = action
    if trust_svc is not None:
        try:
            trust_svc.refresh_agent_trust_fields(user_id, agent)
        except Exception:
            pass
    _write_user_agents(user_id, data)
    ex._audit("agent_paper_profit", user_id=user_id, amount_usd=profit, agent_id=agent_id)

    if lvl is not None:
        try:
            lvl.record_agent_tick(user_id, profit, tick_seconds=tick_seconds)
        except Exception:
            pass

    return {"success": True, "agent_id": agent_id, "action": action,
            "realized_profit_usd": agent["realized_profit_usd"],
            "agent_level": agent.get("agent_level"), "game_time_sec": agent.get("game_time_sec"),
            "intelligence": agent.get("intelligence"), "mastery_pct": agent.get("mastery_pct"),
            "trust_score": agent.get("trust_score"), "composite_iq": agent.get("composite_iq"),
            "activation": agent.get("activation")}


def run_all_user_agents(user_id: str, *, volatility: Optional[float] = None) -> Dict[str, Any]:
    data = _read_user_agents(user_id)
    actions = []
    for agent_id, agent in data.get("agents", {}).items():
        if agent.get("enabled", True):
            actions.append(run_user_agent_tick(user_id, agent_id, volatility=volatility))
    return {"success": True, "ran": len(actions), "actions": actions}


def user_portfolio(user_id: str) -> Dict[str, Any]:
    cfg = load_config()
    vol = float(cfg.get("default_volatility") or 0.35)
    data = _read_user_agents(user_id)
    agents = list(data.get("agents", {}).values())
    rows = []
    total_realized = 0.0
    for a in agents:
        work = dict(a)
        work["skills"] = _agent_skills(a)
        enriched = skills_svc.enrich_agent_offer(work, volatility=vol)
        proj = _project(enriched, vol)
        total_realized += float(a.get("realized_profit_usd") or 0)
        rows.append({
            **enriched,
            "daily_profit_usd": proj["daily_profit_usd"],
            "monthly_projection_usd": proj["monthly_profit_usd"],
        })
    projection = calc.portfolio_projection(rows, horizon_days=30)
    return {
        "success": True,
        "user_id": user_id,
        "agent_count": len(agents),
        "total_realized_profit_usd": round(total_realized, 6),
        "projection": projection,
        "agents": sorted(rows, key=lambda r: r.get("realized_profit_usd") or 0, reverse=True),
    }


def sales_summary() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    if os.path.isfile(_SALES_PATH):
        with open(_SALES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    import json
                    rows.append(json.loads(line))
                except Exception:
                    continue
    return {
        "success": True,
        "sales_count": len(rows),
        "revenue_mn2": round(sum(float(r.get("price_mn2") or 0) for r in rows), 4),
        "revenue_usd": round(sum(float(r.get("price_usd") or 0) for r in rows), 4),
        "recent": rows[-10:][::-1],
    }


def claim_profit(user_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Convert accrued agent paper/live profit USD into the user's MN2 balance."""
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id_required"}
    data = _read_user_agents(user_id)
    agents = data.get("agents") or {}
    if agent_id:
        aid = (agent_id or "").strip()
        if aid not in agents:
            return {"success": False, "error": "agent_not_found"}
        target_ids = [aid]
    else:
        target_ids = [
            aid for aid, ag in agents.items()
            if float((ag or {}).get("realized_profit_usd") or 0) > 0
        ]

    mn2_usd = max(ex._mn2_usd(), 1e-9)
    claims: List[Dict[str, Any]] = []
    total_usd = 0.0
    for aid in target_ids:
        agent = agents.get(aid) or {}
        profit = float(agent.get("realized_profit_usd") or 0)
        if profit <= 0:
            continue
        mn2_amt = round(profit / mn2_usd, 8)
        ex._adjust_quote_balance(
            user_id, "MN2", mn2_amt, "agent_profit_claim",
            {"reference": f"claim-profit:{aid}", "amount_usd": profit, "agent_id": aid},
        )
        agent["realized_profit_usd"] = 0.0
        agent["last_claim_at"] = _iso()
        total_usd += profit
        claims.append({"agent_id": aid, "amount_usd": round(profit, 4), "mn2_credited": mn2_amt})

    if not claims:
        return {"success": False, "error": "nothing_to_claim"}

    _write_user_agents(user_id, data)
    ex._audit("agent_profit_claim", user_id=user_id, amount_usd=round(total_usd, 4), claims=claims)
    return {"success": True, "claimed_usd": round(total_usd, 4), "claims": claims}
