"""Blackjack bracket tournaments — single-elimination on existing BJ engine (Wave 4)."""
from __future__ import annotations

import json
import os
import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()


def _cs():
    from backend.services import casino_service
    return casino_service


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    cfg = _cs()._load_config()
    block = cfg.get("blackjack_tournaments") if isinstance(cfg.get("blackjack_tournaments"), dict) else {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "buy_in": float(block.get("buy_in") or 50),
        "house_seed": float(block.get("house_seed") or 1000),
        "bracket_size": int(block.get("bracket_size") or 8),
        "currency": (block.get("currency") or "coins").lower(),
    }


def _state_path() -> str:
    d = _cs()._log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_bj_tournaments.json")


def _load() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {"tournaments": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("tournaments", {})
            return data
    except Exception:
        pass
    return {"tournaments": {}}


def _save(data: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def _play_match(player_a: str, player_b: str, seed: str, match_id: str) -> Dict[str, Any]:
    """Simulate one-hand blackjack for each player; higher net wins."""
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    conf = _cs()._blackjack_config()
    proof_a = casino_rng.draw(f"{seed}|{match_id}|a")
    proof_b = casino_rng.draw(f"{seed}|{match_id}|b")

    def _hand_score(proof_float: float) -> float:
        deck = cards_engine.shuffle_deck(proof_float)
        player, deck = cards_engine.draw_cards(deck, 2)
        dealer, deck = cards_engine.draw_cards(deck, 2)
        if cards_engine.is_blackjack(player) and cards_engine.is_blackjack(dealer):
            return 1.0
        if cards_engine.is_blackjack(player):
            return 1.0 + conf["blackjack_payout"]
        if cards_engine.is_blackjack(dealer):
            return 0.0
        while cards_engine.dealer_should_hit(dealer, conf.get("hit_soft_17", True)) and deck:
            drawn, deck = cards_engine.draw_cards(deck, 1)
            dealer = list(dealer) + drawn
        outcome, mult = cards_engine.blackjack_outcome(
            player, dealer, blackjack_payout=conf["blackjack_payout"]
        )
        return float(mult)

    score_a = _hand_score(proof_a["float"])
    score_b = _hand_score(proof_b["float"])
    winner = None
    if score_a > score_b:
        winner = player_a
    elif score_b > score_a:
        winner = player_b
    return {
        "winner_id": winner,
        "player_a": {"user_id": player_a, "score": score_a},
        "player_b": {"user_id": player_b, "score": score_b},
        "push": winner is None,
    }


def _build_bracket(players: List[str]) -> List[List[Optional[str]]]:
    conf = _config()
    size = _next_power_of_two(max(len(players), conf["bracket_size"]))
    slots: List[Optional[str]] = list(players) + [None] * (size - len(players))
    rounds: List[List[Optional[str]]] = [slots[:size]]
    while len(rounds[-1]) > 1:
        rounds.append([None] * (len(rounds[-1]) // 2))
    return rounds


def _public(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tournament_id": t.get("tournament_id"),
        "status": t.get("status"),
        "currency": t.get("currency"),
        "buy_in": t.get("buy_in"),
        "pool": t.get("pool"),
        "entrants": list((t.get("entries") or {}).keys()),
        "entrant_count": len(t.get("entries") or {}),
        "bracket_size": t.get("bracket_size"),
        "current_round": t.get("current_round"),
        "rounds": t.get("rounds_public") or [],
        "winner_id": t.get("winner_id"),
        "created_at": t.get("created_at"),
    }


def get_or_create_open() -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "blackjack_tournaments_disabled"}
    with _LOCK:
        data = _load()
        for t in data["tournaments"].values():
            if isinstance(t, dict) and t.get("status") in ("open", "running"):
                return {"success": True, "tournament": _public(t)}
        tid = f"bj-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        t = {
            "tournament_id": tid,
            "status": "open",
            "currency": conf["currency"],
            "buy_in": conf["buy_in"],
            "house_seed": conf["house_seed"],
            "bracket_size": conf["bracket_size"],
            "pool": conf["house_seed"],
            "entries": {},
            "bracket": None,
            "rounds_public": [],
            "current_round": 0,
            "match_results": [],
            "fairness_seed": secrets.token_hex(16),
            "created_at": _iso(),
        }
        data["tournaments"][tid] = t
        _save(data)
    return {"success": True, "tournament": _public(t)}


def join(user_id: str, tournament_id: Optional[str] = None) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "blackjack_tournaments_disabled"}
    if not user_id or user_id == "default_user":
        return {"success": False, "error": "Create an account first", "code": "ACCOUNT_REQUIRED"}

    with _LOCK:
        data = _load()
        t = None
        if tournament_id:
            t = data["tournaments"].get(tournament_id)
        else:
            for cand in data["tournaments"].values():
                if isinstance(cand, dict) and cand.get("status") == "open":
                    t = cand
                    break
        if not isinstance(t, dict):
            return {"success": False, "error": "Tournament not found"}
        if t.get("status") != "open":
            return {"success": False, "error": "Tournament not open for entries"}
        if user_id in (t.get("entries") or {}):
            return {"success": False, "error": "Already joined", "code": "ALREADY_JOINED"}

        currency = _cs()._normalize_currency(t.get("currency"))
        buy_in = float(t.get("buy_in") or 0)
        if buy_in > 0:
            if _cs()._user_balance(user_id, currency) < buy_in:
                return {"success": False, "error": f"Insufficient {currency} for buy-in"}
            _cs()._apply_balance_delta(user_id, -buy_in, currency, "bj_tournament", {"phase": "buyin", "tournament_id": t.get("tournament_id")})
            t["pool"] = float(t.get("pool") or 0) + buy_in

        t.setdefault("entries", {})[user_id] = {"joined_at": _iso(), "buy_in_paid": buy_in}
        entries = list(t["entries"].keys())
        if len(entries) >= int(t.get("bracket_size") or conf["bracket_size"]):
            _start_bracket(t)
        data["tournaments"][t["tournament_id"]] = t
        _save(data)
    return {"success": True, "tournament": _public(t), "balance": _cs()._user_balance(user_id, currency)}


def _start_bracket(t: Dict[str, Any]) -> None:
    players = list((t.get("entries") or {}).keys())
    bracket = _build_bracket(players)
    t["bracket"] = bracket
    t["status"] = "running"
    t["current_round"] = 0
    _advance_round(t)


def _advance_round(t: Dict[str, Any]) -> None:
    bracket = t.get("bracket")
    if not isinstance(bracket, list) or not bracket:
        return
    rnd = int(t.get("current_round") or 0)
    if rnd >= len(bracket) - 1:
        return
    pairs = bracket[rnd]
    next_round: List[Optional[str]] = []
    round_public: List[Dict[str, Any]] = []
    seed = str(t.get("fairness_seed") or "")
    tid = str(t.get("tournament_id") or "")

    for i in range(0, len(pairs), 2):
        a = pairs[i]
        b = pairs[i + 1] if i + 1 < len(pairs) else None
        if a and not b:
            next_round.append(a)
            round_public.append({"slot": i // 2, "player_a": a, "player_b": None, "bye": True, "winner_id": a})
            continue
        if not a or not b:
            next_round.append(a or b)
            continue
        match_id = f"r{rnd}-m{i // 2}"
        result = _play_match(a, b, seed, match_id)
        winner = result.get("winner_id") or a
        next_round.append(winner)
        round_public.append({
            "slot": i // 2,
            "player_a": a,
            "player_b": b,
            "winner_id": winner,
            "push": result.get("push"),
            "score_a": result["player_a"]["score"],
            "score_b": result["player_b"]["score"],
        })
        t.setdefault("match_results", []).append({**result, "round": rnd, "match_id": match_id})

    if rnd + 1 < len(bracket):
        bracket[rnd + 1] = next_round
    t["rounds_public"] = (t.get("rounds_public") or []) + [{"round": rnd, "matches": round_public}]

    if len(next_round) == 1:
        winner = next_round[0]
        t["winner_id"] = winner
        t["status"] = "ended"
        t["ended_at"] = _iso()
        pool = float(t.get("pool") or 0)
        currency = _cs()._normalize_currency(t.get("currency"))
        if winner and pool > 0:
            _cs()._apply_balance_delta(winner, pool, currency, "bj_tournament", {"phase": "prize", "tournament_id": tid})
    else:
        t["current_round"] = rnd + 1
        _advance_round(t)


def list_tournaments() -> Dict[str, Any]:
    data = _load()
    rows = [_public(t) for t in data["tournaments"].values() if isinstance(t, dict)]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"success": True, "tournaments": rows[:10]}


def get_tournament(tournament_id: str) -> Dict[str, Any]:
    data = _load()
    t = data["tournaments"].get(tournament_id)
    if not isinstance(t, dict):
        return {"success": False, "error": "Tournament not found"}
    return {"success": True, "tournament": _public(t)}
