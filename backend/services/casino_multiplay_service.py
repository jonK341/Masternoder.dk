"""Casino MultiPlay — 30+ social room games with crowd boosts and community pot."""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "casino_multiplay_games.json")
_ROOMS_PATH = os.path.join(_BASE, "logs", "casino_multiplay", "rooms.json")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _hour_seed(key: str) -> random.Random:
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    digest = hashlib.sha256(f"{hour}:{key}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _synthetic_population(game: Dict[str, Any]) -> int:
    rng = _hour_seed(game.get("id") or "x")
    lo = int(game.get("min_players") or 2)
    hi = int(game.get("max_players") or 20)
    base = rng.randint(lo, max(lo + 1, hi // 2))
    jitter = rng.randint(0, max(1, hi // 4))
    return min(hi, base + jitter)


def get_multiplay_catalog() -> Dict[str, Any]:
    cfg = _load_config()
    games_out: List[Dict[str, Any]] = []
    total_players = 0
    for g in cfg.get("games") or []:
        if not isinstance(g, dict):
            continue
        pop = _synthetic_population(g)
        total_players += pop
        games_out.append({**g, "players_online": pop, "room_open": True})
    pot = cfg.get("community_pot") if isinstance(cfg.get("community_pot"), dict) else {}
    seed = int(pot.get("seed_coins") or 5000)
    rng = _hour_seed("pot")
    pot_coins = seed + rng.randint(0, 2500)
    return {
        "success": True,
        "version": cfg.get("version"),
        "tab_label": cfg.get("tab_label") or "MultiPlay",
        "tagline": cfg.get("tagline"),
        "categories": cfg.get("categories") or [],
        "games": games_out,
        "stats": {
            "games_count": len(games_out),
            "players_online": total_players,
            "rooms_open": len(games_out),
            "community_pot_coins": pot_coins,
        },
        "room_boost": cfg.get("room_boost") or {},
        "community_pot": pot,
    }


def get_lobby(*, category: Optional[str] = None) -> Dict[str, Any]:
    cat = get_multiplay_catalog()
    games = cat.get("games") or []
    if category:
        games = [g for g in games if g.get("category") == category]
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for g in games:
        by_cat.setdefault(g.get("category") or "other", []).append(g)
    return {
        "success": True,
        "stats": cat.get("stats"),
        "by_category": by_cat,
        "games": games,
    }


def _game_row(game_id: str) -> Optional[Dict[str, Any]]:
    return next((g for g in (_load_config().get("games") or []) if g.get("id") == game_id), None)


def _room_boost_mult(players_online: int) -> float:
    cfg = _load_config().get("room_boost") or {}
    lo = float(cfg.get("min_mult") or 1.05)
    hi = float(cfg.get("max_mult") or 1.35)
    need = int(cfg.get("players_for_max") or 48)
    if players_online <= 0:
        return lo
    t = min(1.0, players_online / max(1, need))
    return round(lo + (hi - lo) * t, 4)


def _maybe_pot_bonus(user_id: str) -> int:
    pot = _load_config().get("community_pot") or {}
    if not pot.get("enabled"):
        return 0
    chance = float(pot.get("win_share_chance") or 0.04)
    cap = int(pot.get("max_share_coins") or 250)
    rng = _hour_seed(f"pot:{user_id}")
    if rng.random() > chance:
        return 0
    return rng.randint(10, cap)


def _play_social_table(
    user_id: str,
    bet: float,
    currency: str,
    *,
    variant: str,
) -> Dict[str, Any]:
    from backend.services import casino_rng, casino_service

    currency = casino_service._normalize_currency(currency)
    err = casino_service._validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = casino_service._parse_bet_amount(bet, currency) or 0
    proof = casino_rng.draw(user_id)
    dealer_proof = casino_rng.draw(f"{user_id}:dealer")
    pf = proof["float"]
    df = dealer_proof["float"]
    if variant == "social_baccarat":
        player_score = 2 + int(pf * 8)
        banker_score = 2 + int(df * 8)
        win = player_score > banker_score
        payout_mult = 1.95
    else:
        player_score = 12 + int(pf * 10)
        dealer_score = 17 + int(df * 5)
        win = player_score > dealer_score and player_score <= 21
        if player_score > 21:
            win = False
        payout_mult = 2.0
    payout = casino_service._round_payout(amount * payout_mult, currency) if win else 0.0
    outcome = "win" if win else "loss"
    return casino_service._finalize_bet(
        user_id,
        f"multiplay_{variant}",
        amount,
        outcome,
        payout,
        currency,
        details={"player_score": player_score, "dealer_score": dealer_score if variant != "social_baccarat" else banker_score},
    )


def _dispatch_engine(
    user_id: str,
    game: Dict[str, Any],
    bet: float,
    currency: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    from backend.services import casino_service

    engine = (game.get("engine") or "").strip()
    p = {**(game.get("engine_params") or {}), **(params or {})}
    if engine == "coin_flip":
        return casino_service.play_coin_flip(user_id, bet, p.get("choice") or "heads", currency=currency)
    if engine == "dice":
        return casino_service.play_dice(user_id, bet, int(p.get("guess") or 3), currency=currency)
    if engine == "rps_bet":
        return casino_service.play_rps_bet(user_id, bet, p.get("choice") or "rock", currency=currency)
    if engine == "wheel":
        return casino_service.play_wheel(user_id, bet, p.get("risk") or "medium", currency=currency)
    if engine == "scratch_card":
        return casino_service.play_scratch_card(user_id, bet, currency=currency)
    if engine == "mystery_coin_flip":
        return casino_service.play_mystery_coin_flip(user_id, bet, p.get("choice") or "heads", currency=currency)
    if engine == "battle_outcome":
        return casino_service.play_battle_outcome_bet(user_id, bet, p.get("prediction") or "win", p.get("difficulty"), currency)
    if engine == "rps_distribution":
        return casino_service.play_rps_distribution_bet(
            user_id, bet, p.get("prediction") or "rock", p.get("difficulty"), p.get("player_move"), currency,
        )
    if engine == "rps_counter_pick":
        return casino_service.play_rps_counter_pick(
            user_id, bet, p.get("choice") or "rock", p.get("difficulty"), p.get("player_move"), currency,
        )
    if engine == "crash":
        return casino_service.start_crash_round(user_id, bet, currency=currency, auto_cashout=p.get("auto_cashout"))
    if engine == "plinko":
        return casino_service.play_plinko(user_id, bet, p.get("risk") or "medium", currency=currency)
    if engine == "roulette":
        return casino_service.play_roulette(
            user_id, bet, p.get("bet_type") or "red", p.get("selection"), currency=currency,
        )
    if engine == "keno":
        picks = p.get("picks") or [1, 2, 3, 4]
        return casino_service.play_keno(user_id, bet, picks, currency=currency)
    if engine == "mines":
        return casino_service.start_mines_round(user_id, bet, currency=currency, mines=int(p.get("mines") or 5))
    if engine == "slot":
        return casino_service.play_slot(user_id, p.get("slot_id") or "slot_classic", bet, currency=currency)
    if engine == "social_blackjack":
        return _play_social_table(user_id, bet, currency, variant="social_blackjack")
    if engine == "social_baccarat":
        return _play_social_table(user_id, bet, currency, variant="social_baccarat")
    return {"success": False, "error": "engine_not_supported"}


def play_multiplay(
    user_id: str,
    game_id: str,
    bet: float,
    currency: str = "coins",
    **play_kwargs: Any,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    game = _game_row(game_id)
    if not game:
        return {"success": False, "error": "unknown_multiplay_game"}
    currency = (currency or "coins").strip().lower()
    bet_f = float(bet)
    lo, hi = float(game.get("min_bet") or 5), float(game.get("max_bet") or 500)
    if bet_f < lo or bet_f > hi:
        return {"success": False, "error": f"bet_out_of_range_{lo}_{hi}"}
    pop = _synthetic_population(game)
    boost = _room_boost_mult(pop)
    out = _dispatch_engine(uid, game, bet_f, currency, play_kwargs)
    if not out.get("success"):
        return out
    out["multiplay_game_id"] = game_id
    out["multiplay_tier"] = True
    out["players_in_room"] = pop
    out["room_boost_mult"] = boost
    net = float(out.get("net") or 0)
    if net > 0 and boost > 1.0:
        try:
            from backend.services import casino_service
            bonus = casino_service._round_payout(net * (boost - 1.0), currency)
            if bonus > 0:
                casino_service._apply_balance_delta(
                    uid, bonus, currency, f"multiplay_{game_id}",
                    {"phase": "room_boost", "mult": boost},
                )
                out["room_boost_bonus"] = bonus
                out["net"] = net + bonus
        except Exception:
            pass
    pot_bonus = _maybe_pot_bonus(uid) if float(out.get("net") or 0) > 0 else 0
    if pot_bonus > 0:
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(uid, "coins", pot_bonus, source="multiplay_community_pot", metadata={"game_id": game_id})
            out["community_pot_bonus"] = pot_bonus
        except Exception:
            pass
    try:
        from backend.services.casino_social_hub_service import push_casino_activity
        push_casino_activity(uid, "multiplay_bet", f"MultiPlay {game.get('title')} · {pop} online", {"game_id": game_id})
    except Exception:
        pass
    return out
