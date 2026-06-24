"""
LLM + heuristic bet planner for casino agent bots.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from backend.services import casino_service as casino

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BRAIN_LOG = os.path.join(
    os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs"),
    "casino_agent_brain.jsonl",
)


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


def _clamp_bet(bet: float, policy: Dict[str, Any]) -> float:
    lo = float(policy.get("min_bet") or 5)
    hi = float(policy.get("max_bet") or 500)
    return max(lo, min(float(bet or lo), hi))


def _validate_plan(plan: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    allowed = [g.lower() for g in (policy.get("allowed_games") or ["dice", "coin_flip"])]
    game = (plan.get("game") or allowed[0]).strip().lower()
    if game not in allowed:
        game = allowed[0]
    bet = _clamp_bet(float(plan.get("bet") or policy.get("min_bet") or 5), policy)
    params = dict(plan.get("params") or {})
    if game == "dice":
        guess = int(params.get("guess") or 3)
        params["guess"] = max(1, min(guess, 6))
    elif game == "coin_flip":
        choice = (params.get("choice") or "heads").strip().lower()
        params["choice"] = choice if choice in ("heads", "tails") else "heads"
    elif game == "plinko":
        risk = (params.get("risk") or "medium").strip().lower()
        params["risk"] = risk if risk in ("low", "medium", "high") else "medium"
    elif game == "battle_outcome":
        pred = (params.get("prediction") or "win").strip().lower()
        params["prediction"] = pred if pred in ("win", "draw", "loss") else "win"
    elif game in ("rps_distribution", "rps_counter_pick"):
        pred = (params.get("prediction") or "rock").strip().lower()
        params["prediction"] = pred if pred in ("rock", "paper", "scissors") else "rock"
    currency = (plan.get("currency") or policy.get("currency") or "coins").strip().lower()
    out = {
        "game": game,
        "bet": bet,
        "currency": currency,
        "params": params,
        "confidence": float(plan.get("confidence") or 0.5),
        "reasoning": str(plan.get("reasoning") or plan.get("source") or ""),
        "spectator_line": str(plan.get("spectator_line") or ""),
        "source": plan.get("source") or "validated",
    }
    return out


def plan_bet(
    *,
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    heuristic_plan: Dict[str, Any],
) -> Dict[str, Any]:
    use_llm = os.environ.get("CASINO_AGENT_LLM", "0").strip().lower() in ("1", "true", "yes")
    if not use_llm:
        plan = _validate_plan({**heuristic_plan, "source": "heuristic"}, policy)
        return {"success": True, "used_ai": False, "plan": plan}

    try:
        from backend.services.agent_ai_router import routed_chat
    except Exception:
        plan = _validate_plan({**heuristic_plan, "source": "heuristic"}, policy)
        return {"success": True, "used_ai": False, "plan": plan}

    lb = casino.get_leaderboard(period=policy.get("leaderboard_period") or "week")
    hist = casino.get_history(user_id, limit=8)
    bal = casino.get_balance(user_id)
    context = {
        "agent_id": agent_id,
        "model": model.get("name") or agent_id,
        "strategy": model.get("strategy"),
        "balance": casino._user_balance(user_id, policy.get("currency") or "coins"),
        "heuristic": heuristic_plan,
        "leaderboard_top": (lb.get("leaderboard") or [])[:5],
        "recent_bets": (hist.get("history") or [])[:5],
        "bets_today": bal.get("bets_today"),
    }
    prompt = (
        "Return ONLY JSON for a single casino bet plan: "
        '{"game":"dice|coin_flip|plinko|battle_outcome|rps_distribution",'
        '"bet":number,"confidence":0-1,"reasoning":"short","spectator_line":"short",'
        '"params":{...}}. '
        f"Allowed games: {policy.get('allowed_games')}. "
        f"Context: {json.dumps(context, default=str)}"
    )
    task_kind = model.get("task_kind") or "casino_bet_plan"
    try:
        resp, meta = routed_chat(
            [{"role": "user", "content": prompt}],
            task_kind,
            user_id,
        )
    except Exception:
        plan = _validate_plan({**heuristic_plan, "source": "heuristic"}, policy)
        return {"success": True, "used_ai": False, "plan": plan}

    if not resp or not getattr(resp, "success", False):
        plan = _validate_plan({**heuristic_plan, "source": "heuristic"}, policy)
        return {"success": True, "used_ai": False, "plan": plan}

    parsed = _extract_json(getattr(resp, "content", "") or "")
    if not parsed:
        plan = _validate_plan({**heuristic_plan, "source": "heuristic"}, policy)
        return {"success": True, "used_ai": False, "plan": plan}

    plan = _validate_plan({**parsed, "source": "llm"}, policy)
    try:
        os.makedirs(os.path.dirname(_BRAIN_LOG), exist_ok=True)
        with open(_BRAIN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"agent_id": agent_id, "plan": plan, "meta": meta}, default=str) + "\n")
    except Exception:
        pass
    return {"success": True, "used_ai": True, "plan": plan, "trace": meta}
