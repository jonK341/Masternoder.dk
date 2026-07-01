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
        _log_spectator_event(agent_id, user_id, model, plan, None, dry_run=True)
        return {"success": True, "agent_id": agent_id, "dry_run": True, "plan": plan, "used_ai": resolved.get("used_ai")}
    result = _execute_plan(user_id, plan)
    _log_spectator_event(agent_id, user_id, model, plan, result, dry_run=False)
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
    skipped: Dict[str, int] = {}
    for agent_id in agents:
        out = run_agent(agent_id, dry_run=dry_run)
        results.append(out)
        if out.get("success") and not dry_run:
            ran += 1
        elif not out.get("success"):
            reason = str(
                (out.get("result") or {}).get("error")
                or out.get("error")
                or "unknown"
            )
            skipped[reason] = skipped.get(reason, 0) + 1
    return {
        "success": True,
        "ran": ran,
        "agent_count": len(agents),
        "dry_run": dry_run,
        "skipped": skipped,
        "results": results,
    }


def ensure_agent_bankrolls(*, min_coins: float | None = None) -> Dict[str, Any]:
    """Top up autonomous agent wallets so they can place minimum bets."""
    target = float(min_coins if min_coins is not None else os.environ.get("CASINO_AGENT_MIN_COINS", "500"))
    agents = _load_json(_AGENTS_FILE)
    from backend.services.unified_points_database import unified_points_db

    topped = 0
    low = 0
    for aid, row in agents.items():
        if not isinstance(row, dict):
            continue
        pol = row.get("policy") if isinstance(row.get("policy"), dict) else {}
        if not pol.get("enabled", True):
            continue
        uid = str(row.get("user_id") or aid)
        need_min = float(pol.get("min_bet") or casino.get_public_config().get("min_bet") or 5)
        balance = float(casino._user_balance(uid, "coins"))
        floor = max(target, need_min * 10)
        if balance >= floor:
            continue
        low += 1
        delta = floor - balance
        if delta <= 0:
            continue
        unified_points_db.add_points(uid, "coins", delta, source="casino_agent_bankroll")
        topped += 1
    return {
        "success": True,
        "agent_count": len(agents),
        "min_coins": target,
        "low_balance_agents": low,
        "topped_up": topped,
    }


def _spectator_log_path() -> str:
    log_dir = casino._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_agent_spectator.jsonl")


def _log_spectator_event(
    agent_id: str,
    user_id: str,
    model: Dict[str, Any],
    plan: Dict[str, Any],
    result: Optional[Dict[str, Any]],
    *,
    dry_run: bool,
) -> None:
    line = {
        "ts": casino._iso() if hasattr(casino, "_iso") else None,
        "agent_id": agent_id,
        "agent_name": model.get("name") or agent_id,
        "user_id": user_id,
        "game": plan.get("game"),
        "bet": plan.get("bet"),
        "currency": plan.get("currency") or "coins",
        "spectator_line": plan.get("spectator_line") or plan.get("reasoning") or "",
        "dry_run": dry_run,
        "outcome": (result or {}).get("outcome") if isinstance(result, dict) else None,
        "net": (result or {}).get("net") if isinstance(result, dict) else None,
    }
    if not line["ts"]:
        from datetime import datetime, timezone
        line["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        with open(_spectator_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _agent_user_ids() -> List[str]:
    agents = _load_json(_AGENTS_FILE)
    ids: List[str] = []
    for row in agents.values():
        if isinstance(row, dict):
            uid = str(row.get("user_id") or "").strip()
            if uid:
                ids.append(uid)
    return ids


def get_spectator_feed(limit: int = 20) -> Dict[str, Any]:
    """Recent agent bets + spectator lines for the home/compete spectator panel."""
    limit = max(1, min(int(limit or 20), 50))
    events: List[Dict[str, Any]] = []
    path = _spectator_log_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            for raw in reversed(lines[-limit * 3:]):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    events.append(row)
                if len(events) >= limit:
                    break
        except OSError:
            pass

    if len(events) < limit:
        agent_ids = set(_agent_user_ids())
        ledger_path = casino._ledger_path()
        if os.path.isfile(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
                    ledger_lines = f.readlines()
                for raw in reversed(ledger_lines):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        row = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if row.get("user_id") not in agent_ids:
                        continue
                    events.append({
                        "ts": row.get("created_at"),
                        "agent_id": row.get("user_id"),
                        "agent_name": row.get("user_id"),
                        "user_id": row.get("user_id"),
                        "game": row.get("game"),
                        "bet": row.get("bet"),
                        "currency": row.get("currency"),
                        "spectator_line": "",
                        "dry_run": False,
                        "outcome": row.get("outcome"),
                        "net": row.get("net"),
                        "source": "ledger",
                    })
                    if len(events) >= limit:
                        break
            except OSError:
                pass

    models = _load_json(_MODELS_PATH).get("models") or _load_json(_MODELS_PATH)
    agents = _load_json(_AGENTS_FILE)
    for ev in events:
        aid = ev.get("agent_id")
        agent_row = agents.get(aid) if isinstance(agents, dict) else None
        if isinstance(agent_row, dict):
            mid = agent_row.get("model_id") or aid
            model = models.get(mid) if isinstance(models, dict) else {}
            if isinstance(model, dict) and model.get("name"):
                ev["agent_name"] = model["name"]
        if not ev.get("spectator_line"):
            game = ev.get("game") or "casino"
            bet = ev.get("bet")
            ev["spectator_line"] = f"Watching {ev.get('agent_name', aid)} on {game}" + (f" for {bet} coins" if bet else "")

    return {"success": True, "events": events[:limit], "count": min(len(events), limit)}
