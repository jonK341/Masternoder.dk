"""
Casino agent bots — auto-play casino games for configured users.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from backend.services import casino_service as casino
from backend.services import casino_agent_llm_planner as planner
from backend.services import casino_calculator_service as calc_svc
from backend.services import casino_prognosis_service as prognosis_svc

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AGENTS_FILE = os.path.join(_ROOT, "data", "casino_agents.json")
_MODELS_PATH = os.path.join(_ROOT, "data", "casino_agent_models.json")

_PLAY_HANDLERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "coin_flip": lambda uid, bet, cur, p: casino.play_coin_flip(uid, bet, (p.get("choice") or "heads"), cur),
    "dice": lambda uid, bet, cur, p: casino.play_dice(uid, bet, int(p.get("guess") or 3), cur),
    "plinko": lambda uid, bet, cur, p: casino.play_plinko(uid, bet, (p.get("risk") or "medium"), cur),
    "wheel": lambda uid, bet, cur, p: casino.play_wheel(uid, bet, (p.get("risk") or "medium"), cur),
    "scratch_card": lambda uid, bet, cur, p: casino.play_scratch_card(uid, bet, cur),
    "battle_outcome": lambda uid, bet, cur, p: casino.play_battle_outcome_bet(
        uid, bet, (p.get("prediction") or "win"), p.get("difficulty"), cur
    ),
    "rps_distribution": lambda uid, bet, cur, p: casino.play_rps_distribution_bet(
        uid, bet, (p.get("prediction") or "rock"), p.get("difficulty"), p.get("player_move"), cur
    ),
    "rps_counter_pick": lambda uid, bet, cur, p: casino.play_rps_counter_pick(
        uid,
        bet,
        (p.get("choice") or p.get("prediction") or "rock"),
        p.get("difficulty"),
        p.get("player_move"),
        cur,
    ),
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


def _load_models() -> Dict[str, Any]:
    data = _load_json(_MODELS_PATH)
    return data.get("models") if isinstance(data.get("models"), dict) else {}


def _load_agents() -> Dict[str, Any]:
    return _load_json(_AGENTS_FILE)


def list_models() -> Dict[str, Any]:
    models = _load_models()
    items = [{"model_id": mid, **row} for mid, row in models.items() if isinstance(row, dict)]
    return {"success": True, "count": len(items), "models": items}


def list_agents() -> Dict[str, Any]:
    agents_raw = _load_agents()
    models = _load_models()
    items: List[Dict[str, Any]] = []
    for aid, row in agents_raw.items():
        if not isinstance(row, dict):
            continue
        model_id = row.get("model_id") or aid
        model = models.get(model_id) or {}
        pol = row.get("policy") if isinstance(row.get("policy"), dict) else {}
        items.append(
            {
                "agent_id": aid,
                "user_id": row.get("user_id"),
                "model_id": model_id,
                "model_name": model.get("name") or model_id,
                "enabled": bool(pol.get("enabled", True)),
                "policy": pol,
                "spectator_persona": model.get("spectator_persona"),
            }
        )
    return {"success": True, "count": len(items), "agents": items}


def _heuristic_plan(
    model: Dict[str, Any],
    policy: Dict[str, Any],
    balance: float,
    currency: str,
) -> Dict[str, Any]:
    cfg = casino.get_public_config() or {}
    min_bet = float(policy.get("min_bet") or cfg.get("min_bet") or 5)
    max_bet = float(policy.get("max_bet") or cfg.get("max_bet") or 500)
    allowed = [g.lower() for g in (policy.get("allowed_games") or model.get("preferred_games") or ["dice"])]
    preferred = [g.lower() for g in (model.get("preferred_games") or []) if g.lower() in allowed]
    game = preferred[0] if preferred else (allowed[0] if allowed else "dice")

    frac = float(model.get("bet_fraction") or 0.05)
    gcfg = (cfg.get("games") or {}).get(game) or {}
    mult = float(gcfg.get("payout_multiplier") or 1.9)
    if game == "dice":
        mult = float(gcfg.get("payout_multiplier") or 4.0)
    wp = calc_svc.win_probability_estimate(game).get("win_probability", 0.5)
    kelly = calc_svc.kelly_bet_size(balance, wp, mult, fraction=frac)
    bet = max(min_bet, min(kelly.get("suggested_stake") or min_bet, max_bet))

    params: Dict[str, Any] = {}
    if game == "dice":
        params["guess"] = 3
    elif game == "coin_flip":
        params["choice"] = "heads"
    elif game == "plinko":
        params["risk"] = "medium"
    elif game == "battle_outcome":
        sig = prognosis_svc.battle_outcome_prognosis()
        params["prediction"] = sig.get("signal") or "win"
    elif game in ("rps_distribution", "rps_counter_pick"):
        sig = prognosis_svc.rps_prognosis()
        params["prediction"] = sig.get("signal") or "rock"

    return {
        "game": game,
        "bet": round(bet, 2),
        "currency": currency,
        "params": params,
        "source": "heuristic",
        "reasoning": f"Kelly {frac:.0%} on {game} from balance {balance:.0f}.",
    }


def _resolve_plan(
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    balance: float,
) -> Dict[str, Any]:
    currency = (policy.get("currency") or model.get("currency") or "coins").strip().lower()
    if "allowed_games" not in policy:
        policy = {**policy, "allowed_games": model.get("preferred_games") or ["dice", "coin_flip"]}
    heuristic = _heuristic_plan(model, policy, balance, currency)
    return planner.plan_bet(
        agent_id=agent_id,
        user_id=user_id,
        model=model,
        agent=agent,
        policy=policy,
        heuristic_plan=heuristic,
    )


def _execute_plan(user_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    game = (plan.get("game") or "").strip().lower()
    handler = _PLAY_HANDLERS.get(game)
    if not handler:
        return {"success": False, "error": f"unsupported_game:{game}"}
    return handler(user_id, plan.get("bet"), plan.get("currency") or "coins", plan.get("params") or {})


def run_all(*, dry_run: bool = False, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    agents_raw = _load_agents()
    models = _load_models()
    results: List[Dict[str, Any]] = []
    ran = 0

    for aid, row in agents_raw.items():
        if agent_ids and aid not in agent_ids:
            continue
        if not isinstance(row, dict):
            continue
        pol = row.get("policy") if isinstance(row.get("policy"), dict) else {}
        if not pol.get("enabled", True):
            continue
        user_id = str(row.get("user_id") or "").strip()
        if not user_id:
            continue
        model_id = row.get("model_id") or aid
        model = models.get(model_id) or {}
        currency = (pol.get("currency") or model.get("currency") or "coins").strip().lower()
        balance = casino._user_balance(user_id, currency)
        resolved = _resolve_plan(aid, user_id, model, row, pol, balance)
        entry: Dict[str, Any] = {
            "agent_id": aid,
            "user_id": user_id,
            "used_ai": resolved.get("used_ai", False),
            "plan": resolved.get("plan"),
        }
        if dry_run:
            entry["dry_run"] = True
            results.append(entry)
            ran += 1
            continue
        if not resolved.get("success"):
            entry["error"] = resolved.get("error") or "plan_failed"
            results.append(entry)
            continue
        play = _execute_plan(user_id, resolved.get("plan") or {})
        entry["play"] = play
        results.append(entry)
        ran += 1

    return {"success": True, "ran": ran, "dry_run": dry_run, "results": results}
