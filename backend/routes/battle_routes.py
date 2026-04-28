"""
Battle Routes - Stub implementations for Battle and Trophies pages
Extracted from battle.py.backup; uses stub logic until battle_system services exist.
All endpoints resolve user_id via session > query/body > identification.
"""
from flask import Blueprint, jsonify, request
import uuid
import os
import json
from datetime import datetime, timedelta, timezone
import random

battle_bp = Blueprint('battle', __name__)

_MINIMAL_CONTENT_CACHE = None
_BATTLE_V2_STATE_FILE = "battle_v2_state.json"


def _data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def _load_battle_minimal_content() -> dict:
    global _MINIMAL_CONTENT_CACHE
    if _MINIMAL_CONTENT_CACHE is not None:
        return _MINIMAL_CONTENT_CACHE
    path = os.path.join(_data_dir(), "battle_minimal_content.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _MINIMAL_CONTENT_CACHE = json.load(f)
    except Exception:
        _MINIMAL_CONTENT_CACHE = {}
    return _MINIMAL_CONTENT_CACHE


def _battle_v2_state_path() -> str:
    return os.path.join(_data_dir(), _BATTLE_V2_STATE_FILE)


def _load_battle_v2_state() -> dict:
    path = _battle_v2_state_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("users", {})
                return data
        except Exception:
            pass
    return {"users": {}}


def _save_battle_v2_state(data: dict) -> None:
    os.makedirs(os.path.dirname(_battle_v2_state_path()), exist_ok=True)
    tmp = _battle_v2_state_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _battle_v2_state_path())


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_iso_utc(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _seconds_until(iso_value):
    dt = _parse_iso_utc(iso_value)
    if not dt:
        return 0
    return max(0, int((dt - _utc_now()).total_seconds()))


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')


def _tournament_api_dict(raw: dict) -> dict:
    """Frontend expects tournament_id, type, max_participants, entry_fee, prize_pool."""
    tid = raw.get("id") or ""
    return {
        "id": tid,
        "tournament_id": tid,
        "name": raw.get("name", ""),
        "status": raw.get("status", "open"),
        "type": raw.get("type", "Single Elimination"),
        "max_participants": int(raw.get("max_participants") or 16),
        "entry_fee": int(raw.get("entry_fee") or 0),
        "prize_pool": raw.get("prize_pool") or {},
        "participants": list(raw.get("participants") or []),
    }


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamped_limit(raw_value, default=20, max_value=100):
    value = _to_int(raw_value, default=default)
    if value < 1:
        return default
    return min(value, max_value)


def _safe_skill_profiles(raw_profiles, max_count=15):
    if not isinstance(raw_profiles, list):
        return []
    safe_profiles = []
    for profile in raw_profiles:
        if isinstance(profile, dict):
            safe_profiles.append(profile)
        if len(safe_profiles) >= max_count:
            break
    return safe_profiles


def _get_battle_stats(user_id: str) -> dict:
    """Get battle stats from unified points or return defaults."""
    stats = {
        'battle_points': 0,
        'wins': 0,
        'losses': 0,
        'total_battles': 0,
        'win_streak': 0,
        'rank': 0,
        'accuracy': 0,
        'win_rate': 0.0,
        'power': 0,
        'level': 1,
    }
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            points = unified_points_db.get_all_points(user_id)
            systems = (points or {}).get('systems', (points or {}).get('points', {}).get('systems', {})) or {}
            wins = int(systems.get('battle_wins', systems.get('wins', 0)) or 0)
            losses = int(systems.get('battle_losses', systems.get('losses', 0)) or 0)
            draws = int(systems.get('battle_draws', 0) or 0)
            total = wins + losses + draws
            stats.update({
                'battle_points': int(systems.get('battle_points', 0) or 0),
                'wins': wins,
                'losses': losses,
                'total_battles': total,
                'win_streak': int(systems.get('battle_streak', 0) or 0),
                'win_rate': round((wins / total * 100), 1) if total > 0 else 0.0,
            })
    except Exception:
        pass
    return stats


_RPS_BEATS = {'rock': 'scissors', 'scissors': 'paper', 'paper': 'rock'}
_RPS_MOVES = frozenset(_RPS_BEATS.keys())


def _rps_outcome(player_move: str, ai_move: str) -> str:
    if player_move == ai_move:
        return 'draw'
    if _RPS_BEATS[player_move] == ai_move:
        return 'win'
    return 'loss'


def _pick_ai_rps_move(player_move: str, difficulty: str) -> str:
    moves = ('rock', 'paper', 'scissors')
    if difficulty == 'hard' and random.random() < 0.42:
        for m in moves:
            if _RPS_BEATS[m] == player_move:
                return m
    if difficulty == 'easy' and random.random() < 0.38:
        return _RPS_BEATS[player_move]
    return random.choice(moves)


def _weighted_random_result(difficulty: str) -> str:
    """Quick skirmish when client sends no stance (legacy / one-click battle)."""
    r = random.random()
    if difficulty == 'easy':
        if r < 0.48:
            return 'win'
        if r < 0.78:
            return 'draw'
        return 'loss'
    if difficulty == 'hard':
        if r < 0.28:
            return 'win'
        if r < 0.48:
            return 'draw'
        return 'loss'
    if r < 0.36:
        return 'win'
    if r < 0.62:
        return 'draw'
    return 'loss'


def _hunter_xp_for_quick_battle(result: str, difficulty: str, used_rps: bool) -> int:
    base = {'win': 42, 'draw': 14, 'loss': 6}
    b = base.get(result, 0)
    mult = {'easy': 0.92, 'balanced': 1.0, 'hard': 1.12}.get(difficulty, 1.0)
    if used_rps and result == 'win':
        mult *= 1.06
    cap = 65
    return max(0, min(int(b * mult), cap))


def _current_battle_season_id() -> str:
    now = _utc_now()
    return f"season_{now.year}_{now.month:02d}"


def _default_battle_resources() -> dict:
    mc = _load_battle_minimal_content()
    tmpl = dict(mc.get('fantasy_resources_template') or {'energy': 100, 'shards': 3, 'boost_tokens': 1})
    return {
        "energy": float(tmpl.get("energy", 100) or 0),
        "shards": float(tmpl.get("shards", 0) or 0),
        "boost_tokens": float(tmpl.get("boost_tokens", 0) or 0),
    }


def _battle_v2_user_state(data: dict, user_id: str) -> dict:
    users = data.setdefault("users", {})
    user_state = users.setdefault(user_id, {})
    user_state.setdefault("resource_ledger", [])
    user_state.setdefault("season_progress", {})
    user_state.setdefault("telemetry", [])
    user_state.setdefault("crypto", {"total_mn2_earned": 0, "claims": [], "options": {}})
    return user_state


def _resource_balances(user_state: dict) -> dict:
    balances = _default_battle_resources()
    for row in user_state.get("resource_ledger", []):
        if not isinstance(row, dict):
            continue
        for key, amount in (row.get("delta") or {}).items():
            if key not in balances:
                continue
            try:
                balances[key] += float(amount or 0)
            except (TypeError, ValueError):
                continue
    return {k: round(max(0.0, v), 4) for k, v in balances.items()}


def _battle_reward_resources(result: str, difficulty: str, used_rps: bool) -> dict:
    shard = {'win': 2, 'draw': 1, 'loss': 0}.get(result, 0)
    energy = {'win': 4, 'draw': 2, 'loss': 1}.get(result, 0)
    if difficulty == 'hard' and result == 'win':
        shard += 1
    if used_rps and result == 'win':
        energy += 1
    return {"energy": energy, "shards": shard}


def _record_battle_v2_event(user_id: str, battle_id: str, result: str, points_delta: int, difficulty: str,
                            opponent_type: str, player_move: str = None, opponent_move: str = None) -> None:
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    now_iso = _utc_now().isoformat()
    used_rps = bool(player_move and opponent_move)

    resource_delta = _battle_reward_resources(result, difficulty, used_rps)
    user_state["resource_ledger"].append({
        "type": "quick_battle_reward",
        "battle_id": battle_id,
        "delta": resource_delta,
        "result": result,
        "created_at": now_iso,
    })
    user_state["resource_ledger"] = user_state["resource_ledger"][-200:]

    sid = _current_battle_season_id()
    season = user_state["season_progress"].setdefault(sid, {
        "season_id": sid,
        "score": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "matches": 0,
        "points_delta": 0,
        "started_at": now_iso,
    })
    season["matches"] = int(season.get("matches", 0) or 0) + 1
    season["points_delta"] = int(season.get("points_delta", 0) or 0) + int(points_delta or 0)
    season["score"] = int(season.get("score", 0) or 0) + max(0, int(points_delta or 0)) + {'win': 7, 'draw': 2, 'loss': 1}.get(result, 0)
    if result == "win":
        season["wins"] = int(season.get("wins", 0) or 0) + 1
    elif result == "loss":
        season["losses"] = int(season.get("losses", 0) or 0) + 1
    else:
        season["draws"] = int(season.get("draws", 0) or 0) + 1
    season["updated_at"] = now_iso

    telemetry = {
        "battle_id": battle_id,
        "season_id": sid,
        "result": result,
        "points_delta": points_delta,
        "difficulty": difficulty,
        "opponent_type": opponent_type,
        "battle_mode": "rps" if used_rps else "skirmish",
        "player_move": player_move,
        "opponent_move": opponent_move,
        "resource_delta": resource_delta,
        "created_at": now_iso,
    }
    user_state["telemetry"].append(telemetry)
    user_state["telemetry"] = user_state["telemetry"][-200:]
    user_state["updated_at"] = now_iso
    _save_battle_v2_state(data)


def _battle_resources_status(user_id: str) -> dict:
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    ledger = list(user_state.get("resource_ledger", []))
    return {
        "balances": _resource_balances(user_state),
        "ledger": ledger[-30:],
        "ledger_count": len(ledger),
        "implementation_status": "user_ledger",
    }


def _battle_season_status(user_id: str) -> dict:
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    sid = _current_battle_season_id()
    seasons = user_state.get("season_progress", {})
    current = seasons.get(sid) or {
        "season_id": sid,
        "score": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "matches": 0,
        "points_delta": 0,
    }
    return {
        "current_season_id": sid,
        "current": current,
        "seasons": seasons,
        "implementation_status": "dedicated_user_season_progress",
    }


def _battle_telemetry_status(user_id: str, limit: int = 20) -> dict:
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    rows = list(user_state.get("telemetry", []))
    wins = sum(1 for r in rows if r.get("result") == "win")
    rps = sum(1 for r in rows if r.get("battle_mode") == "rps")
    return {
        "events": rows[-limit:],
        "event_count": len(rows),
        "summary": {
            "wins": wins,
            "rps_openers": rps,
            "tracked_matches": len(rows),
        },
        "implementation_status": "per_match_telemetry",
    }


def _battle_crypto_options():
    return [
        {
            "id": "duel_hash",
            "name": "Duel Hash",
            "description": "Claim a small MN2 reward after proving Battle activity.",
            "cooldown_sec": 30 * 60,
            "base_mn2": 0.002,
            "requires": {"matches": 1},
        },
        {
            "id": "streak_miner",
            "name": "Streak Miner",
            "description": "Convert win streak pressure into an in-app MN2 balance reward.",
            "cooldown_sec": 3 * 60 * 60,
            "base_mn2": 0.004,
            "requires": {"win_streak": 2},
        },
        {
            "id": "season_relay",
            "name": "Season Relay",
            "description": "Earn from dedicated season progress and battle score.",
            "cooldown_sec": 6 * 60 * 60,
            "base_mn2": 0.007,
            "requires": {"season_score": 25},
        },
        {
            "id": "clan_node",
            "name": "Clan Node",
            "description": "Reward social battle setup when your user id owns a clan membership.",
            "cooldown_sec": 12 * 60 * 60,
            "base_mn2": 0.01,
            "requires": {"clans": 1},
        },
    ]


def _battle_crypto_progress(user_id: str) -> dict:
    stats = _get_battle_stats(user_id)
    season = _battle_season_status(user_id).get("current") or {}
    social = _battle_social_progress(user_id)
    resources = _battle_resources_status(user_id).get("balances") or {}
    return {
        "matches": int(stats.get("total_battles", 0) or 0),
        "wins": int(stats.get("wins", 0) or 0),
        "win_streak": int(stats.get("win_streak", 0) or 0),
        "battle_points": int(stats.get("battle_points", 0) or 0),
        "season_score": int(season.get("score", 0) or 0),
        "clans": len(social.get("joined_clans") or []),
        "tournaments": len(social.get("joined_tournaments") or []),
        "shards": float(resources.get("shards", 0) or 0),
    }


def _crypto_requirement_met(option, progress):
    for key, needed in (option.get("requires") or {}).items():
        if float(progress.get(key, 0) or 0) < float(needed or 0):
            return False
    return True


def _battle_crypto_reward_amount(option, progress):
    amount = float(option.get("base_mn2", 0) or 0)
    if option["id"] == "duel_hash":
        amount += min(float(progress.get("matches", 0) or 0), 100) * 0.00008
    elif option["id"] == "streak_miner":
        amount += min(float(progress.get("win_streak", 0) or 0), 20) * 0.00035
    elif option["id"] == "season_relay":
        amount += min(float(progress.get("season_score", 0) or 0), 500) * 0.00001
    elif option["id"] == "clan_node":
        amount += min(float(progress.get("shards", 0) or 0), 100) * 0.00003
    return round(amount, 8)


def _battle_crypto_status(user_id: str) -> dict:
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    crypto = user_state.setdefault("crypto", {"total_mn2_earned": 0, "claims": [], "options": {}})
    progress = _battle_crypto_progress(user_id)
    options = []
    for option in _battle_crypto_options():
        option_state = crypto.setdefault("options", {}).setdefault(option["id"], {})
        remaining = _seconds_until(option_state.get("next_claim_at"))
        unlocked = _crypto_requirement_met(option, progress)
        options.append({
            **option,
            "reward_mn2": _battle_crypto_reward_amount(option, progress),
            "unlocked": unlocked,
            "ready": unlocked and remaining <= 0,
            "cooldown_remaining_sec": remaining,
            "last_claim_at": option_state.get("last_claim_at"),
            "next_claim_at": option_state.get("next_claim_at"),
            "claims_count": int(option_state.get("claims_count", 0) or 0),
        })
    points = {}
    try:
        from backend.services.unified_points_database import unified_points_db
        res = unified_points_db.get_all_points(user_id) if unified_points_db else {}
        points = res.get("points", {}) if isinstance(res, dict) else {}
    except Exception:
        points = {}
    return {
        "user_id": user_id,
        "currency": "MN2",
        "progress": progress,
        "options": options,
        "total_mn2_earned": round(float(crypto.get("total_mn2_earned", 0) or 0), 8),
        "mn2_balance": float(points.get("mn2_balance", 0) or 0),
        "claims": list(crypto.get("claims", []))[-20:],
        "implementation_status": "internal_mn2_balance_claims",
    }


def _claim_battle_crypto(user_id: str, option_id: str):
    data = _load_battle_v2_state()
    user_state = _battle_v2_user_state(data, user_id)
    crypto = user_state.setdefault("crypto", {"total_mn2_earned": 0, "claims": [], "options": {}})
    option = next((o for o in _battle_crypto_options() if o["id"] == option_id), None)
    if not option:
        return {"success": False, "error": "Unknown crypto option"}, 404
    progress = _battle_crypto_progress(user_id)
    if not _crypto_requirement_met(option, progress):
        return {"success": False, "error": "Crypto option is locked", "progress": progress, "requires": option.get("requires", {})}, 400
    option_state = crypto.setdefault("options", {}).setdefault(option_id, {})
    remaining = _seconds_until(option_state.get("next_claim_at"))
    if remaining > 0:
        return {"success": False, "error": "cooldown", "cooldown_remaining_sec": remaining}, 429
    now = _utc_now()
    amount = _battle_crypto_reward_amount(option, progress)
    next_claim_at = (now + timedelta(seconds=int(option.get("cooldown_sec", 0) or 0))).isoformat()
    try:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            user_id, "mn2_balance", amount,
            source="battle_crypto_claim",
            metadata={"option_id": option_id, "option_name": option.get("name"), "progress": progress},
        )
    except Exception as e:
        return {"success": False, "error": "MN2 award failed: " + str(e)}, 500

    claim = {
        "option_id": option_id,
        "option_name": option.get("name"),
        "amount_mn2": amount,
        "claimed_at": now.isoformat(),
        "next_claim_at": next_claim_at,
        "progress": progress,
    }
    option_state["last_claim_at"] = claim["claimed_at"]
    option_state["next_claim_at"] = next_claim_at
    option_state["claims_count"] = int(option_state.get("claims_count", 0) or 0) + 1
    crypto["total_mn2_earned"] = round(float(crypto.get("total_mn2_earned", 0) or 0) + amount, 8)
    crypto.setdefault("claims", []).append(claim)
    user_state["updated_at"] = now.isoformat()
    _save_battle_v2_state(data)
    try:
        from backend.routes.social_routes import push_activity
        push_activity(user_id, "battle_crypto_claim", f"Claimed {amount:.8f} MN2 from {option.get('name')}", {"option_id": option_id})
    except Exception:
        pass
    return {"success": True, "claim": claim, "crypto": _battle_crypto_status(user_id)}, 200


