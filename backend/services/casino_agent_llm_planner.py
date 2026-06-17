"""LLM-driven bet planning for casino agent personas — context, persona prompts, validation."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import backend.services.casino_service as casino

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BRAIN_LOG = os.path.join(_BASE, "logs", "casino_agent_brain.jsonl")

_VALID_GAMES = frozenset({
    "dice", "coin_flip", "slot_classic", "slot_diamond", "plinko", "wheel", "crash", "rps_bet",
})
_RISK_LEVELS = frozenset({"low", "medium", "high"})
_RPS = frozenset({"rock", "paper", "scissors"})
_COIN = frozenset({"heads", "tails"})

_PERSONA_PROMPTS: Dict[str, str] = {
    "kelly_flat": (
        "You are Kelly Optimizer — a disciplined bankroll mathematician. "
        "Size bets as a small fraction of balance. Prefer dice and coin_flip. "
        "Never bet more than 8% of balance. Explain tradeoffs briefly."
    ),
    "martingale_conservative": (
        "You are Martingale Conservative — cautious loss recovery on even-money games only. "
        "After losses, increase bet modestly (max 2x base) but never chase beyond 3 steps. "
        "Prefer coin_flip and rps_bet. Stop recovery if balance is fragile."
    ),
    "slot_hunter": (
        "You are Slot Hunter — a variance seeker hunting jackpot symbols and big slot hits. "
        "Accept higher variance; pick slot_classic or slot_diamond. Bet slightly bolder when rank is low."
    ),
    "tournament_grinder": (
        "You are Tournament Grinder — maximize tournament net score, not single-hand glory. "
        "Steady medium bets on dice/coin_flip during active tournaments. Consistency beats swings."
    ),
    "crash_timer": (
        "You are Crash Timer — a crash specialist with strict auto-cashout discipline. "
        "Always play crash with auto_cashout between 1.3 and 2.5. Lower cashout when balance is low."
    ),
    "leaderboard_chaser": (
        "You are Leaderboard Chaser — read rank gaps and bet to climb the weekly board. "
        "Behind rank 10: press slightly. Top 3: protect bankroll with smaller bets. "
        "Mix dice, plinko, wheel for variety."
    ),
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_brain(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_BRAIN_LOG), exist_ok=True)
        with open(_BRAIN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception:
        pass


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _recent_bets(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        rows = casino.get_history(user_id, limit=limit).get("history") or []
        out = []
        for r in rows[:limit]:
            out.append({
                "game": r.get("game"),
                "bet": r.get("bet"),
                "net": r.get("net"),
                "outcome": r.get("outcome"),
            })
        return out
    except Exception:
        return []


def _rank_context(user_id: str, period: str) -> Dict[str, Any]:
    try:
        board = casino.get_leaderboard(period=period, limit=15, currency="coins")
        rows = board.get("leaderboard") or []
        mine = next((r for r in rows if r.get("user_id") == user_id), None)
        top = [{"rank": r.get("rank"), "net": r.get("net"), "user_id": r.get("user_id")} for r in rows[:5]]
        return {
            "period": period,
            "my_rank": mine.get("rank") if mine else None,
            "my_net": mine.get("net") if mine else 0,
            "my_bets": mine.get("bets") if mine else 0,
            "top5": top,
            "players_on_board": len(rows),
        }
    except Exception:
        return {"period": period, "my_rank": None, "top5": []}


def build_context(
    *,
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    heuristic_plan: Dict[str, Any],
) -> Dict[str, Any]:
    currency = policy.get("currency") or "coins"
    bal = casino._user_balance(user_id, currency)
    return {
        "agent_id": agent_id,
        "persona": model.get("name"),
        "specialization": model.get("specialization"),
        "strategy": model.get("strategy"),
        "skills": model.get("skills") or [],
        "balance": bal,
        "currency": currency,
        "min_bet": policy.get("min_bet"),
        "max_bet": policy.get("max_bet"),
        "allowed_games": policy.get("allowed_games") or [],
        "leaderboard": _rank_context(user_id, policy.get("leaderboard_period") or "week"),
        "recent_bets": _recent_bets(user_id),
        "last_outcome": agent.get("last_outcome"),
        "last_game": agent.get("last_game"),
        "last_net": agent.get("last_net"),
        "martingale_step": agent.get("martingale_step"),
        "heuristic_suggestion": heuristic_plan,
        "bets_today": casino.get_balance(user_id).get("bets_today"),
    }


def _system_prompt(model: Dict[str, Any]) -> str:
    strategy = model.get("strategy") or "kelly_flat"
    persona = _PERSONA_PROMPTS.get(strategy, _PERSONA_PROMPTS["kelly_flat"])
    return (
        f"{persona}\n\n"
        "You play virtual COINS only (practice rail). Respond with STRICT JSON only — no markdown.\n"
        "Schema:\n"
        "{\n"
        '  "game": "dice|coin_flip|slot_classic|slot_diamond|plinko|wheel|crash|rps_bet",\n'
        '  "bet": <integer coins>,\n'
        '  "confidence": <0.0-1.0>,\n'
        '  "reasoning": "<one or two sentences>",\n'
        '  "spectator_line": "<witty 8-15 word arena comment for fans>",\n'
        '  "params": {\n'
        '    "guess": <1-6 for dice>,\n'
        '    "choice": "heads|tails" for coin_flip,\n'
        '    "pick": "rock|paper|scissors" for rps_bet,\n'
        '    "risk": "low|medium|high" for plinko/wheel,\n'
        '    "auto_cashout": <1.2-3.0 for crash>\n'
        "  }\n"
        "}\n"
        "Omit unused params keys. Bet MUST be within min_bet and max_bet from context."
    )


def _clamp_bet(bet: Any, policy: Dict[str, Any]) -> float:
    try:
        val = float(bet)
    except (TypeError, ValueError):
        val = float(policy.get("min_bet") or 5)
    mn = float(policy.get("min_bet") or 5)
    mx = float(policy.get("max_bet") or 200)
    val = max(mn, min(mx, val))
    return float(int(val))


def _validate_plan(raw: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    allowed = set(policy.get("allowed_games") or _VALID_GAMES)
    game = str(raw.get("game") or "dice").strip().lower()
    if game not in _VALID_GAMES:
        game = "dice"
    if game not in allowed:
        game = next(iter(allowed), "dice")

    bet = _clamp_bet(raw.get("bet"), policy)
    params = raw.get("params") if isinstance(raw.get("params"), dict) else {}

    if game == "dice":
        sides = int((casino.get_public_config().get("games") or {}).get("dice", {}).get("sides") or 6)
        try:
            guess = int(params.get("guess", 1))
        except (TypeError, ValueError):
            guess = 1
        params["guess"] = max(1, min(sides, guess))
    elif game == "coin_flip":
        c = str(params.get("choice") or "heads").lower()
        params["choice"] = c if c in _COIN else "heads"
    elif game == "rps_bet":
        p = str(params.get("pick") or params.get("choice") or "rock").lower()
        params["pick"] = p if p in _RPS else "rock"
    elif game in ("plinko", "wheel"):
        r = str(params.get("risk") or "medium").lower()
        params["risk"] = r if r in _RISK_LEVELS else "medium"
    elif game == "crash":
        try:
            ac = float(params.get("auto_cashout") or 1.5)
        except (TypeError, ValueError):
            ac = 1.5
        params["auto_cashout"] = round(max(1.2, min(3.0, ac)), 2)

    conf = raw.get("confidence")
    try:
        confidence = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "game": game,
        "bet": bet,
        "currency": policy.get("currency") or "coins",
        "confidence": confidence,
        "reasoning": str(raw.get("reasoning") or "")[:500],
        "spectator_line": str(raw.get("spectator_line") or "")[:120],
        "params": params,
    }


def llm_enabled() -> bool:
    if os.environ.get("CASINO_AGENT_LLM", "1") == "0":
        return False
    try:
        from backend.services import llm_service
        return llm_service.is_available()
    except Exception:
        return False


def plan_bet(
    *,
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    agent: Dict[str, Any],
    policy: Dict[str, Any],
    heuristic_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ask the routed LLM for a bet plan. Returns validated plan or error dict.
    """
    if not llm_enabled():
        return {"success": False, "used_ai": False, "reason": "llm_disabled_or_unavailable"}

    ctx = build_context(
        agent_id=agent_id,
        user_id=user_id,
        model=model,
        agent=agent,
        policy=policy,
        heuristic_plan=heuristic_plan,
    )

    task_kind = model.get("task_kind") or "casino_bet_plan"
    task_type = model.get("llm_task_type") or "reason"
    user_prompt = (
        f"Plan ONE casino bet for leaderboard climb.\n"
        f"Context JSON:\n{json.dumps(ctx, default=str)}\n"
        "Output strict JSON only."
    )

    try:
        from backend.services.agent_ai_router import routed_chat
        resp, routing = routed_chat(
            [
                {"role": "system", "content": _system_prompt(model)},
                {"role": "user", "content": user_prompt},
            ],
            task_kind,
            user_id,
            temperature=0.35,
            max_tokens=350,
            timeout=int(os.environ.get("CASINO_AGENT_LLM_TIMEOUT", "12")),
        )
    except Exception as exc:
        return {"success": False, "used_ai": True, "reason": "llm_call_failed", "error": str(exc)[:200]}

    if not resp.success:
        return {
            "success": False,
            "used_ai": True,
            "reason": "llm_error",
            "error": resp.error,
            "routing": routing,
        }

    parsed = _extract_json(resp.content or "")
    if not parsed:
        return {
            "success": False,
            "used_ai": True,
            "reason": "invalid_json",
            "raw": (resp.content or "")[:400],
            "routing": routing,
        }

    plan = _validate_plan(parsed, policy)
    brain = {
        "ts": _iso(),
        "agent_id": agent_id,
        "user_id": user_id,
        "provider": resp.provider,
        "model": resp.model,
        "task_kind": task_kind,
        "trace_id": routing.get("trace_id"),
        "plan": plan,
        "context_rank": ctx.get("leaderboard", {}).get("my_rank"),
    }
    _append_brain(brain)

    return {
        "success": True,
        "used_ai": True,
        "source": "llm",
        "plan": plan,
        "routing": routing,
        "provider": resp.provider,
        "brain": brain,
    }


def recent_brain(agent_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    if not os.path.isfile(_BRAIN_LOG):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_BRAIN_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if agent_id and row.get("agent_id") != agent_id:
                        continue
                    rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))
