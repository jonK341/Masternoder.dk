"""Shared post-trade learning: skill proficiency, IQ, and optional PPP skill stacks."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def resolve_skill_ids_for_agent(
    agent_id: str,
    *,
    agent_row: Optional[Dict[str, Any]] = None,
    account: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Merge skills from arb agent config, AI config, signal-stack config, or account."""
    ids: List[str] = []
    seen = set()

    def _add(raw: Any) -> None:
        for sid in raw or []:
            s = str(sid or "").strip()
            if s and s not in seen:
                seen.add(s)
                ids.append(s)

    acct = account or {}
    _add(acct.get("skills"))

    row = agent_row or {}
    _add(row.get("skills"))
    ss = row.get("skill_set")
    if ss:
        try:
            from backend.services.exchange_bot_skills_service import resolve_skill_set

            resolved = resolve_skill_set(str(ss))
            _add(resolved.get("skills"))
        except Exception:
            pass

    if ids:
        return ids

    aid = str(agent_id or "").strip()
    if aid == "ai_market_trader" or aid.startswith("ai_"):
        try:
            from backend.services.exchange_ai_trading_service import load_ai_config

            _add(load_ai_config().get("default_skills"))
        except Exception:
            pass

    if aid.startswith("arb_signal") or aid == "arb_signal_stack":
        try:
            from backend.services.exchange_signal_stack_service import load_config

            _add(load_config().get("default_skills"))
        except Exception:
            pass

    if not ids:
        _add(["spatial_arbitrage", "withdrawal_aware_routing"])
    return ids


def merge_skills_into_account(acct: Dict[str, Any], skill_ids: List[str]) -> None:
    if not skill_ids:
        return
    existing = list(acct.get("skills") or [])
    merged = list(dict.fromkeys(existing + list(skill_ids)))
    acct["skills"] = merged
    prof: Dict[str, float] = dict(acct.get("skill_proficiency") or {})
    for sid in merged:
        prof.setdefault(sid, float(prof.get(sid) or 0.15))
    acct["skill_proficiency"] = prof


def apply_profit_learning(
    acct: Dict[str, Any],
    profit_usd: float,
    *,
    agent_id: Optional[str] = None,
    agent_row: Optional[Dict[str, Any]] = None,
    sync_ledger_skills: bool = False,
) -> Dict[str, Any]:
    """Update agent account after realized profit (in-place)."""
    profit = float(profit_usd or 0)
    if profit <= 0:
        return {"success": True, "skipped": True, "reason": "zero_profit"}

    aid = str(agent_id or acct.get("agent_id") or "").strip()
    skill_ids = resolve_skill_ids_for_agent(aid, agent_row=agent_row, account=acct)
    merge_skills_into_account(acct, skill_ids)

    out: Dict[str, Any] = {"success": True, "agent_id": aid, "profit_usd": profit}
    try:
        from backend.services.exchange_agent_learning_service import learn_from_profit

        out["learning"] = learn_from_profit(acct, profit)
    except Exception as exc:
        out["learning_error"] = str(exc)[:120]

    try:
        from backend.services.exchange_leveling_service import agent_level_for_xp, agent_edge_bonus_bps

        ticks = int(acct.get("ticks") or 0)
        lvl = agent_level_for_xp(float(ticks * 12))
        acct["agent_level"] = max(int(acct.get("agent_level") or 1), lvl)
        acct["level_edge_bonus_bps"] = agent_edge_bonus_bps(int(acct.get("agent_level") or 1))
    except Exception:
        pass

    if sync_ledger_skills and aid:
        try:
            from backend.services.exchange_profit_agent_skills_service import sync_from_ledger_research

            out["skills_sync"] = sync_from_ledger_research(agent_id=aid, limit=40)
        except Exception as exc:
            out["skills_sync_error"] = str(exc)[:120]

    return out
