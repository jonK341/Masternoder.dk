"""Autonomous casino betting agents — headless parity with the casino UI."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import backend.services.casino_service as casino

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AGENTS_FILE = os.path.join(_BASE, "data", "casino_agents.json")
_MODELS_PATH = os.path.join(_BASE, "data", "casino_agent_models.json")

_GAME_DISPATCH = {
    "coin_flip": lambda uid, bet, cur, p: casino.play_coin_flip(uid, bet, p.get("choice", "heads"), cur),
    "dice": lambda uid, bet, cur, p: casino.play_dice(uid, bet, p.get("guess", 3), cur),
    "plinko": lambda uid, bet, cur, p: casino.play_plinko(uid, bet, p.get("risk", "medium"), cur),
    "wheel": lambda uid, bet, cur, p: casino.play_wheel(uid, bet, p.get("risk", "medium"), cur),
    "keno": lambda uid, bet, cur, p: casino.play_keno(uid, bet, p.get("spots", [1, 2, 3]), cur),
    "roulette": lambda uid, bet, cur, p: casino.play_roulette(uid, bet, p.get("bet_type", "red"), p.get("selection"), cur),
    "baccarat": lambda uid, bet, cur, p: casino.play_baccarat(uid, bet, p.get("side", "player"), cur),
}


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def list_models() -> Dict[str, Any]:
    data = _load_json(_MODELS_PATH)
    models = data.get("models") if isinstance(data.get("models"), dict) else data
    rows = []
    for mid, row in (models or {}).items():
        if isinstance(row, dict):
            rows.append({"model_id": mid, **row})
    return {"success": True, "models": rows, "count": len(rows)}


def list_agents() -> Dict[str, Any]:
    agents = _load_json(_AGENTS_FILE)
    rows = []
    for aid, row in agents.items():
        if isinstance(row, dict):
            rows.append({"agent_id": aid, **row})
    return {"success": True, "agents": rows, "count": len(rows)}


def _policy_for(agent: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
    cfg = casino.get_public_config()
    pol = agent.get("policy") if isinstance(agent.get("policy"), dict) else {}
    allowed = pol.get("allowed_games") or model.get("preferred_games") or ["dice", "coin_flip"]
    return {
        "min_bet": int(pol.get("min_bet") or cfg.get("min_bet") or 5),
        "max_bet": int(pol.get("max_bet") or cfg.get("max_bet") or 500),
        "allowed_games": list(allowed),
        "currency": pol.get("currency") or model.get("currency") or "coins",
        "leaderboard_period": pol.get("leaderboard_period") or "week",
        "bet_fraction": float(model.get("bet_fraction") or 0.05),
    }


def _resolve_plan(
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    balance: float,
) -> Dict[str, Any]:
    from backend.services import casino_agent_llm_planner as planner

    heuristic = planner._heuristic_plan(model, policy, balance)
    return planner.plan_bet(agent_id, user_id, model, agent, policy, heuristic_plan=heuristic)


def _execute_plan(user_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    game = plan.get("game")
    bet = plan.get("bet")
    currency = plan.get("currency") or "coins"
    params = plan.get("params") if isinstance(plan.get("params"), dict) else {}
    fn = _GAME_DISPATCH.get(str(game))
    if not fn:
        return {"success": False, "error": f"Unsupported agent game: {game}"}
    return fn(user_id, bet, currency, params)


def run_agent(agent_id: str, *, dry_run: bool = False) -> Dict[str, Any]:
    agents = _load_json(_AGENTS_FILE)
    agent = agents.get(agent_id)
    if not isinstance(agent, dict):
        return {"success": False, "error": "Agent not found"}
    policy_row = agent.get("policy") if isinstance(agent.get("policy"), dict) else {}
    if not policy_row.get("enabled", True):
        return {"success": False, "error": "Agent disabled", "agent_id": agent_id}

    models = _load_json(_MODELS_PATH).get("models") or _load_json(_MODELS_PATH)
    model_id = agent.get("model_id") or agent_id
    model = models.get(model_id) if isinstance(models, dict) else {}
    if not isinstance(model, dict):
        model = {}

    user_id = str(agent.get("user_id") or agent_id)
    policy = _policy_for(agent, model)
    balance = casino._user_balance(user_id, policy["currency"])
    resolved = _resolve_plan(agent_id, user_id, model, agent, policy, balance)
    if not resolved.get("success"):
        return resolved
    plan = resolved["plan"]
    if dry_run:
        return {"success": True, "agent_id": agent_id, "dry_run": True, "plan": plan, "used_ai": resolved.get("used_ai")}
    result = _execute_plan(user_id, plan)
    return {
        "success": bool(result.get("success")),
        "agent_id": agent_id,
        "plan": plan,
        "used_ai": resolved.get("used_ai"),
        "result": result,
    }


def run_all(*, dry_run: bool = False) -> Dict[str, Any]:
    agents = _load_json(_AGENTS_FILE)
    results: List[Dict[str, Any]] = []
    ran = 0
    for agent_id in agents:
        out = run_agent(agent_id, dry_run=dry_run)
        results.append(out)
        if out.get("success") and not dry_run:
            ran += 1
    return {"success": True, "ran": ran, "dry_run": dry_run, "results": results}