@battle_bp.route('/api/battle/stats', methods=['GET'])
def battle_stats():
    """Get battle stats"""
    try:
        user_id = _resolve_uid()
        stats = _get_battle_stats(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/history', methods=['GET'])
def battle_history():
    """Get battle history (from DB when migration run)."""
    try:
        user_id = _resolve_uid()
        limit = _clamped_limit(request.args.get('limit', 20), default=20, max_value=100)
        history = []
        try:
            from backend.services.battle_db_service import get_battle_history
            history = get_battle_history(user_id, limit=limit) or []
        except Exception:
            pass
        return jsonify({
            'success': True,
            'user_id': user_id,
            'history': history,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/quick', methods=['POST'])
def battle_quick():
    """Quick battle vs AI or PvP queue stub. Optional player_move (rock|paper|scissors) for an RPS opening duel (both modes)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_uid()
        difficulty = (data.get('difficulty') or 'balanced').strip().lower()
        opponent_type = (data.get('opponent_type') or 'ai').strip().lower()
        if difficulty not in {'easy', 'balanced', 'hard'}:
            difficulty = 'balanced'
        if opponent_type not in {'ai', 'player'}:
            opponent_type = 'ai'

        raw_move = data.get('player_move') or data.get('stance')
        player_move = None
        if isinstance(raw_move, str):
            pm = raw_move.strip().lower()
            if pm in _RPS_MOVES:
                player_move = pm

        use_rps = bool(player_move) and opponent_type in ('ai', 'player')
        ai_move = None
        if use_rps:
            ai_move = _pick_ai_rps_move(player_move, difficulty)
            result = _rps_outcome(player_move, ai_move)
        elif opponent_type == 'ai':
            result = _weighted_random_result(difficulty)
        else:
            result = _weighted_random_result(difficulty)

        battle_id = str(uuid.uuid4())[:8]
        points_delta = {'win': 10, 'loss': -3, 'draw': 2}.get(result, 0)
        try:
            from backend.services.battle_db_service import record_battle
            record_battle(user_id=user_id, battle_id=battle_id, opponent_type=opponent_type,
                          difficulty=difficulty, result=result, points_delta=points_delta)
        except Exception:
            pass

        # Update unified points so profile, dashboard, and battle page show correct counts
        try:
            from backend.services.unified_points_database import unified_points_db
            meta = {
                "battle_id": battle_id,
                "difficulty": difficulty,
                "opponent_type": opponent_type,
                "battle_mode": (
                    "rps_pvp" if use_rps and opponent_type == "player" else ("rps" if use_rps else "skirmish")
                ),
            }
            if player_move:
                meta["player_move"] = player_move
            if ai_move:
                meta["opponent_move"] = ai_move
                if opponent_type == "ai":
                    meta["ai_move"] = ai_move
            unified_points_db.add_points(user_id, "battle_points", float(points_delta), "quick_battle", meta)
            if result == "win":
                unified_points_db.add_points(user_id, "battle_wins", 1, "quick_battle", meta)
                unified_points_db.add_points(user_id, "battle_streak", 1, "quick_battle", meta)
            elif result == "loss":
                unified_points_db.add_points(user_id, "battle_losses", 1, "quick_battle", meta)
                all_pts = unified_points_db.get_all_points(user_id)
                systems = (all_pts or {}).get("points", {}).get("systems", {}) or {}
                current_streak = int(systems.get("battle_streak", 0) or 0)
                if current_streak > 0:
                    unified_points_db.add_points(user_id, "battle_streak", -current_streak, "quick_battle", meta)
            else:
                unified_points_db.add_points(user_id, "battle_draws", 1, "quick_battle", meta)
                all_pts = unified_points_db.get_all_points(user_id)
                systems = (all_pts or {}).get("points", {}).get("systems", {}) or {}
                current_streak = int(systems.get("battle_streak", 0) or 0)
                if current_streak > 0:
                    unified_points_db.add_points(user_id, "battle_streak", -current_streak, "quick_battle", meta)
        except Exception:
            pass

        try:
            _record_battle_v2_event(
                user_id=user_id,
                battle_id=battle_id,
                result=result,
                points_delta=points_delta,
                difficulty=difficulty,
                opponent_type=opponent_type,
                player_move=player_move,
                opponent_move=ai_move,
            )
        except Exception:
            pass

        hunter_xp_info = None
        try:
            from backend.routes.hunters_game import award_xp
            xp_amt = _hunter_xp_for_quick_battle(result, difficulty, use_rps)
            if xp_amt > 0:
                xp_res = award_xp(
                    user_id,
                    {'xp': xp_amt},
                    xp_source='quick_battle',
                    xp_action_type=f'battle_{result}',
                )
                if xp_res.get('success'):
                    hunter_xp_info = {
                        'xp_awarded': xp_res.get('xp_awarded'),
                        'level': xp_res.get('level'),
                        'leveled_up': xp_res.get('leveled_up'),
                        'total_xp': xp_res.get('total_xp'),
                    }
        except Exception:
            pass

        try:
            from backend.services.ai_user_controller import on_user_activity
            on_user_activity(user_id, "battle_completed", {"result": result, "points_delta": points_delta})
        except Exception:
            pass
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('battle')
        except Exception:
            pass

        # AI post-battle commentary (DeepSeek R1 via reason routing)
        commentary = None
        strategy_tip = None
        try:
            from backend.services.llm_service import complete as llm_complete
            result_word = {'win': 'victory', 'loss': 'defeat', 'draw': 'draw'}.get(result, result)
            rps_ctx = ""
            if use_rps and player_move and ai_move:
                if opponent_type == "player":
                    rps_ctx = (
                        " PvP opening duel (rock-paper-scissors): player chose %s, opponent chose %s."
                        % (player_move, ai_move)
                    )
                else:
                    rps_ctx = " They played rock-paper-scissors: player chose %s, AI chose %s." % (player_move, ai_move)
            opp_label = "a human opponent (matchmaking)" if opponent_type == "player" else "AI"
            r = llm_complete(
                prompt=(
                    "A player just had a quick battle vs %s (%s difficulty). Outcome: %s.%s "
                    "Write: 1) A punchy 1-sentence battle commentary (exciting, dramatic). "
                    "2) One tactical tip for next time. "
                    "Return JSON: {\"commentary\": \"...\", \"tip\": \"...\"}" % (opp_label, difficulty, result_word, rps_ctx)
                ),
                system_prompt="Output strict JSON only. Be concise and engaging.",
                task_type="speed",
                max_tokens=120,
                temperature=0.8,
            )
            if r.success and r.content:
                import json as _json
                raw = r.content.strip().strip('`')
                if raw.startswith('json'):
                    raw = raw[4:]
                parsed = _json.loads(raw)
                commentary = parsed.get('commentary')
                strategy_tip = parsed.get('tip')
        except Exception:
            pass

        try:
            from backend.routes.social_routes import push_activity
            result_word = {'win': 'won', 'loss': 'lost', 'draw': 'drew'}.get(result, result)
            push_activity(user_id, "battle", f"Quick battle: {result_word} ({points_delta:+d} pts)", {"result": result, "points_delta": points_delta})
        except Exception:
            pass

        payload = {
            'success': True,
            'status': 'matched',
            'battle_id': battle_id,
            'result': result,
            'points_delta': points_delta,
            'message': 'Battle started',
            'opponent_type': opponent_type,
            'ai_commentary': commentary,
            'strategy_tip': strategy_tip,
            'battle_mode': (
                'rps_pvp' if use_rps and opponent_type == 'player' else ('rps' if use_rps else 'skirmish')
            ),
        }
        if player_move:
            payload['player_move'] = player_move
        if ai_move:
            payload['opponent_move'] = ai_move
            if opponent_type == 'ai':
                payload['ai_move'] = ai_move
        if hunter_xp_info:
            payload['hunter_xp'] = hunter_xp_info
        payload['instant_skirmish_note'] = (
            'One-click skirmish uses difficulty-weighted odds. '
            'Send player_move rock|paper|scissors for a skill duel.'
        )
        return jsonify(payload), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/agents/match', methods=['POST'])
def battle_agents_match():
    """Run an agent-vs-agent battle using their battle skills."""
    try:
        data = request.get_json(silent=True) or {}
        agent_a = data.get('agent_a')
        agent_b = data.get('agent_b')
        if not agent_a or not agent_b:
            return jsonify({'success': False, 'error': 'agent_a and agent_b are required'}), 400

        from backend.services.agent_skillset import agent_skillset
        all_skillsets = agent_skillset.get_all_skillsets().get('agents', {})
        a = all_skillsets.get(agent_a)
        b = all_skillsets.get(agent_b)
        if not a or not b:
            return jsonify({'success': False, 'error': 'agent not found'}), 404

        a_profiles = _safe_skill_profiles(a.get('battle_skill_profiles', []), max_count=15)
        b_profiles = _safe_skill_profiles(b.get('battle_skill_profiles', []), max_count=15)
        a_power = sum(_to_int(s.get('battle_power', 0)) for s in a_profiles) + random.randint(0, 50)
        b_power = sum(_to_int(s.get('battle_power', 0)) for s in b_profiles) + random.randint(0, 50)

        if a_power == b_power:
            winner = random.choice([agent_a, agent_b])
        else:
            winner = agent_a if a_power > b_power else agent_b

        # AI battle analysis
        analysis = None
        try:
            from backend.services.llm_service import complete as llm_complete
            r = llm_complete(
                prompt=(
                    "Agent battle result: %s (power %d, %d skills) vs %s (power %d, %d skills). "
                    "Winner: %s. Power gap: %d. "
                    "Write a 2-sentence dramatic battle narrative and one strategic insight about why %s won. "
                    "Return JSON: {\"narrative\": \"...\", \"insight\": \"...\"}"
                    % (agent_a, a_power, len(a_profiles),
                       agent_b, b_power, len(b_profiles),
                       winner, abs(a_power - b_power), winner)
                ),
                system_prompt="Output strict JSON only. Be vivid and insightful.",
                task_type="speed",
                max_tokens=150,
                temperature=0.85,
            )
            if r.success and r.content:
                import json as _json
                raw = r.content.strip().strip('`')
                if raw.startswith('json'):
                    raw = raw[4:]
                analysis = _json.loads(raw)
        except Exception:
            pass

        return jsonify({
            'success': True,
            'battle_id': str(uuid.uuid4())[:10],
            'timestamp': datetime.utcnow().isoformat(),
            'agent_a': {'id': agent_a, 'power': a_power, 'skill_count': len(a_profiles)},
            'agent_b': {'id': agent_b, 'power': b_power, 'skill_count': len(b_profiles)},
            'winner': winner,
            'ai_analysis': analysis,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _battle_leaderboard_from_points(limit: int) -> list:
    """Build battle leaderboard from unified points file store (competition ranking)."""
    import os
    import json
    import hashlib
    leaderboard = []
    try:
        from backend.services.unified_points_database import unified_points_db
        points_dir = getattr(unified_points_db, 'points_dir', None)
        if not points_dir or not os.path.isdir(points_dir):
            return []
        for fn in os.listdir(points_dir):
            if not fn.endswith('.json'):
                continue
            user_id = fn[:-5]
            try:
                store = unified_points_db._load_file_store(user_id)
                systems = store.get('systems') or {}
                bp = int(float(systems.get('battle_points', 0) or 0))
                wins = int(float(systems.get('battle_wins', 0) or 0))
                losses = int(float(systems.get('battle_losses', 0) or 0))
                draws = int(float(systems.get('battle_draws', 0) or 0))
                total = wins + losses + draws
                if bp == 0 and total == 0:
                    continue
                h = int(hashlib.md5(user_id.encode()).hexdigest()[:4], 16)
                nouns = ["Hunter", "Master", "Creator", "Wizard", "Noder", "Seeker", "Ranger", "Fighter"]
                adjectives = ["Alpha", "Prime", "Swift", "Dark", "Neon", "Gold", "Elite", "Storm"]
                display_name = adjectives[h % len(adjectives)] + " " + nouns[(h // len(adjectives)) % len(nouns)]
                leaderboard.append({
                    'user_id': user_id,
                    'display_name': display_name,
                    'battle_points': bp,
                    'wins': wins,
                    'losses': losses,
                    'draws': draws,
                    'total': total,
                    'win_rate': round((wins / total * 100), 1) if total > 0 else 0.0,
                })
            except Exception:
                continue
        leaderboard.sort(key=lambda p: (p['battle_points'], p['wins']), reverse=True)
        return leaderboard[:limit]
    except Exception:
        return []


def _leaderboard_payload():
    """Shared body for global and seasonal leaderboards."""
    limit = _clamped_limit(request.args.get('limit', 10), default=10, max_value=50)
    user_id = request.args.get('user_id', _resolve_uid())
    leaderboard = []
    try:
        from backend.services.battle_db_service import get_battle_leaderboard
        rows = get_battle_leaderboard(limit=limit) or []
        if rows:
            import hashlib
            for r in rows:
                uid = r.get('user_id', '')
                h = int(hashlib.md5(uid.encode()).hexdigest()[:4], 16)
                nouns = ["Hunter", "Master", "Creator", "Wizard", "Noder", "Seeker", "Ranger", "Fighter"]
                adjectives = ["Alpha", "Prime", "Swift", "Dark", "Neon", "Gold", "Elite", "Storm"]
                leaderboard.append({
                    'user_id': uid,
                    'display_name': adjectives[h % len(adjectives)] + " " + nouns[(h // len(adjectives)) % len(nouns)],
                    'battle_points': int(r.get('total_points', 0) or 0),
                    'wins': int(r.get('wins', 0) or 0),
                    'losses': int(r.get('losses', 0) or 0),
                    'draws': int(r.get('draws', 0) or 0),
                    'total': int(r.get('total', 0) or 0),
                    'win_rate': round((int(r.get('wins', 0) or 0) / max(1, int(r.get('total', 1) or 1))) * 100, 1),
                })
    except Exception:
        pass
    if not leaderboard:
        leaderboard = _battle_leaderboard_from_points(limit)
    my_rank = None
    for i, p in enumerate(leaderboard):
        if p.get('user_id') == user_id:
            my_rank = i + 1
            break
    if my_rank is None and user_id:
        full = _battle_leaderboard_from_points(500)
        for i, p in enumerate(full):
            if p.get('user_id') == user_id:
                my_rank = i + 1
                break
    return {
        'success': True,
        'leaderboard': leaderboard,
        'my_rank': my_rank,
        'competition': 'quick_battle',
    }


def _battle_trophies_for_stats(stats: dict) -> list:
    mc = _load_battle_minimal_content()
    defs = mc.get('trophy_definitions') or []
    trophies = []
    for d in defs:
        tid = d.get('id')
        earned = False
        if tid == 'first_skirmish':
            earned = stats.get('total_battles', 0) >= 1
        elif tid == 'streak_3':
            earned = stats.get('win_streak', 0) >= 3
        elif tid == 'duelist':
            earned = stats.get('wins', 0) >= 1
        row = dict(d)
        row['earned'] = earned
        trophies.append(row)
    return trophies


def _battle_social_progress(user_id: str) -> dict:
    """Return tournament/clan progress related to a user id, preserving old string member state."""
    try:
        from backend.services import battle_social_store as bss
        state = bss.load_state()
    except Exception:
        state = {"tournaments": [], "clans": []}

    tournaments = []
    for tour in state.get("tournaments", []):
        if not isinstance(tour, dict):
            continue
        participants = [str(p) for p in (tour.get("participants") or []) if p]
        if user_id in participants:
            tournaments.append(_tournament_api_dict(tour))

    clans = []
    for clan in state.get("clans", []):
        if not isinstance(clan, dict):
            continue
        members = [str(m) for m in (clan.get("members") or []) if m]
        user_members = [
            m for m in members
            if m == user_id or m.startswith(user_id + ":") or m.startswith(user_id + "::")
        ]
        if user_members:
            clans.append({
                "id": clan.get("id", ""),
                "name": clan.get("name", ""),
                "focus": clan.get("focus", ""),
                "memberships": user_members,
                "member_count": len(members),
            })

    return {
        "joined_tournaments": tournaments,
        "joined_clans": clans,
    }


def _lab_progress_slice(user_id: str) -> dict:
    try:
        from backend.routes.lab_routes import lab_public_summary
        summary = lab_public_summary(user_id)
        if isinstance(summary, dict):
            return {
                "tier": summary.get("lab_tier", "Novice"),
                "researched_count": int(summary.get("researched_count") or 0),
                "total": int(summary.get("total") or 0),
                "exploration_count": int(summary.get("exploration_count") or 0),
                "deep_scan_count": int(summary.get("deep_scan_count") or 0),
            }
    except Exception:
        pass
    return {
        "tier": "Novice",
        "researched_count": 0,
        "total": 0,
        "exploration_count": 0,
        "deep_scan_count": 0,
    }


def _battle_progress_payload(user_id: str, history_limit: int = 8) -> dict:
    stats = _get_battle_stats(user_id)
    history = []
    try:
        from backend.services.battle_db_service import get_battle_history
        history = get_battle_history(user_id, limit=history_limit) or []
    except Exception:
        history = []

    leaderboard = _leaderboard_payload()
    social = _battle_social_progress(user_id)
    resources = _battle_resources_status(user_id)
    season = _battle_season_status(user_id)
    telemetry = _battle_telemetry_status(user_id, limit=10)
    crypto = _battle_crypto_status(user_id)
    trophies = _battle_trophies_for_stats(stats)
    earned_trophies = [t for t in trophies if t.get("earned")]
    lab_progress = _lab_progress_slice(user_id)

    missing_for_v2 = []
    if not history:
        missing_for_v2.append("No durable battle history found for this user until battle_matches is populated.")
    if not social.get("joined_tournaments"):
        missing_for_v2.append("Tournament participation exists, but this user has not joined a tournament yet.")
    if not social.get("joined_clans"):
        missing_for_v2.append("Clan membership should be stored against user_id plus selected agent.")
    if int((season.get("current") or {}).get("matches", 0) or 0) <= 0:
        missing_for_v2.append("Dedicated season progress is ready, but this user has not recorded a season match yet.")
    if telemetry.get("event_count", 0) <= 0:
        missing_for_v2.append("Per-match telemetry is ready, but this user has no tracked telemetry yet.")
    if not any(o.get("ready") for o in (crypto.get("options") or [])):
        missing_for_v2.append("Crypto earning options are present; play more Battle actions to unlock a claim.")

    completion_total = 9
    completion_done = 0
    completion_done += 1 if stats.get("total_battles", 0) > 0 else 0
    completion_done += 1 if stats.get("battle_points", 0) != 0 else 0
    completion_done += 1 if history else 0
    completion_done += 1 if earned_trophies else 0
    completion_done += 1 if social.get("joined_tournaments") else 0
    completion_done += 1 if social.get("joined_clans") else 0
    completion_done += 1 if int((season.get("current") or {}).get("matches", 0) or 0) > 0 else 0
    completion_done += 1 if telemetry.get("event_count", 0) > 0 else 0
    completion_done += 1 if crypto.get("options") else 0

    return {
        "success": True,
        "user_id": user_id,
        "version": "battle-v2-progress-draft",
        "progress": {
            "completion_percent": round((completion_done / completion_total) * 100),
            "completion_done": completion_done,
            "completion_total": completion_total,
            "stats": stats,
            "history": history,
            "resources": resources,
            "season": season,
            "telemetry": telemetry,
            "crypto": crypto,
            "trophies": trophies,
            "earned_trophy_count": len(earned_trophies),
            "social": social,
            "leaderboard": {
                "my_rank": leaderboard.get("my_rank"),
                "competition": leaderboard.get("competition", "quick_battle"),
            },
            "lab": lab_progress,
        },
        "missing_for_v2": missing_for_v2,
    }


@battle_bp.route('/api/battle/leaderboard', methods=['GET'])
def battle_leaderboard():
    """Get battle leaderboard (competition). From DB when migration run, else from unified points."""
    try:
        return jsonify(_leaderboard_payload()), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/progress', methods=['GET'])
def battle_progress():
    """Single user-id scoped progress contract for Battle v2.0 surfaces."""
    try:
        user_id = _resolve_uid()
        limit = _clamped_limit(request.args.get('history_limit', 8), default=8, max_value=50)
        return jsonify(_battle_progress_payload(user_id, limit)), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/v2/resources', methods=['GET'])
def battle_v2_resources():
    """User-owned Battle resource balances and earning ledger."""
    try:
        user_id = _resolve_uid()
        return jsonify({"success": True, "user_id": user_id, **_battle_resources_status(user_id)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/v2/telemetry', methods=['GET'])
def battle_v2_telemetry():
    """Per-match telemetry tracked for Battle v2 intelligence."""
    try:
        user_id = _resolve_uid()
        limit = _clamped_limit(request.args.get('limit', 20), default=20, max_value=100)
        return jsonify({"success": True, "user_id": user_id, **_battle_telemetry_status(user_id, limit=limit)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/crypto', methods=['GET'])
def battle_crypto():
    """Per-user in-game Battle crypto status. Awards use internal mn2_balance, not wallet transfers."""
    try:
        user_id = _resolve_uid()
        return jsonify({"success": True, **_battle_crypto_status(user_id)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/crypto/claim', methods=['POST'])
def battle_crypto_claim():
    """Claim an eligible Battle MN2 earning option."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_uid()
        option_id = (data.get("option_id") or request.args.get("option_id") or "").strip()
        body, status = _claim_battle_crypto(user_id, option_id)
        return jsonify(body), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/season/<season_id>/leaderboard', methods=['GET'])
def battle_season_leaderboard(season_id):
    """Seasonal leaderboard (same pool as global until seasonal splits are stored)."""
    try:
        p = _leaderboard_payload()
        p['season_id'] = season_id
        p['season_note'] = 'Uses quick-battle unified points; dedicated season ledger not stored yet.'
        for i, row in enumerate(p.get('leaderboard') or [], start=1):
            row['rank'] = i
            uid = row.get('user_id')
            pts = int(row.get('battle_points') or 0)
            row['points'] = pts
        return jsonify(p), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/season/<season_id>/progress', methods=['GET'])
def battle_season_progress(season_id):
    """Dedicated user season progress for Battle v2.0."""
    try:
        user_id = _resolve_uid()
        status = _battle_season_status(user_id)
        seasons = status.get("seasons") or {}
        sid = (season_id or "").strip()
        if sid in {"current", "active"}:
            sid = status.get("current_season_id")
        return jsonify({
            "success": True,
            "user_id": user_id,
            "season_id": sid,
            "progress": seasons.get(sid) or (status.get("current") if sid == status.get("current_season_id") else None) or {
                "season_id": sid,
                "score": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "matches": 0,
                "points_delta": 0,
            },
            "current_season_id": status.get("current_season_id"),
            "implementation_status": status.get("implementation_status"),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _filtered_battle_tournaments():
    """Tournaments from persistent store; optional ?status= filter (e.g. open)."""
    from backend.services import battle_social_store as bss
    status = (request.args.get('status') or '').strip().lower()
    tours = bss.get_tournaments_filtered(status if status else None)
    return [_tournament_api_dict(t) for t in tours]


@battle_bp.route('/api/battle/fantasy/tournaments', methods=['GET'])
def battle_fantasy_tournaments():
    """Get fantasy tournaments"""
    try:
        return jsonify({
            'success': True,
            'tournaments': _filtered_battle_tournaments(),
            'implementation_status': 'active'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/tournaments', methods=['GET'])
def battle_tournaments_legacy_alias():
    """Legacy alias for GET /api/battle/fantasy/tournaments (older clients used this path)."""
    return battle_fantasy_tournaments()


@battle_bp.route('/api/battle/fantasy/tournaments/<tournament_id>/join', methods=['POST'])
def battle_fantasy_tournaments_join(tournament_id):
    """Join fantasy tournament"""
    try:
        from backend.services import battle_social_store as bss
        user_id = _resolve_uid()
        ok, detail, code = bss.join_tournament(tournament_id, user_id)
        if not ok:
            return jsonify({'success': False, 'error': detail}), code
        return jsonify({
            'success': True,
            'tournament_id': tournament_id,
            'message': 'Joined tournament',
            'participants': detail,
            'implementation_status': 'active'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/tournament/join', methods=['POST'])
def battle_tournament_join_legacy():
    """Legacy alias: POST body { tournament_id } (URL join is canonical)."""
    try:
        from backend.services import battle_social_store as bss
        body = request.get_json() or {}
        tid = body.get('tournament_id') or body.get('tournamentId')
        if not tid or not isinstance(tid, str):
            return jsonify({'success': False, 'error': 'tournament_id required'}), 400
        user_id = _resolve_uid()
        ok, detail, code = bss.join_tournament(tid.strip(), user_id)
        if not ok:
            return jsonify({'success': False, 'error': detail}), code
        return jsonify({
            'success': True,
            'tournament_id': tid.strip(),
            'message': 'Joined tournament',
            'participants': detail,
            'implementation_status': 'active'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/clans', methods=['GET'])
def battle_clans():
    """Get all battle clans with member counts."""
    try:
        from backend.services import battle_social_store as bss
        state = bss.load_state()
        clans = []
        for clan in state.get('clans', []):
            mem = clan.get('members') or []
            clans.append({
                'id': clan['id'],
                'name': clan['name'],
                'focus': clan.get('focus', ''),
                'members': mem,
                'member_count': len(mem),
            })
        return jsonify({'success': True, 'clans': clans}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/clans/<clan_id>/join', methods=['POST'])
def battle_clan_join(clan_id):
    """Join a clan with an agent."""
    try:
        from backend.services import battle_social_store as bss
        data = request.get_json(silent=True) or {}
        user_id = _resolve_uid()
        agent_id = data.get('agent_id') or data.get('user_id')
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400

        membership_id = f"{user_id}:{agent_id}"
        ok, detail, code = bss.join_clan(clan_id, membership_id)
        if not ok:
            return jsonify({'success': False, 'error': detail}), code

        return jsonify({
            'success': True,
            'clan_id': clan_id,
            'user_id': user_id,
            'agent_id': agent_id,
            'membership_id': membership_id,
            'member_count': detail,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/fantasy/resources', methods=['GET'])
def battle_fantasy_resources():
    """Get fantasy battle resources (user-owned v2 ledger + balances)."""
    try:
        user_id = _resolve_uid()
        status = _battle_resources_status(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'resources': status.get("balances", {}),
            'ledger': status.get("ledger", []),
            'ledger_count': status.get("ledger_count", 0),
            'implementation_status': status.get("implementation_status", "user_ledger")
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/intelligence/statistics', methods=['GET'])
def battle_intelligence_statistics():
    """Battle intelligence statistics (merged with your quick-battle stats)."""
    try:
        user_id = _resolve_uid()
        st = _get_battle_stats(user_id)
        mc = _load_battle_minimal_content()
        intel = dict(mc.get('intelligence_defaults') or {})
        intel['win_rate'] = st.get('win_rate', 0)
        intel['total_battles'] = st.get('total_battles', 0)
        intel['win_streak'] = st.get('win_streak', 0)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'stats': intel,
            'implementation_status': 'minimal'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@battle_bp.route('/api/battle/pvp/trophies', methods=['GET'])
def battle_pvp_trophies():
    """PVP trophies: definitions plus earned flags from quick-battle stats."""
    try:
        user_id = _resolve_uid()
        st = _get_battle_stats(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'trophies': _battle_trophies_for_stats(st),
            'implementation_status': 'minimal'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
