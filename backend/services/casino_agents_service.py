"""
Casino agent personas — specialized AI models that play for leaderboard rank.

Each persona binds an agent_id (from data/casino_agent_models.json) to a user_id
and policy. `run_agent` executes ONE play step via casino_service (coins rail by
default). State: data/casino_agents.json, audit: logs/casino_agent_activity.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import backend.services.casino_service as casino

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODELS_PATH = os.path.join(_BASE, "data", "casino_agent_models.json")
_AGENTS_FILE = os.path.join(_BASE, "data", "casino_agents.json")
_ACTIVITY_FILE = "casino_agent_activity.jsonl"

_DEFAULT_POLICY = {
    "enabled": True,
    "currency": "coins",
    "bet_fraction": 0.03,
    "min_bet": 5,
    "max_bet": 200,
    "seed_coins": 5000,
    "seed_if_below": 100,
    "max_bets_per_run": 1,
    "leaderboard_mode": True,
    "leaderboard_period": "week",
    "allowed_games": ["dice", "coin_flip", "slot_classic", "slot_diamond", "plinko", "wheel", "crash", "rps_bet"],
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_BASE, "logs")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load_models() -> Dict[str, Any]:
    raw = _load_json(_MODELS_PATH, {"models": {}})
    models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
    return models


def get_model(agent_id: str) -> Optional[Dict[str, Any]]:
    return load_models().get(agent_id)


def _load_agents() -> Dict[str, Any]:
    return _load_json(_AGENTS_FILE, {})


def _save_agents(data: Dict[str, Any]) -> None:
    _save_json(_AGENTS_FILE, data)


def _policy(agent: Dict[str, Any], model: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pol = dict(_DEFAULT_POLICY)
    if model:
        if model.get("bet_fraction") is not None:
            pol["bet_fraction"] = float(model["bet_fraction"])
        if model.get("currency"):
            pol["currency"] = model["currency"]
        if model.get("preferred_games"):
            pol["allowed_games"] = list(model["preferred_games"]) + pol["allowed_games"]
    pol.update(agent.get("policy") or {})
    return pol


def _audit(agent_id: str, user_id: str, payload: Dict[str, Any]) -> None:
    path = os.path.join(_log_dir(), _ACTIVITY_FILE)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        row = {"ts": _iso(), "agent_id": agent_id, "user_id": user_id, **payload}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception:
        pass


def _seed_default_agents() -> None:
    agents = _load_agents()
    if agents:
        return
    models = load_models()
    for agent_id, model in models.items():
        user_id = f"casino_{agent_id}"
        agents[agent_id] = {
            "user_id": user_id,
            "model_id": agent_id,
            "policy": {"enabled": True},
            "created_at": _iso(),
        }
    _save_agents(agents)


def _ensure_bankroll(user_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
    currency = policy.get("currency") or "coins"
    bal = casino._user_balance(user_id, currency)
    floor = float(policy.get("seed_if_below") or 100)
    target = float(policy.get("seed_coins") or 5000)
    if currency != "coins":
        return {"seeded": False, "balance": bal}
    if bal >= floor:
        return {"seeded": False, "balance": bal}
    need = max(target - bal, floor)
    try:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            user_id, "coins", need,
            source="casino_agent_seed",
            metadata={"reason": "agent_bankroll"},
        )
        return {"seeded": True, "amount": need, "balance": casino._user_coins(user_id)}
    except Exception as exc:
        return {"seeded": False, "error": str(exc), "balance": bal}


def _bet_size(user_id: str, policy: Dict[str, Any], *, boost: float = 1.0) -> float:
    currency = policy.get("currency") or "coins"
    bal = max(casino._user_balance(user_id, currency), 0.0)
    frac = float(policy.get("bet_fraction") or 0.03) * boost
    raw = bal * frac
    mn = float(policy.get("min_bet") or casino.get_public_config().get("min_bet") or 5)
    mx = float(policy.get("max_bet") or casino.get_public_config().get("max_bet") or 200)
    bet = max(mn, min(mx, raw))
    if currency == "coins":
        return float(int(bet))
    return round(bet, 8 if currency == "mn2" else 2)


def _leaderboard_boost(user_id: str, period: str) -> float:
    try:
        board = casino.get_leaderboard(period=period, limit=100, currency="coins").get("leaderboard") or []
        rank = None
        for row in board:
            if row.get("user_id") == user_id:
                rank = row.get("rank")
                break
        if rank is None:
            return 1.15
        if rank <= 3:
            return 0.85
        if rank <= 10:
            return 1.0
        return 1.2
    except Exception:
        return 1.0


def _pick_game(policy: Dict[str, Any], model: Optional[Dict[str, Any]], strategy: str) -> str:
    allowed = set(policy.get("allowed_games") or [])
    preferred = [g for g in (model or {}).get("preferred_games") or [] if g in allowed]
    pool = preferred or list(allowed)
    if strategy == "slot_hunter":
        for g in ("slot_classic", "slot_diamond"):
            if g in allowed:
                return g
    if strategy == "crash_timer" and "crash" in allowed:
        return "crash"
    if not pool:
        return "dice"
    return random.choice(pool)


def _play_step(
    user_id: str,
    game: str,
    bet: float,
    currency: str,
    model: Optional[Dict[str, Any]],
    agent: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    strategy = (model or {}).get("strategy") or "kelly_flat"
    params = params if isinstance(params, dict) else {}

    if game == "crash":
        lo, hi = (model or {}).get("auto_cashout_range") or [1.4, 2.0]
        try:
            auto = float(params.get("auto_cashout"))
        except (TypeError, ValueError):
            auto = random.uniform(float(lo), float(hi))
        auto = round(max(1.2, min(3.0, auto)), 2)
        return casino.start_crash_round(user_id, bet, currency=currency, auto_cashout=auto)

    if game in ("slot_classic", "slot_diamond"):
        fn = casino.play_slot_classic if game == "slot_classic" else casino.play_slot_diamond
        return fn(user_id, bet, currency=currency)

    if game == "plinko":
        risk = str(params.get("risk") or "medium").lower()
        if risk not in ("low", "medium", "high"):
            risk = "medium"
        return casino.play_plinko(user_id, bet, risk=risk, currency=currency)

    if game == "wheel":
        risk = str(params.get("risk") or "medium").lower()
        if risk not in ("low", "medium", "high"):
            risk = "medium"
        return casino.play_wheel(user_id, bet, risk=risk, currency=currency)

    if game == "coin_flip":
        choice = str(params.get("choice") or random.choice(["heads", "tails"])).lower()
        if choice not in ("heads", "tails"):
            choice = "heads"
        if strategy == "martingale_conservative" and agent.get("last_outcome") == "loss":
            choice = agent.get("last_choice") or choice
        return casino.play_coin_flip(user_id, bet, choice, currency=currency)

    if game == "rps_bet":
        pick = str(params.get("pick") or params.get("choice") or random.choice(["rock", "paper", "scissors"])).lower()
        if pick not in ("rock", "paper", "scissors"):
            pick = "rock"
        return casino.play_rps_bet(user_id, bet, pick, currency=currency)

    sides = int((casino.get_public_config().get("games") or {}).get("dice", {}).get("sides") or 6)
    try:
        guess = int(params.get("guess", random.randint(1, sides)))
    except (TypeError, ValueError):
        guess = random.randint(1, sides)
    guess = max(1, min(sides, guess))
    return casino.play_dice(user_id, bet, guess, currency=currency)


def _heuristic_plan(
    user_id: str,
    pol: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    agent: Dict[str, Any],
    boost: float,
) -> Dict[str, Any]:
    strategy = (model or {}).get("strategy") or "kelly_flat"
    bet = _bet_size(user_id, pol, boost=boost)
    game = _pick_game(pol, model, strategy)
    if strategy == "martingale_conservative" and agent.get("last_outcome") == "loss":
        steps = int(agent.get("martingale_step") or 0)
        max_steps = int((model or {}).get("martingale_max_steps") or pol.get("martingale_max_steps") or 3)
        if steps < max_steps:
            bet = min(float(pol.get("max_bet") or 200), bet * (1.8 ** (steps + 1)))
    return {
        "game": game,
        "bet": bet,
        "currency": pol.get("currency") or "coins",
        "strategy": strategy,
        "boost": boost,
        "source": "heuristic",
        "confidence": 0.4,
        "reasoning": f"Heuristic {strategy}: {game} for {int(bet)} coins",
        "params": {},
    }


def _resolve_plan(
    agent_id: str,
    user_id: str,
    model: Optional[Dict[str, Any]],
    agent: Dict[str, Any],
    pol: Dict[str, Any],
    boost: float,
) -> Dict[str, Any]:
    heuristic = _heuristic_plan(user_id, pol, model, agent, boost)
    if not model:
        return {"success": True, "plan": heuristic, "used_ai": False}

    try:
        from backend.services.casino_agent_llm_planner import plan_bet, llm_enabled
        if llm_enabled():
            llm = plan_bet(
                agent_id=agent_id,
                user_id=user_id,
                model=model,
                agent=agent,
                policy=pol,
                heuristic_plan=heuristic,
            )
            if llm.get("success"):
                plan = llm.get("plan") or {}
                plan["source"] = "llm"
                plan["strategy"] = heuristic.get("strategy")
                plan["boost"] = boost
                plan["routing"] = llm.get("routing")
                plan["provider"] = llm.get("provider")
                plan["brain"] = llm.get("brain")
                return {"success": True, "plan": plan, "used_ai": True, "llm": llm}
            if os.environ.get("CASINO_AGENT_LLM_REQUIRED", "0") == "1":
                return {"success": False, "used_ai": True, "error": llm.get("reason"), "llm": llm}
    except Exception as exc:
        if os.environ.get("CASINO_AGENT_LLM_REQUIRED", "0") == "1":
            return {"success": False, "used_ai": False, "error": str(exc)}

    return {"success": True, "plan": heuristic, "used_ai": False}


def plan_agent(agent_id: str) -> Dict[str, Any]:
    """Preview next bet (LLM + context) without playing."""
    _seed_default_agents()
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        return {"success": False, "error": f"unknown agent '{agent_id}'"}
    model = get_model(agent.get("model_id") or agent_id)
    user_id = str(agent.get("user_id") or "").strip()
    pol = _policy(agent, model)
    boost = _leaderboard_boost(user_id, pol.get("leaderboard_period") or "week") if pol.get("leaderboard_mode") else 1.0
    resolved = _resolve_plan(agent_id, user_id, model, agent, pol, boost)
    if not resolved.get("success"):
        return resolved
    try:
        from backend.services.casino_agent_llm_planner import build_context, llm_enabled
        ctx = build_context(
            agent_id=agent_id,
            user_id=user_id,
            model=model or {},
            agent=agent,
            policy=pol,
            heuristic_plan=resolved["plan"],
        )
        ai_on = llm_enabled()
    except Exception:
        ctx = {}
        ai_on = False
    return {
        "success": True,
        "agent_id": agent_id,
        "used_ai": resolved.get("used_ai"),
        "llm_available": ai_on,
        "plan": resolved.get("plan"),
        "context": ctx,
    }


def agent_brain(agent_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    from backend.services.casino_agent_llm_planner import recent_brain, llm_enabled
    rows = recent_brain(agent_id, limit=limit)
    agents = _load_agents()
    persona = None
    if agent_id and agent_id in agents:
        model = get_model(agents[agent_id].get("model_id") or agent_id)
        persona = {
            "name": (model or {}).get("name"),
            "strategy": (model or {}).get("strategy"),
            "description": (model or {}).get("description"),
        }
    return {
        "success": True,
        "llm_enabled": llm_enabled(),
        "agent_id": agent_id,
        "persona": persona,
        "thoughts": rows,
        "count": len(rows),
    }


def _maybe_join_tournament(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        from backend.services import casino_tournaments
        listing = casino_tournaments.list_tournaments(user_id)
        for t in (listing.get("tournaments") or []):
            if t.get("status") != "running":
                continue
            if (t.get("currency") or "coins") != "coins":
                continue
            tid = t.get("id")
            if not tid:
                continue
            if user_id in (t.get("entries") or {}):
                return {"joined": True, "tournament_id": tid}
            return casino_tournaments.join_tournament(user_id, tid)
    except Exception:
        pass
    return None


def list_agents() -> Dict[str, Any]:
    _seed_default_agents()
    agents = _load_agents()
    models = load_models()
    out = []
    for aid, a in agents.items():
        model = models.get(a.get("model_id") or aid) or models.get(aid)
        pol = _policy(a, model)
        out.append({
            "agent_id": aid,
            "user_id": a.get("user_id"),
            "model": {
                "name": (model or {}).get("name"),
                "strategy": (model or {}).get("strategy"),
                "specialization": (model or {}).get("specialization"),
                "skills": (model or {}).get("skills") or [],
            },
            "enabled": bool(pol.get("enabled", True)),
            "currency": pol.get("currency"),
            "leaderboard_mode": pol.get("leaderboard_mode"),
            "last_thought": (a.get("brain_log") or [{}])[0] if isinstance(a.get("brain_log"), list) else None,
        })
    try:
        from backend.services.casino_agent_llm_planner import llm_enabled
        ai_on = llm_enabled()
    except Exception:
        ai_on = False
    return {
        "success": True,
        "agents": out,
        "models": list(models.keys()),
        "count": len(out),
        "automation_enabled": os.environ.get("CASINO_AGENT_AUTOMATION", "1") != "0",
        "llm_enabled": ai_on,
    }


def list_models() -> Dict[str, Any]:
    models = load_models()
    items = []
    for mid, m in models.items():
        items.append({
            "model_id": mid,
            "name": m.get("name"),
            "specialization": m.get("specialization"),
            "strategy": m.get("strategy"),
            "skills": m.get("skills") or [],
            "task_kind": m.get("task_kind"),
            "description": m.get("description"),
        })
    return {"success": True, "models": items, "count": len(items)}


def upsert_agent(agent_id: str, user_id: str, policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    agent_id = str(agent_id or "").strip()
    user_id = str(user_id or "").strip()
    if not agent_id or not user_id:
        return {"success": False, "error": "agent_id and user_id required"}
    agents = _load_agents()
    rec = agents.get(agent_id) or {}
    rec["user_id"] = user_id
    rec.setdefault("model_id", agent_id)
    pol = dict(rec.get("policy") or {})
    if isinstance(policy, dict):
        pol.update(policy)
    rec["policy"] = pol
    rec["updated_at"] = _iso()
    agents[agent_id] = rec
    _save_agents(agents)
    model = get_model(rec.get("model_id") or agent_id)
    return {"success": True, "agent_id": agent_id, "user_id": user_id, "policy": _policy(rec, model)}


def run_agent(agent_id: str, dry_run: bool = False) -> Dict[str, Any]:
    agent_id = str(agent_id or "").strip()
    try:
        from backend.services.agent_kill_switch import check_action
        halt = check_action("run_casino_agent", agent_id=agent_id)
        if not halt.get("allowed"):
            return {"success": False, **halt}
    except ImportError:
        pass

    if os.environ.get("CASINO_AGENT_AUTOMATION", "1") == "0":
        return {"success": False, "error": "casino agent automation disabled", "code": "automation_disabled"}

    _seed_default_agents()
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        return {"success": False, "error": f"unknown agent '{agent_id}'", "code": "unknown_agent"}

    model = get_model(agent.get("model_id") or agent_id)
    user_id = str(agent.get("user_id") or "").strip()
    pol = _policy(agent, model)
    if not pol.get("enabled", True):
        return {"success": False, "error": "agent disabled", "code": "disabled", "agent_id": agent_id}

    strategy = (model or {}).get("strategy") or "kelly_flat"
    actions: List[Dict[str, Any]] = []

    bankroll = _ensure_bankroll(user_id, pol)
    actions.append({"action": "bankroll", **bankroll})

    if strategy == "tournament_grinder":
        tjoin = _maybe_join_tournament(user_id)
        if tjoin:
            actions.append({"action": "tournament", **tjoin})

    boost = 1.0
    if pol.get("leaderboard_mode"):
        boost = _leaderboard_boost(user_id, pol.get("leaderboard_period") or "week")

    resolved = _resolve_plan(agent_id, user_id, model, agent, pol, boost)
    if not resolved.get("success"):
        return {"success": False, "agent_id": agent_id, "error": resolved.get("error"), "used_ai": resolved.get("used_ai")}

    plan = resolved.get("plan") or {}
    game = plan.get("game") or "dice"
    bet = float(plan.get("bet") or _bet_size(user_id, pol, boost=boost))
    currency = plan.get("currency") or pol.get("currency") or "coins"
    params = plan.get("params") if isinstance(plan.get("params"), dict) else {}
    used_ai = bool(resolved.get("used_ai"))

    if dry_run:
        actions.append({"action": "play", "planned": True, "used_ai": used_ai, **plan})
        return {"success": True, "agent_id": agent_id, "user_id": user_id, "dry_run": True, "used_ai": used_ai, "actions": actions}

    if plan.get("strategy") == "martingale_conservative" and agent.get("last_outcome") == "loss" and not used_ai:
        steps = int(agent.get("martingale_step") or 0)
        max_steps = int((model or {}).get("martingale_max_steps") or pol.get("martingale_max_steps") or 3)
        if steps < max_steps:
            agent["martingale_step"] = steps + 1
        else:
            agent["martingale_step"] = 0

    result = _play_step(user_id, game, bet, currency, model, agent, params=params)
    actions.append({"action": "play", "used_ai": used_ai, "plan": plan, "result": result})

    if result.get("success"):
        agent["last_outcome"] = result.get("outcome")
        agent["last_game"] = game
        agent["last_net"] = result.get("net")
        if game == "coin_flip":
            agent["last_choice"] = (result.get("details") or {}).get("choice")
        if result.get("outcome") == "win":
            agent["martingale_step"] = 0
        brain_log = agent.get("brain_log") if isinstance(agent.get("brain_log"), list) else []
        if used_ai and plan.get("reasoning"):
            brain_log.insert(0, {
                "ts": _iso(),
                "reasoning": plan.get("reasoning"),
                "spectator_line": plan.get("spectator_line"),
                "game": game,
                "bet": bet,
                "confidence": plan.get("confidence"),
                "provider": plan.get("provider"),
                "outcome": result.get("outcome"),
                "net": result.get("net"),
            })
            agent["brain_log"] = brain_log[:8]
        try:
            from backend.services.agent_db_service import agent_db_service
            agent_db_service.record_agent_activity(
                user_id=user_id,
                agent_id=agent_id,
                action="casino_play",
                skill=(model or {}).get("skills", ["leaderboard_racing"])[0],
                xp_gained=2 if (result.get("net") or 0) > 0 else 1,
                metadata={"game": game, "net": result.get("net"), "bet_id": result.get("bet_id")},
            )
        except Exception:
            pass
        try:
            from backend.services.activity_events_service import emit
            emit(
                "casino_agent_play",
                channel="casino",
                user_id=user_id,
                payload={
                    "agent_id": agent_id,
                    "game": game,
                    "net": result.get("net"),
                    "bet": bet,
                    "used_ai": used_ai,
                    "reasoning": plan.get("reasoning"),
                    "spectator_line": plan.get("spectator_line"),
                    "confidence": plan.get("confidence"),
                },
            )
        except Exception:
            pass

    agent["last_run_at"] = _iso()
    agents[agent_id] = agent
    _save_agents(agents)
    _audit(agent_id, user_id, {"actions": actions})

    return {
        "success": bool(result.get("success")),
        "agent_id": agent_id,
        "user_id": user_id,
        "dry_run": False,
        "used_ai": used_ai,
        "actions": actions,
        "balance": casino.get_balance(user_id),
    }


def run_all(dry_run: bool = False) -> Dict[str, Any]:
    try:
        from backend.services.agent_kill_switch import check_action
        halt = check_action("run_casino_all")
        if not halt.get("allowed"):
            return {"success": False, **halt}
    except ImportError:
        pass
    _seed_default_agents()
    agents = _load_agents()
    results = []
    for aid, a in agents.items():
        model = get_model(a.get("model_id") or aid)
        if not _policy(a, model).get("enabled", True):
            continue
        results.append(run_agent(aid, dry_run=dry_run))
    return {"success": True, "ran": len(results), "results": results}


def leaderboard_snapshot(period: str = "week", limit: int = 20) -> Dict[str, Any]:
    board = casino.get_leaderboard(period=period, limit=limit, currency="coins")
    agents = _load_agents()
    agent_users = {a.get("user_id") for a in agents.values()}
    agent_rows = [r for r in (board.get("leaderboard") or []) if r.get("user_id") in agent_users]
    return {
        "success": True,
        "period": period,
        "leaderboard": board.get("leaderboard") or [],
        "agent_leaderboard": agent_rows,
        "agent_count_on_board": len(agent_rows),
    }
