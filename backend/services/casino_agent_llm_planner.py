"""LLM-assisted bet planning for autonomous casino agents."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import backend.services.casino_service as casino

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BRAIN_LOG = os.path.join(_BASE, "logs", "casino_agent_brain.jsonl")


def _llm_enabled() -> bool:
    return os.environ.get("CASINO_AGENT_LLM", "0").strip().lower() in ("1", "true", "yes")


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _validate_plan(plan: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    allowed = [str(g) for g in (policy.get("allowed_games") or ["dice", "coin_flip"])]
    game = str(plan.get("game") or allowed[0])
    if game not in allowed:
        game = allowed[0]
    min_bet = int(policy.get("min_bet") or 5)
    max_bet = int(policy.get("max_bet") or 500)
    try:
        bet = int(plan.get("bet") or min_bet)
    except (TypeError, ValueError):
        bet = min_bet
    bet = max(min_bet, min(max_bet, bet))
    params = plan.get("params") if isinstance(plan.get("params"), dict) else {}
    if game == "dice":
        try:
            guess = int(params.get("guess") or 1)
        except (TypeError, ValueError):
            guess = 1
        params["guess"] = max(1, min(6, guess))
    elif game == "coin_flip":
        choice = str(params.get("choice") or "heads").lower()
        params["choice"] = choice if choice in ("heads", "tails") else "heads"
    return {
        "game": game,
        "bet": bet,
        "currency": policy.get("currency") or "coins",
        "params": params,
        "confidence": float(plan.get("confidence") or 0.5),
        "reasoning": str(plan.get("reasoning") or ""),
        "spectator_line": str(plan.get("spectator_line") or ""),
        "source": plan.get("source") or "llm",
    }


def _heuristic_plan(model: Dict[str, Any], policy: Dict[str, Any], balance: float) -> Dict[str, Any]:
    preferred = [str(g) for g in (model.get("preferred_games") or policy.get("allowed_games") or ["dice"])]
    game = preferred[0] if preferred else "dice"
    frac = float(model.get("bet_fraction") or policy.get("bet_fraction") or 0.05)
    min_bet = int(policy.get("min_bet") or 5)
    max_bet = int(policy.get("max_bet") or 500)
    bet = max(min_bet, min(max_bet, int(balance * frac) or min_bet))
    params: Dict[str, Any] = {}
    if game == "dice":
        params["guess"] = 3
    elif game == "coin_flip":
        params["choice"] = "heads"
    return _validate_plan({"game": game, "bet": bet, "params": params, "source": "heuristic"}, policy)


def plan_bet(
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    heuristic_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    balance = casino._user_balance(user_id, policy.get("currency") or "coins")
    fallback = _validate_plan(heuristic_plan or _heuristic_plan(model, policy, balance), policy)
    if not _llm_enabled():
        return {"success": True, "used_ai": False, "plan": fallback}

    period = policy.get("leaderboard_period") or "week"
    try:
        board = casino.get_leaderboard(period=period, user_id=user_id, currency=policy.get("currency") or "coins")
        history = casino.get_history(user_id, limit=5)
        bal = casino.get_balance(user_id)
    except Exception:
        board, history, bal = {"leaderboard": []}, {"history": []}, {}

    prompt = (
        f"You are {model.get('name') or agent_id}, a casino betting agent.\n"
        f"Balance: {balance}. Bets today: {bal.get('bets_today') if isinstance(bal, dict) else '?'}\n"
        f"Allowed games: {policy.get('allowed_games')}. Bet range: {policy.get('min_bet')}-{policy.get('max_bet')}.\n"
        f"Leaderboard: {json.dumps(board.get('leaderboard', [])[:3])}\n"
        f"Recent history: {json.dumps(history.get('history', [])[:3])}\n"
        "Return JSON only: {\"game\",\"bet\",\"confidence\",\"reasoning\",\"spectator_line\",\"params\"}."
    )
    try:
        from backend.services.agent_ai_router import routed_chat

        resp, _meta = routed_chat(
            task_kind=model.get("task_kind") or "casino_bet_plan",
            user_id=user_id,
            messages=[{"role": "user", "content": prompt}],
            task_type=model.get("llm_task_type") or "reason",
        )
        if not resp.success:
            return {"success": True, "used_ai": False, "plan": fallback}
        parsed = _extract_json(resp.content or "")
        if not parsed:
            return {"success": True, "used_ai": False, "plan": fallback}
        plan = _validate_plan({**parsed, "source": "llm"}, policy)
        try:
            os.makedirs(os.path.dirname(_BRAIN_LOG), exist_ok=True)
            with open(_BRAIN_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"agent_id": agent_id, "user_id": user_id, "plan": plan}) + "\n")
        except OSError:
            pass
        return {"success": True, "used_ai": True, "plan": plan}
    except Exception:
        return {"success": True, "used_ai": False, "plan": fallback}
