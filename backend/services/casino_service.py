"""
Virtual-coins casino with optional MN2 real-money rail.
"""
from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_ROOT, "data", "casino_config.json")
_RPS_MOVES = ("rock", "paper", "scissors")
_RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
_BATTLE_V2_PATH = os.path.join(_ROOT, "data", "battle_v2_state.json")
_SOCIAL_DATA_PATH = os.path.join(_ROOT, "data", "social_structure.json")
_MN2_CONFIG_PATH = os.path.join(_ROOT, "data", "mn2_config.json")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utcnow()).isoformat()


def _today_key() -> str:
    return _utcnow().strftime("%Y-%m-%d")


def _load_config() -> Dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ledger_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_bets.jsonl")


def _append_ledger(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    path = _ledger_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        # Do not fail bets when log dir is not writable on the server.
        pass
    # Best-effort mirror into the indexed DB (powers the live activity feed).
    try:
        from backend.services import casino_ledger
        casino_ledger.record(row)
    except Exception:
        pass
    # Tournament scoring: add this bet's net to any running tournament the user
    # has joined in this currency. Best-effort; never fails the bet.
    try:
        from backend.services import casino_tournaments
        casino_tournaments.record_bet(row)
    except Exception:
        pass
    # Progressive jackpot: contribute from this wager and maybe drop the pool.
    # Returns an award dict when the jackpot hits, which callers attach to the
    # play result. Never fails the bet.
    # Progressive jackpot: contribute from this wager and maybe drop the pool.
    # Progression XP / achievements — best-effort, before jackpot return.
    try:
        from backend.services import casino_progression
        casino_progression.on_bet(row)
    except Exception:
        pass
    try:
        from backend.services import casino_jackpot
        return casino_jackpot.on_bet(row)
    except Exception:
        return None


def _read_ledger(user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
    path = _ledger_path()
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("user_id") == user_id:
                    rows.append(row)
    except OSError:
        return []
    return list(reversed(rows[-limit:]))


def _count_bets_today(user_id: str) -> int:
    path = _ledger_path()
    if not os.path.isfile(path):
        return 0
    today = _today_key()
    count = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("user_id") == user_id and str(row.get("created_at") or "").startswith(today):
                    count += 1
    except OSError:
        return 0
    return count


def _payment_config() -> Dict[str, Any]:
    cfg = _load_config()
    rm = cfg.get("real_money") if isinstance(cfg.get("real_money"), dict) else {}
    packs = rm.get("paypal_deposit_packs") if isinstance(rm.get("paypal_deposit_packs"), list) else []
    mn2_packs = rm.get("mn2_buyin_packs") if isinstance(rm.get("mn2_buyin_packs"), list) else []
    return {
        "enabled": bool(rm.get("enabled")),
        "rails": [str(r).lower() for r in (rm.get("rails") or ["mn2"])],
        "mn2_min_bet": float(rm.get("mn2_min_bet") or 0.05),
        "mn2_max_bet": float(rm.get("mn2_max_bet") or 5.0),
        "paypal_min_bet": float(rm.get("paypal_min_bet") or 0.5),
        "paypal_max_bet": float(rm.get("paypal_max_bet") or 25.0),
        "paypal_currency": str(rm.get("paypal_currency") or "USD"),
        "paypal_deposit_packs": packs,
        "mn2_buyin_packs": mn2_packs,
        "disclaimer_coins": rm.get("disclaimer_coins") or cfg.get("disclaimer") or "",
        "disclaimer_mn2": rm.get("disclaimer_mn2") or (
            "MN2 bets use your on-chain wallet balance. Virtual coin bets remain separate."
        ),
        "disclaimer_paypal": rm.get("disclaimer_paypal") or (
            "USD bets use your PayPal-funded casino balance. Deposit first, then stake in USD."
        ),
    }


def _paypal_enabled() -> bool:
    pay = _payment_config()
    return pay["enabled"] and "paypal" in pay["rails"]


def _normalize_currency(currency: Optional[str]) -> str:
    c = (currency or "coins").strip().lower()
    pay = _payment_config()
    if c in ("usd", "paypal", "fiat"):
        if pay["enabled"] and "paypal" in pay["rails"]:
            return "usd"
    if c == "mn2":
        if pay["enabled"] and "mn2" in pay["rails"]:
            return "mn2"
    return "coins"


def _user_fiat_balance(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db

    result = unified_points_db.get_all_points(user_id)
    points = result.get("points") if isinstance(result, dict) else {}
    if not isinstance(points, dict):
        return 0.0
    bal = float(points.get("casino_fiat_balance") or 0)
    if bal == 0 and isinstance(points.get("systems"), dict):
        bal = float(points["systems"].get("casino_fiat_balance") or 0)
    return bal


def _user_balance(user_id: str, currency: str) -> float:
    if currency == "mn2":
        return _user_mn2_balance(user_id)
    if currency == "usd":
        return _user_fiat_balance(user_id)
    return _user_coins(user_id)


def _parse_bet_amount(bet: Any, currency: str) -> Optional[float]:
    try:
        amount = float(bet)
    except (TypeError, ValueError):
        return None
    if currency == "mn2":
        return round(amount, 8)
    if currency == "usd":
        return round(amount, 2)
    return float(int(amount))


def _round_payout(amount: float, currency: str) -> float:
    if currency == "mn2":
        return round(amount, 8)
    if currency == "usd":
        return round(amount, 2)
    return float(int(round(amount)))


def _currency_label(currency: str) -> str:
    if currency == "mn2":
        return "MN2"
    if currency == "usd":
        return "USD"
    return "coins"


def _mn2_config() -> Dict[str, Any]:
    try:
        with open(_MN2_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _user_mn2_balance(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db

    result = unified_points_db.get_all_points(user_id)
    points = result.get("points") if isinstance(result, dict) else {}
    if not isinstance(points, dict):
        return 0.0
    bal = float(points.get("mn2_balance") or 0)
    if bal == 0 and isinstance(points.get("systems"), dict):
        bal = float(points["systems"].get("mn2_balance") or 0)
    return bal


def get_public_config() -> Dict[str, Any]:
    cfg = _load_config()
    games = cfg.get("games") if isinstance(cfg.get("games"), dict) else {}
    public_games = {}
    for key, game in games.items():
        if not isinstance(game, dict):
            continue
        row = {
            "label": game.get("label") or key,
            "payout_multiplier": float(game.get("payout_multiplier") or 0),
            "choices": game.get("choices") or [],
        }
        sides = game.get("sides")
        if sides is not None:
            row["sides"] = int(sides)
        if game.get("min_multiplier") is not None:
            row["min_multiplier"] = float(game.get("min_multiplier"))
        if game.get("max_multiplier") is not None:
            row["max_multiplier"] = float(game.get("max_multiplier"))
        if game.get("symbols"):
            row["symbols"] = list(game.get("symbols"))
        if game.get("match_2_multiplier") is not None:
            row["match_2_multiplier"] = float(game.get("match_2_multiplier"))
        if game.get("match_3_multiplier") is not None:
            row["match_3_multiplier"] = float(game.get("match_3_multiplier"))
        if isinstance(game.get("payout_multipliers"), dict):
            row["payout_multipliers"] = game.get("payout_multipliers")
        if str(key).startswith("slot_"):
            for field in (
                "icon", "volatility", "rtp_estimate", "reels", "symbol_display",
                "wild_symbols", "scatter_symbol", "scatter_min", "scatter_multiplier",
                "jackpot_symbol", "jackpot_multiplier", "paytable", "weights",
            ):
                if game.get(field) is not None:
                    row[field] = game.get(field)
            row["has_wild"] = bool(game.get("wild_symbols"))
            row["has_scatter"] = bool(game.get("scatter_symbol"))
        if key == "crash":
            for field in (
                "icon", "rtp_estimate", "house_edge", "growth_per_second",
                "max_round_seconds", "max_auto_cashout",
            ):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "plinko":
            for field in ("icon", "rtp_estimate", "rows", "risk_tables"):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "mines":
            for field in (
                "icon", "rtp_estimate", "tiles", "default_mines",
                "min_mines", "max_mines", "house_edge",
            ):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "wheel":
            for field in ("icon", "rtp_estimate", "risk_tables"):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "keno":
            for field in ("icon", "rtp_estimate", "pool", "draw", "max_spots", "pay_table"):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "hilo":
            for field in ("icon", "rtp_estimate", "ranks", "house_edge"):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        if key == "roulette":
            for field in ("icon", "rtp_estimate", "pockets"):
                if game.get(field) is not None:
                    row[field] = game.get(field)
        for card_key in ("blackjack", "baccarat", "video_poker"):
            if key == card_key:
                for field in ("icon", "rtp_estimate", "house_edge", "blackjack_payout", "banker_commission", "paytable"):
                    if game.get(field) is not None:
                        row[field] = game.get(field)
        public_games[key] = row
    pay = _payment_config()
    mn2_cfg = _mn2_config()
    featured = cfg.get("featured_games") if isinstance(cfg.get("featured_games"), list) else []
    social_links = cfg.get("social_links") if isinstance(cfg.get("social_links"), list) else []
    return {
        "currency": cfg.get("currency") or "coins",
        "disclaimer": pay["disclaimer_coins"] if not pay["enabled"] else pay["disclaimer_mn2"],
        "min_bet": int(cfg.get("min_bet") or 1),
        "max_bet": int(cfg.get("max_bet") or 500),
        "max_bets_per_day": int(cfg.get("max_bets_per_day") or 200),
        "featured_games": featured,
        "social_links": social_links,
        "games": public_games,
        "real_money": {
            "enabled": pay["enabled"],
            "rails": pay["rails"],
            "mn2_min_bet": pay["mn2_min_bet"],
            "mn2_max_bet": pay["mn2_max_bet"],
            "paypal_min_bet": pay["paypal_min_bet"],
            "paypal_max_bet": pay["paypal_max_bet"],
            "paypal_currency": pay["paypal_currency"],
            "paypal_deposit_packs": pay["paypal_deposit_packs"],
            "ticker": mn2_cfg.get("ticker") or "MN2",
            "coins_per_mn2": float(mn2_cfg.get("coins_per_mn2") or 100),
        },
    }


def _user_coins(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db

    result = unified_points_db.get_all_points(user_id)
    points = result.get("points") if isinstance(result, dict) else {}
    if not isinstance(points, dict):
        return 0.0
    return float(points.get("coins") or 0)


def get_balance(user_id: str) -> Dict[str, Any]:
    try:
        cfg = get_public_config()
        pay = _payment_config()
        return {
            "success": True,
            "user_id": user_id,
            "currency": cfg["currency"],
            "balance": _user_coins(user_id),
            "mn2_balance": _user_mn2_balance(user_id),
            "fiat_balance": _user_fiat_balance(user_id),
            "real_money": {
                "enabled": pay["enabled"],
                "rails": pay["rails"],
                "mn2_min_bet": pay["mn2_min_bet"],
                "mn2_max_bet": pay["mn2_max_bet"],
                "paypal_min_bet": pay["paypal_min_bet"],
                "paypal_max_bet": pay["paypal_max_bet"],
                "paypal_deposit_packs": pay["paypal_deposit_packs"],
                "disclaimer_mn2": pay["disclaimer_mn2"],
                "disclaimer_paypal": pay["disclaimer_paypal"],
                "disclaimer_coins": pay["disclaimer_coins"],
            },
            "active_currency": "coins",
            "bets_today": _count_bets_today(user_id),
            "max_bets_per_day": cfg["max_bets_per_day"],
            "min_bet": cfg["min_bet"],
            "max_bet": cfg["max_bet"],
            "mn2_min_bet": pay["mn2_min_bet"],
            "mn2_max_bet": pay["mn2_max_bet"],
            "paypal_min_bet": pay["paypal_min_bet"],
            "paypal_max_bet": pay["paypal_max_bet"],
            "paypal_deposit_packs": pay["paypal_deposit_packs"],
            "disclaimer": pay["disclaimer_coins"],
            "games": cfg.get("games") or {},
            "featured_games": cfg.get("featured_games") or [],
            "social_links": cfg.get("social_links") or [],
        }
    except Exception as exc:
        return {
            "success": False,
            "user_id": user_id,
            "error": str(exc),
            "currency": "coins",
            "balance": 0,
            "mn2_balance": 0,
            "fiat_balance": 0,
            "bets_today": 0,
            "max_bets_per_day": 200,
            "min_bet": 5,
            "max_bet": 500,
            "disclaimer": "",
            "games": {},
        }


def _validate_bet(user_id: str, bet: float, currency: str = "coins") -> Optional[str]:
    currency = _normalize_currency(currency)
    amount = _parse_bet_amount(bet, currency)
    if amount is None or amount <= 0:
        return "Invalid bet amount"
    if currency in ("mn2", "usd"):
        try:
            from flask import has_request_context, request
            from backend.services.account_security_service import check_real_money_action

            token = None
            if has_request_context():
                data = request.get_json(silent=True) or {}
                token = data.get("verification_token") or data.get("security_token")
            sec_err = check_real_money_action(user_id, verification_token=token)
            if sec_err:
                return sec_err
        except Exception:
            pass
    cfg = get_public_config()
    pay = _payment_config()
    if currency in ("mn2", "usd"):
        try:
            tiers = (cfg.get("bet_tiers") or []) if isinstance(cfg.get("bet_tiers"), list) else []
            if tiers:
                from backend.services.unified_points_database import unified_points_db
                pts = unified_points_db.get_all_points(str(user_id))
                xp = float((pts.get("points") or {}).get("xp_total") or (pts.get("systems") or {}).get("xp_total") or 0)
                tier = None
                for t in sorted(tiers, key=lambda x: int(x.get("min_xp") or 0), reverse=True):
                    if xp >= float(t.get("min_xp") or 0):
                        tier = t
                        break
                if tier:
                    cap_key = "max_bet_mn2" if currency == "mn2" else "max_bet_usd"
                    cap = tier.get(cap_key)
                    if cap is not None and amount > float(cap):
                        return f"Bet exceeds tier cap ({cap} {currency}) — earn more XP to unlock higher limits"
        except Exception:
            pass
    if currency == "mn2":
        if amount < pay["mn2_min_bet"]:
            return f"Minimum bet is {pay['mn2_min_bet']} MN2"
        if amount > pay["mn2_max_bet"]:
            return f"Maximum bet is {pay['mn2_max_bet']} MN2"
    elif currency == "usd":
        if amount < pay["paypal_min_bet"]:
            return f"Minimum bet is ${pay['paypal_min_bet']:.2f} USD"
        if amount > pay["paypal_max_bet"]:
            return f"Maximum bet is ${pay['paypal_max_bet']:.2f} USD"
    else:
        if amount < cfg["min_bet"]:
            return f"Minimum bet is {cfg['min_bet']} coins"
        if amount > cfg["max_bet"]:
            return f"Maximum bet is {cfg['max_bet']} coins"
    if _count_bets_today(user_id) >= cfg["max_bets_per_day"]:
        return "Daily bet limit reached"
    if _user_balance(user_id, currency) < amount:
        return f"Insufficient {_currency_label(currency)}"
    try:
        from backend.services.casino_responsible_gaming import check_before_bet
        rg_err = check_before_bet(user_id, amount, currency)
        if rg_err:
            return rg_err
    except ImportError:
        pass
    return None


def _apply_balance_delta(
    user_id: str,
    delta: float,
    currency: str,
    game: str,
    meta: Dict[str, Any],
) -> None:
    from backend.services.unified_points_database import unified_points_db

    if delta == 0:
        return
    if currency == "mn2":
        point_type = "mn2_balance"
        source = "casino_mn2"
    elif currency == "usd":
        point_type = "casino_fiat_balance"
        source = "casino_paypal"
    else:
        point_type = "coins"
        source = "casino"
    unified_points_db.add_points(
        user_id=user_id,
        point_type=point_type,
        amount=float(delta),
        source=source,
        metadata={"game": game, "currency": currency, **meta},
    )


def _apply_coin_delta(user_id: str, delta: int, game: str, meta: Dict[str, Any]) -> None:
    _apply_balance_delta(user_id, float(delta), "coins", game, meta)


def _finalize_bet(
    user_id: str,
    game: str,
    bet: float,
    outcome: str,
    payout: float,
    details: Dict[str, Any],
    *,
    skip_stake: bool = False,
    exclude_leaderboard: bool = False,
    parent_bet_id: Optional[str] = None,
    double_step: int = 0,
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    bet = _parse_bet_amount(bet, currency) or 0
    payout = _round_payout(payout, currency)
    net = _round_payout(payout - (0 if skip_stake else bet), currency)
    if not skip_stake and bet > 0:
        _apply_balance_delta(user_id, -bet, currency, game, {"phase": "stake", **details})
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, game, {"phase": "payout", **details})

    row = {
        "bet_id": str(uuid.uuid4()),
        "user_id": user_id,
        "game": game,
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": exclude_leaderboard,
        "parent_bet_id": parent_bet_id,
        "double_step": double_step,
    }
    jackpot_award = _append_ledger(row)
    if currency == "mn2":
        try:
            from backend.services.activity_events_service import emit
            emit(
                "casino_mn2_bet",
                channel="casino",
                user_id=user_id,
                payload={"game": game, "bet": bet, "payout": payout, "net": net, "outcome": outcome, "bet_id": row["bet_id"]},
            )
        except Exception:
            pass
        try:
            from backend.services.exchange_casino_leaderboard_service import record_highroller_net

            record_highroller_net(user_id, net)
        except Exception:
            pass
        if net > 0 and outcome in ("win", "jackpot", "payout"):
            try:
                from backend.services.exchange_casino_quest_service import record_bridge_action, emit_bridge_market_event

                record_bridge_action(user_id, "casino_mn2_win")
                min_net = float(os.environ.get("BRIDGE_MARKET_MIN_MN2_WIN", "0.5"))
                if net >= min_net:
                    emit_bridge_market_event("casino_mn2_big_win", user_id, {
                        "game": game, "net": net, "bet": bet, "payout": payout, "outcome": outcome,
                    })
            except Exception:
                pass
    if net > 0 and outcome in ("win", "jackpot", "payout"):
        try:
            from backend.services.casino_social_service import on_big_win
            on_big_win(
                user_id=user_id,
                game=game,
                currency=currency,
                net=net,
                payout=payout,
                bet_id=row["bet_id"],
            )
        except Exception:
            pass
    try:
        from backend.services.casino_responsible_gaming import record_after_bet
        record_after_bet(user_id, net, currency)
    except ImportError:
        pass
    try:
        from backend.services.casino_social_service import track_referral_casino_play, track_referral_bet
        track_referral_casino_play(user_id)
        track_referral_bet(user_id)
    except Exception:
        pass
    if not skip_stake and bet > 0:
        try:
            from backend.services.battle_pass_service import record_battle_pass_action

            record_battle_pass_action(user_id, "casino_bet")
        except Exception:
            pass
    trophy_rebate = None
    try:
        from backend.services.casino_trophy_rake_rebate import apply_rebate
        trophy_rebate = apply_rebate(user_id, bet, net, currency, game)
    except ImportError:
        pass
    result = {
        "success": True,
        "bet_id": row["bet_id"],
        "game": game,
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "balance": _user_balance(user_id, currency),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
        try:
            from backend.services.casino_social_service import on_jackpot_win
            on_jackpot_win(
                user_id=user_id,
                currency=jackpot_award.get("currency") or currency,
                amount=float(jackpot_award.get("amount") or 0),
                reason=str((details or {}).get("jackpot_reason") or "jackpot"),
                bet_id=row["bet_id"],
            )
        except Exception:
            pass
    if trophy_rebate:
        result["trophy_rebate"] = trophy_rebate
        result["balance"] = _user_balance(user_id, currency)
    if currency == "coins":
        result["coins_balance"] = _user_coins(user_id)
        result["mn2_balance"] = _user_mn2_balance(user_id)
        result["fiat_balance"] = _user_fiat_balance(user_id)
    else:
        result["mn2_balance"] = _user_mn2_balance(user_id)
        result["fiat_balance"] = _user_fiat_balance(user_id)
        result["coins_balance"] = _user_coins(user_id)
    result.update(_double_offer(row))
    return result


def play_coin_flip(user_id: str, bet: float, choice: str, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("coin_flip") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or ["heads", "tails"])]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    result = random.choice(allowed)
    multiplier = float(game_cfg.get("payout_multiplier") or 1.9)
    payout = _round_payout(amount * multiplier, currency) if result == pick else 0
    outcome = "win" if payout > 0 else "loss"
    return _finalize_bet(
        user_id,
        "coin_flip",
        amount,
        outcome,
        payout,
        {"choice": pick, "result": result, "multiplier": multiplier},
        currency=currency,
    )


def play_dice(user_id: str, bet: float, guess: int, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("dice") or {}
    sides = int(game_cfg.get("sides") or 6)
    try:
        pick = int(guess)
    except (TypeError, ValueError):
        return {"success": False, "error": "guess must be an integer"}
    if pick < 1 or pick > sides:
        return {"success": False, "error": f"guess must be between 1 and {sides}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    roll = random.randint(1, sides)
    multiplier = float(game_cfg.get("payout_multiplier") or 4.0)
    payout = _round_payout(amount * multiplier, currency) if roll == pick else 0
    outcome = "win" if payout > 0 else "loss"
    return _finalize_bet(
        user_id,
        "dice",
        amount,
        outcome,
        payout,
        {"guess": pick, "roll": roll, "sides": sides, "multiplier": multiplier},
        currency=currency,
    )


def play_rps_bet(user_id: str, bet: float, choice: str, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("rps_bet") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or ["rock", "paper", "scissors"])]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    opponent = random.choice(allowed)
    if pick == opponent:
        outcome = "draw"
        payout = amount
    elif _RPS_BEATS.get(pick) == opponent:
        outcome = "win"
        multiplier = float(game_cfg.get("payout_multiplier") or 2.0)
        payout = _round_payout(amount * multiplier, currency)
    else:
        outcome = "loss"
        payout = 0
    return _finalize_bet(
        user_id,
        "rps_bet",
        amount,
        outcome,
        payout,
        {"choice": pick, "opponent": opponent, "multiplier": float(game_cfg.get("payout_multiplier") or 2.0)},
        currency=currency,
    )


def get_history(user_id: str, limit: int = 25) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 25), 100))
    return {"success": True, "user_id": user_id, "history": _read_ledger(user_id, safe_limit)}


# ---------------------------------------------------------------------------
# Crash — live multiplier game (provably fair, stateful: start then cash out)
# ---------------------------------------------------------------------------

def _crash_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("crash") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Crash",
        "icon": game.get("icon") or "🚀",
        "house_edge": float(game.get("house_edge") if game.get("house_edge") is not None else 0.03),
        "growth_per_second": float(game.get("growth_per_second") or 0.13863),
        "max_round_seconds": float(game.get("max_round_seconds") or 60),
        "max_auto_cashout": float(game.get("max_auto_cashout") or 100.0),
        "rtp_estimate": float(game.get("rtp_estimate") or 97.0),
    }


def _crash_rounds_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_crash_rounds.json")


def _load_crash_rounds() -> Dict[str, Any]:
    path = _crash_rounds_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_crash_rounds(data: Dict[str, Any]) -> None:
    try:
        with open(_crash_rounds_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _crash_elapsed_seconds(round_state: Dict[str, Any]) -> float:
    try:
        started = datetime.fromisoformat(round_state.get("started_at"))
    except Exception:
        return 0.0
    return max(0.0, (_utcnow() - started).total_seconds())


def _settle_crash_round(round_state: Dict[str, Any], payout: float, outcome: str) -> Dict[str, Any]:
    """Credit payout for a pre-staked crash round and write a correct ledger row."""
    user_id = round_state["user_id"]
    currency = _normalize_currency(round_state.get("currency"))
    bet = _parse_bet_amount(round_state.get("bet"), currency) or 0
    payout = _round_payout(payout, currency)
    net = _round_payout(payout - bet, currency)
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, "crash", {"phase": "payout"})
    details = {
        "bust": round_state.get("bust"),
        "cashout": round_state.get("cashout"),
        "growth_per_second": round_state.get("growth_per_second"),
        "fairness": round_state.get("fairness"),
        "auto_cashout": round_state.get("auto_cashout"),
    }
    row = {
        "bet_id": round_state.get("round_id") or str(uuid.uuid4()),
        "user_id": user_id,
        "game": "crash",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": False,
        "parent_bet_id": None,
        "double_step": 0,
    }
    jackpot_award = _append_ledger(row)
    result = {
        "success": True,
        "bet_id": row["bet_id"],
        "round_id": round_state.get("round_id"),
        "game": "crash",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "cashout": round_state.get("cashout"),
        "bust": round_state.get("bust"),
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
    return result


def _expire_stale_crash_rounds() -> None:
    """Treat abandoned rounds (never cashed out) as a bust loss and ledger them."""
    rounds = _load_crash_rounds()
    conf = _crash_config()
    grace = conf["max_round_seconds"] + 5.0
    changed = False
    for rid in list(rounds.keys()):
        state = rounds.get(rid)
        if not isinstance(state, dict) or state.get("settled"):
            rounds.pop(rid, None)
            changed = True
            continue
        if _crash_elapsed_seconds(state) > grace:
            state["cashout"] = 0.0
            _settle_crash_round(state, payout=0.0, outcome="loss")
            rounds.pop(rid, None)
            changed = True
    if changed:
        _save_crash_rounds(rounds)


def start_crash_round(
    user_id: str,
    bet: float,
    currency: str = "coins",
    auto_cashout: Optional[float] = None,
) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import crash as crash_engine

    currency = _normalize_currency(currency)
    _expire_stale_crash_rounds()
    rounds = _load_crash_rounds()
    for rid, state in rounds.items():
        if isinstance(state, dict) and state.get("user_id") == user_id and not state.get("settled"):
            return {
                "success": False,
                "error": "Finish your active crash round first",
                "code": "CRASH_ROUND_ACTIVE",
                "round_id": rid,
            }

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    conf = _crash_config()
    auto = None
    if auto_cashout is not None:
        try:
            auto = max(1.01, min(float(auto_cashout), conf["max_auto_cashout"]))
        except (TypeError, ValueError):
            auto = None

    proof = casino_rng.draw(user_id)
    bust = crash_engine.crash_point(proof["float"], conf["house_edge"])

    # Stake is committed up front (matches the other games' immediate debit).
    _apply_balance_delta(user_id, -amount, currency, "crash", {"phase": "stake"})

    round_id = str(uuid.uuid4())
    round_state = {
        "round_id": round_id,
        "user_id": user_id,
        "bet": amount,
        "currency": currency,
        "bust": bust,
        "auto_cashout": auto,
        "growth_per_second": conf["growth_per_second"],
        "started_at": _iso(),
        "settled": False,
        "fairness": {
            "server_seed_hash": proof["server_seed_hash"],
            "client_seed": proof["client_seed"],
            "nonce": proof["nonce"],
        },
    }
    rounds[round_id] = round_state
    _save_crash_rounds(rounds)

    return {
        "success": True,
        "round_id": round_id,
        "bet": amount,
        "currency": currency,
        "auto_cashout": auto,
        "growth_per_second": conf["growth_per_second"],
        "max_round_seconds": conf["max_round_seconds"],
        "started_at": round_state["started_at"],
        "fairness": round_state["fairness"],
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
    }


def cashout_crash_round(
    user_id: str,
    round_id: str,
    multiplier: Optional[float] = None,
) -> Dict[str, Any]:
    from backend.services.engines import crash as crash_engine

    rounds = _load_crash_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "CRASH_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "CRASH_ALREADY_SETTLED"}

    elapsed = _crash_elapsed_seconds(state)
    outcome_calc = crash_engine.settle(
        bust=float(state.get("bust") or 1.0),
        elapsed_seconds=elapsed,
        requested_multiplier=multiplier,
        auto_cashout=state.get("auto_cashout"),
        growth_per_second=float(state.get("growth_per_second") or 0.13863),
    )

    bet_currency = _normalize_currency(state.get("currency"))
    bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
    if outcome_calc["won"]:
        state["cashout"] = outcome_calc["cashout"]
        payout = bet_amount * outcome_calc["multiplier"]
        outcome = "win"
    else:
        state["cashout"] = 0.0
        payout = 0.0
        outcome = "loss"

    state["settled"] = True
    result = _settle_crash_round(state, payout=payout, outcome=outcome)
    rounds.pop(round_id, None)
    _save_crash_rounds(rounds)
    result["multiplier"] = outcome_calc["multiplier"]
    return result


# ---------------------------------------------------------------------------
# Provably-fair seed management + live activity feed
# ---------------------------------------------------------------------------

def get_fairness_state(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    return casino_rng.public_state(user_id)


def set_fairness_client_seed(user_id: str, client_seed: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    return casino_rng.set_client_seed(user_id, client_seed)


def rotate_fairness(user_id: str, new_client_seed: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_rng
    return casino_rng.rotate(user_id, new_client_seed)


def verify_fairness(server_seed: str, client_seed: str, nonce: int) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import crash as crash_engine

    if not server_seed or not client_seed:
        return {"success": False, "error": "server_seed, client_seed and nonce are required"}
    try:
        nonce_int = int(nonce)
    except (TypeError, ValueError):
        return {"success": False, "error": "nonce must be an integer"}
    proof = casino_rng.verify(server_seed, client_seed, nonce_int)
    proof["success"] = True
    proof["crash_bust"] = crash_engine.crash_point(proof["float"], _crash_config()["house_edge"])
    return proof


def get_activity_feed(limit: int = 12, currency: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_ledger

    safe_limit = max(1, min(int(limit or 12), 50))
    cur = _normalize_currency(currency) if currency else None
    wins = casino_ledger.recent_wins(limit=safe_limit, currency=cur)
    feed = []
    for row in wins:
        feed.append({
            "bet_id": row.get("bet_id"),
            "user_id": row.get("user_id"),
            "game": row.get("game"),
            "currency": row.get("currency"),
            "bet": row.get("bet"),
            "payout": row.get("payout"),
            "net": row.get("net"),
            "created_at": row.get("created_at"),
            "multiplier": (row.get("details") or {}).get("cashout"),
        })
    return {"success": True, "feed": feed}


def get_activity_stats(days: int = 5, currency: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_ledger

    cur = _normalize_currency(currency) if currency else None
    safe_days = max(1, min(int(days or 5), 30))
    daily = casino_ledger.daily_stats(days=safe_days, currency=cur)
    tournament_joins = 0
    try:
        tpath = os.path.join(_ROOT, "logs", "casino_tournament_ledger.jsonl")
        if os.path.isfile(tpath):
            from datetime import datetime, timedelta, timezone
            cutoff = (datetime.now(timezone.utc) - timedelta(days=safe_days - 1)).strftime("%Y-%m-%d")
            with open(tpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if str(row.get("type") or "") != "buyin":
                        continue
                    created = str(row.get("created_at") or "")[:10]
                    if created >= cutoff:
                        tournament_joins += 1
    except OSError:
        pass
    return {
        "success": True,
        "days": safe_days,
        "currency": cur or "all",
        "daily": daily,
        "tournament_joins": tournament_joins,
    }


def get_casino_social_preferences(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_social_service

    prefs = casino_social_service.get_preferences(user_id)
    links = casino_social_service.get_social_links()
    discord = links.get("discord") or {}
    return {
        "success": True,
        "preferences": prefs,
        "share_ok": casino_social_service.may_share_win(user_id),
        "discord_earn_href": discord.get("discord_play_path") or "/discord-play/",
        "discord_invite_url": discord.get("invite_url"),
        "discord_earn_coins": discord.get("earn_coins_join") or 0,
    }


def set_casino_social_preferences(
    user_id: str,
    *,
    share_wins: Optional[bool] = None,
    country_code: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services import casino_social_service

    return casino_social_service.set_preferences(
        user_id,
        share_wins=share_wins,
        country_code=country_code,
    )


def get_jackpots() -> Dict[str, Any]:
    from backend.services import casino_jackpot
    return casino_jackpot.public_pools()


def reconcile_jackpots() -> Dict[str, Any]:
    from backend.services import casino_jackpot
    return casino_jackpot.reconcile()


# ---------------------------------------------------------------------------
# Plinko — single-call drop (provably fair, config-driven payout table)
# ---------------------------------------------------------------------------

def _plinko_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("plinko") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    tables = game.get("risk_tables") if isinstance(game.get("risk_tables"), dict) else {}
    clean_tables: Dict[str, List[float]] = {}
    for risk, table in tables.items():
        if isinstance(table, list):
            clean_tables[str(risk).lower()] = [float(x) for x in table]
    return {
        "label": game.get("label") or "Plinko",
        "icon": game.get("icon") or "🟡",
        "rows": int(game.get("rows") or 12),
        "rtp_estimate": float(game.get("rtp_estimate") or 99.0),
        "risk_tables": clean_tables,
    }


def play_plinko(user_id: str, bet: float, risk: str = "medium", currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import plinko as plinko_engine

    currency = _normalize_currency(currency)
    conf = _plinko_config()
    risk = (risk or "medium").strip().lower()
    table = conf["risk_tables"].get(risk)
    if not table:
        return {"success": False, "error": f"risk must be one of {sorted(conf['risk_tables'].keys())}"}
    if len(table) != conf["rows"] + 1:
        return {"success": False, "error": "Plinko risk table is misconfigured"}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    res = plinko_engine.play(proof["float"], conf["rows"], table)
    multiplier = float(res["multiplier"])
    payout = _round_payout(amount * multiplier, currency)
    if payout > amount:
        outcome = "win"
    elif payout == amount:
        outcome = "draw"
    else:
        outcome = "loss"

    return _finalize_bet(
        user_id,
        "plinko",
        amount,
        outcome,
        payout,
        {
            "risk": risk,
            "rows": conf["rows"],
            "bin": res["bin"],
            "path": res["path"],
            "multiplier": multiplier,
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


def _quests_claims_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_quest_claims.json")


def _load_quest_claims() -> Dict[str, Any]:
    path = _quests_claims_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_quest_claims(data: Dict[str, Any]) -> None:
    try:
        with open(_quests_claims_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _battle_meta_config() -> Dict[str, Any]:
    cfg = _load_config()
    meta = cfg.get("battle_meta") if isinstance(cfg.get("battle_meta"), dict) else {}
    return {
        "window_hours": int(meta.get("window_hours") or 24),
        "max_events": int(meta.get("max_events") or 50),
        "rarity_base_multiplier": float(meta.get("rarity_base_multiplier") or 2.0),
        "rarity_min_multiplier": float(meta.get("rarity_min_multiplier") or 1.8),
        "rarity_max_multiplier": float(meta.get("rarity_max_multiplier") or 3.5),
        "difficulty_lanes": meta.get("difficulty_lanes") or ["easy", "balanced", "hard"],
    }


def _quest_streak_config() -> Dict[str, int]:
    cfg = _load_config()
    streaks = cfg.get("quest_streaks") if isinstance(cfg.get("quest_streaks"), dict) else {}
    return {
        "daily_all_claimed_bonus": int(streaks.get("daily_all_claimed_bonus") or 10),
        "streak_3_day_bonus": int(streaks.get("streak_3_day_bonus") or 25),
        "streak_days_required": int(streaks.get("streak_days_required") or 3),
    }


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _collect_battle_telemetry(
    *,
    battle_modes: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
    player_move: Optional[str] = None,
    require_opponent_move: bool = False,
    require_result: bool = False,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    allowed_modes = {m.lower() for m in battle_modes} if battle_modes else None
    lane = (difficulty or "").strip().lower() or None
    if lane and lane not in ("easy", "balanced", "hard"):
        lane = None
    ctx_move = (player_move or "").strip().lower() or None
    if ctx_move and ctx_move not in _RPS_MOVES:
        ctx_move = None
    try:
        if not os.path.isfile(_BATTLE_V2_PATH):
            return events
        with open(_BATTLE_V2_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for user_state in (data.get("users") or {}).values():
            if not isinstance(user_state, dict):
                continue
            for row in user_state.get("telemetry") or []:
                if not isinstance(row, dict):
                    continue
                mode = str(row.get("battle_mode") or "").strip().lower()
                if allowed_modes and mode not in allowed_modes:
                    continue
                if lane and str(row.get("difficulty") or "").strip().lower() != lane:
                    continue
                if ctx_move and str(row.get("player_move") or "").strip().lower() != ctx_move:
                    continue
                if require_opponent_move:
                    move = str(row.get("opponent_move") or "").strip().lower()
                    if move not in _RPS_MOVES:
                        continue
                if require_result:
                    result = str(row.get("result") or "").strip().lower()
                    if result not in ("win", "draw", "loss"):
                        continue
                events.append(row)
    except Exception:
        return events
    events.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return events


def _collect_battle_rps_events() -> List[Dict[str, Any]]:
    return _collect_battle_telemetry(battle_modes=["rps"], require_opponent_move=True)


def _select_battle_window(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    meta = _battle_meta_config()
    cutoff = _utcnow() - timedelta(hours=meta["window_hours"])
    selected: List[Dict[str, Any]] = []
    for row in events:
        created = _parse_iso(str(row.get("created_at") or ""))
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and created < cutoff:
            continue
        selected.append(row)
        if len(selected) >= meta["max_events"]:
            break
    return selected


def _rarity_multipliers(percentages: Dict[str, float]) -> Dict[str, float]:
    meta = _battle_meta_config()
    mults: Dict[str, float] = {}
    for move in _RPS_MOVES:
        pct = max(float(percentages.get(move) or 0), 0.01)
        raw = meta["rarity_base_multiplier"] / pct
        mults[move] = round(
            min(max(raw, meta["rarity_min_multiplier"]), meta["rarity_max_multiplier"]),
            2,
        )
    return mults


def _claimed_quest_ids(user_id: str) -> set:
    today = _today_key()
    data = _load_quest_claims()
    user_day = (data.get(user_id) or {}).get(today) or []
    return set(user_day) if isinstance(user_day, list) else set()


def _bonus_claimed_today(user_id: str, bonus_id: str) -> bool:
    data = _load_quest_claims()
    bonus_day = ((data.get(user_id) or {}).get("_bonus") or {}).get(_today_key()) or []
    return bonus_id in bonus_day if isinstance(bonus_day, list) else False


def _mark_bonus_claimed(user_id: str, bonus_id: str) -> None:
    data = _load_quest_claims()
    user_map = data.setdefault(user_id, {})
    bonus_map = user_map.setdefault("_bonus", {})
    today_bonus = bonus_map.setdefault(_today_key(), [])
    if bonus_id not in today_bonus:
        today_bonus.append(bonus_id)
    _save_quest_claims(data)


def _all_daily_quests_claimed(user_id: str) -> bool:
    defs = [q for q in _daily_quest_defs() if isinstance(q, dict) and q.get("id")]
    if not defs:
        return False
    claimed = _claimed_quest_ids(user_id)
    return all(str(q["id"]) in claimed for q in defs)


def _consecutive_all_claimed_days(user_id: str) -> int:
    data = _load_quest_claims()
    user_map = data.get(user_id) or {}
    required = len([q for q in _daily_quest_defs() if isinstance(q, dict) and q.get("id")])
    if required <= 0:
        return 0
    streak = 0
    day = _utcnow().date()
    for offset in range(30):
        key = (day - timedelta(days=offset)).strftime("%Y-%m-%d")
        claimed = user_map.get(key) or []
        if isinstance(claimed, list) and len(claimed) >= required:
            streak += 1
        else:
            break
    return streak


def _streak_bonus_eligible(user_id: str) -> bool:
    cfg = _quest_streak_config()
    streak = _consecutive_all_claimed_days(user_id)
    if streak < cfg["streak_days_required"]:
        return False
    data = _load_quest_claims()
    meta = (data.get(user_id) or {}).get("_meta") or {}
    last_at = int(meta.get("streak_bonus_at") or 0)
    return streak > last_at


def _mark_streak_bonus_claimed(user_id: str) -> None:
    data = _load_quest_claims()
    user_map = data.setdefault(user_id, {})
    meta = user_map.setdefault("_meta", {})
    meta["streak_bonus_at"] = _consecutive_all_claimed_days(user_id)
    _save_quest_claims(data)


def _quest_bonuses(user_id: str) -> List[Dict[str, Any]]:
    cfg = _quest_streak_config()
    streak = _consecutive_all_claimed_days(user_id)
    all_claimed = _all_daily_quests_claimed(user_id)
    return [
        {
            "id": "bonus_daily_all",
            "title": "Daily sweep",
            "description": "Claim all daily quests today",
            "reward_coins": cfg["daily_all_claimed_bonus"],
            "eligible": all_claimed,
            "claimed": _bonus_claimed_today(user_id, "bonus_daily_all"),
            "streak_days": streak,
        },
        {
            "id": "bonus_streak_3",
            "title": "Quest streak",
            "description": f"Claim all dailies {cfg['streak_days_required']} days in a row",
            "reward_coins": cfg["streak_3_day_bonus"],
            "eligible": _streak_bonus_eligible(user_id),
            "claimed": _bonus_claimed_today(user_id, "bonus_streak_3"),
            "streak_days": streak,
            "streak_required": cfg["streak_days_required"],
        },
    ]


def _mark_quest_claimed(user_id: str, quest_id: str) -> None:
    today = _today_key()
    data = _load_quest_claims()
    user_map = data.setdefault(user_id, {})
    claimed = user_map.setdefault(today, [])
    if quest_id not in claimed:
        claimed.append(quest_id)
    _save_quest_claims(data)


def _read_today_rows(user_id: str) -> List[Dict[str, Any]]:
    path = _ledger_path()
    if not os.path.isfile(path):
        return []
    today = _today_key()
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(row, dict)
                    and row.get("user_id") == user_id
                    and str(row.get("created_at") or "").startswith(today)
                ):
                    rows.append(row)
    except OSError:
        return []
    return rows


def _today_quest_metrics(user_id: str) -> Dict[str, int]:
    rows = _read_today_rows(user_id)
    wins = sum(1 for r in rows if r.get("outcome") == "win")
    net = sum(float(r.get("net") or 0) for r in rows)
    return {
        "bets": len(rows),
        "wins": wins,
        "net": int(net),
        "rps_distribution_bets": sum(1 for r in rows if r.get("game") == "rps_distribution"),
        "coin_flip_bets": sum(1 for r in rows if r.get("game") == "coin_flip"),
        "dice_wins": sum(1 for r in rows if r.get("game") == "dice" and r.get("outcome") == "win"),
        "scratch_bets": sum(1 for r in rows if r.get("game") == "scratch_card"),
        "rps_counter_bets": sum(1 for r in rows if r.get("game") == "rps_counter_pick"),
    }


def _rotating_quest_defs() -> List[Dict[str, Any]]:
    cfg = _load_config()
    pool = cfg.get("rotating_daily_quests")
    if not isinstance(pool, list) or not pool:
        return []
    day_index = _utcnow().weekday() % len(pool)
    entry = pool[day_index]
    if isinstance(entry, dict) and isinstance(entry.get("quests"), list):
        return [q for q in entry["quests"] if isinstance(q, dict) and q.get("id")]
    if isinstance(entry, dict) and entry.get("id"):
        return [entry]
    return []


def _all_quest_defs_for_user(user_id: str) -> List[Dict[str, Any]]:
    return _daily_quest_defs() + _rotating_quest_defs()


def _daily_quest_defs() -> List[Dict[str, Any]]:
    cfg = _load_config()
    quests = cfg.get("daily_quests")
    return quests if isinstance(quests, list) else []


def get_daily_quests(user_id: str) -> Dict[str, Any]:
    metrics = _today_quest_metrics(user_id)
    claimed = _claimed_quest_ids(user_id)
    quests_out = []
    for quest in _all_quest_defs_for_user(user_id):
        if not isinstance(quest, dict) or not quest.get("id"):
            continue
        metric = str(quest.get("metric") or "bets")
        target = int(quest.get("target") or 1)
        progress = int(metrics.get(metric, 0))
        completed = progress >= target
        quests_out.append({
            "id": quest["id"],
            "title": quest.get("title") or quest["id"],
            "description": quest.get("description") or "",
            "metric": metric,
            "target": target,
            "progress": min(progress, target),
            "reward_coins": int(quest.get("reward_coins") or 0),
            "completed": completed,
            "claimed": quest["id"] in claimed,
            "rotating": bool(quest.get("rotating")),
        })
    return {
        "success": True,
        "user_id": user_id,
        "date": _today_key(),
        "quests": quests_out,
        "rotating_quests": [q for q in quests_out if q.get("rotating")],
        "bonuses": _quest_bonuses(user_id),
        "streak_days": _consecutive_all_claimed_days(user_id),
        "weekly": get_weekly_challenge(user_id),
        "free_daily_bet": get_free_daily_bet_status(user_id),
    }


def _claim_quest_bonus(user_id: str, bonus_id: str) -> Dict[str, Any]:
    bonus_id = (bonus_id or "").strip()
    bonuses = {b["id"]: b for b in _quest_bonuses(user_id)}
    bonus = bonuses.get(bonus_id)
    if not bonus:
        return {"success": False, "error": "Unknown bonus"}
    if bonus.get("claimed"):
        return {"success": False, "error": "Bonus already claimed"}
    if not bonus.get("eligible"):
        return {"success": False, "error": "Bonus not eligible yet"}
    reward = int(bonus.get("reward_coins") or 0)
    if reward > 0:
        _apply_coin_delta(user_id, reward, "quest_bonus", {"bonus_id": bonus_id, "date": _today_key()})
    _mark_bonus_claimed(user_id, bonus_id)
    if bonus_id == "bonus_streak_3":
        _mark_streak_bonus_claimed(user_id)
    return {
        "success": True,
        "user_id": user_id,
        "bonus_id": bonus_id,
        "reward_coins": reward,
        "balance": _user_coins(user_id),
        "streak_days": _consecutive_all_claimed_days(user_id),
    }


def claim_daily_quest(user_id: str, quest_id: str) -> Dict[str, Any]:
    quest_id = (quest_id or "").strip()
    if not quest_id:
        return {"success": False, "error": "quest_id required"}
    if quest_id.startswith("bonus_"):
        return _claim_quest_bonus(user_id, quest_id)
    if quest_id == "weekly_wins" or quest_id == (_weekly_challenge_config().get("id") or "weekly_wins"):
        return claim_weekly_challenge(user_id)
    status = get_daily_quests(user_id)
    quest = next((q for q in status.get("quests", []) if q.get("id") == quest_id), None)
    if not quest:
        return {"success": False, "error": "Unknown quest"}
    if not quest.get("completed"):
        return {"success": False, "error": "Quest not completed yet"}
    if quest.get("claimed"):
        return {"success": False, "error": "Quest already claimed"}
    reward = int(quest.get("reward_coins") or 0)
    if reward > 0:
        _apply_coin_delta(user_id, reward, "quest_reward", {"quest_id": quest_id, "date": _today_key()})
    _mark_quest_claimed(user_id, quest_id)
    return {
        "success": True,
        "user_id": user_id,
        "quest_id": quest_id,
        "reward_coins": reward,
        "balance": _user_coins(user_id),
    }


def _period_start(period: str) -> Optional[str]:
    p = (period or "today").strip().lower()
    if p == "today":
        return _today_key()
    if p == "week":
        return (_utcnow() - timedelta(days=6)).strftime("%Y-%m-%d")
    return None


def _row_in_period(row: Dict[str, Any], period: str) -> bool:
    start = _period_start(period)
    if start is None:
        return True
    created = str(row.get("created_at") or "")
    if not created:
        return False
    return created[:10] >= start


def get_leaderboard(
    period: str = "today",
    limit: int = 10,
    user_id: Optional[str] = None,
    currency: str = "coins",
) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 10), 50))
    currency = _normalize_currency(currency)
    agg: Dict[str, Dict[str, float]] = defaultdict(lambda: {"net": 0.0, "bets": 0, "wins": 0, "wagered": 0.0})

    # Prefer indexed DB when available (ledger migration slice).
    try:
        from backend.services import casino_ledger
        db_rows = casino_ledger.leaderboard_aggregate(period=period, currency=currency)
        if db_rows:
            for uid, stats in db_rows.items():
                agg[uid] = stats
    except Exception:
        pass

    if not agg:
        path = _ledger_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(row, dict) or not row.get("user_id"):
                            continue
                        row_currency = _normalize_currency(row.get("currency") or "coins")
                        if row_currency != currency:
                            continue
                        if row.get("exclude_leaderboard"):
                            continue
                        if not _row_in_period(row, period):
                            continue
                        uid = str(row["user_id"])
                        agg[uid]["net"] += float(row.get("net") or 0)
                        agg[uid]["bets"] += 1
                        agg[uid]["wagered"] += float(row.get("bet") or 0)
                        if row.get("outcome") == "win":
                            agg[uid]["wins"] += 1
            except OSError:
                pass

    def _row_stats(uid: str, stats: Dict[str, float], rank: int) -> Dict[str, Any]:
        bets = int(stats["bets"])
        wins = int(stats["wins"])
        wagered = float(stats["wagered"])
        net = float(stats["net"])
        win_rate = round(100.0 * wins / bets, 1) if bets else 0.0
        roi = round(100.0 * net / wagered, 1) if wagered else 0.0
        return {
            "rank": rank,
            "user_id": uid,
            "net": round(net, 8) if currency == "mn2" else (round(net, 2) if currency == "usd" else int(net)),
            "bets": bets,
            "wins": wins,
            "wagered": round(wagered, 8) if currency == "mn2" else (round(wagered, 2) if currency == "usd" else int(wagered)),
            "win_rate": win_rate,
            "roi": roi,
            "currency": currency,
        }

    ranked = sorted(agg.items(), key=lambda item: (item[1]["net"], item[1]["wins"]), reverse=True)
    leaderboard = [_row_stats(uid, stats, rank) for rank, (uid, stats) in enumerate(ranked[:safe_limit], start=1)]

    your_rank = None
    if user_id:
        top_net = float(ranked[0][1]["net"]) if ranked else 0.0
        for rank, (uid, stats) in enumerate(ranked, start=1):
            if uid == user_id:
                row = _row_stats(uid, stats, rank)
                row["gap_to_first"] = max(0.0, top_net - float(row["net"]))
                your_rank = row
                break
        if your_rank is None and user_id in agg:
            stats = agg[user_id]
            row = _row_stats(user_id, stats, len(ranked) + 1)
            row["gap_to_first"] = max(0.0, top_net - float(row["net"]))
            your_rank = row

    return {
        "success": True,
        "period": (period or "today").strip().lower(),
        "currency": currency,
        "leaderboard": leaderboard,
        "your_rank": your_rank,
    }


def get_battle_rps_distribution(
    limit_events: Optional[int] = None,
    difficulty: Optional[str] = None,
    player_move: Optional[str] = None,
) -> Dict[str, Any]:
    meta = _battle_meta_config()
    events = _collect_battle_telemetry(
        battle_modes=["rps"],
        difficulty=difficulty,
        player_move=player_move,
        require_opponent_move=True,
    )
    if limit_events is not None:
        selected = events[: max(1, int(limit_events))]
    else:
        selected = _select_battle_window(events)
    counts = {move: 0 for move in _RPS_MOVES}
    total = 0
    for row in selected:
        move = str(row.get("opponent_move") or "").strip().lower()
        if move in counts:
            counts[move] += 1
            total += 1
    source = "battle_telemetry"
    lane = (difficulty or "").strip().lower() or None
    ctx = (player_move or "").strip().lower() or None
    if ctx and ctx in _RPS_MOVES:
        source = "dual_signal"
    if total == 0:
        counts = {move: 1 for move in _RPS_MOVES}
        total = 3
        source = "uniform_fallback"
    percentages = {move: round(counts[move] / total, 4) for move in _RPS_MOVES}
    payout_multipliers = _rarity_multipliers(percentages)
    lane_label = lane if lane in ("easy", "balanced", "hard") else "all lanes"
    signal_label = f"when players open {ctx}" if ctx in _RPS_MOVES else "all openers"
    return {
        "success": True,
        "total": total,
        "counts": counts,
        "percentages": percentages,
        "payout_multipliers": payout_multipliers,
        "source": source,
        "window_hours": meta["window_hours"],
        "max_events": meta["max_events"],
        "window_label": f"Last {meta['window_hours']}h · up to {meta['max_events']} battles",
        "difficulty": lane,
        "difficulty_label": lane_label,
        "player_move": ctx if ctx in _RPS_MOVES else None,
        "signal_label": signal_label,
        "difficulty_lanes": meta.get("difficulty_lanes") or ["easy", "balanced", "hard"],
    }


def _weighted_rps_move(counts: Dict[str, int]) -> str:
    total = sum(counts.get(move, 0) for move in _RPS_MOVES) or 1
    pick = random.uniform(0, total)
    cumulative = 0.0
    for move in _RPS_MOVES:
        cumulative += counts.get(move, 0)
        if pick <= cumulative:
            return move
    return random.choice(list(_RPS_MOVES))


def play_rps_distribution_bet(
    user_id: str,
    bet: float,
    prediction: str,
    difficulty: Optional[str] = None,
    player_move: Optional[str] = None,
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("rps_distribution") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or list(_RPS_MOVES))]
    pick = (prediction or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"prediction must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    distribution = get_battle_rps_distribution(difficulty=difficulty, player_move=player_move)
    actual = _weighted_rps_move(distribution.get("counts") or {})
    mults = distribution.get("payout_multipliers") or {}
    base_mult = float(game_cfg.get("payout_multiplier") or 2.2)
    multiplier = float(mults.get(pick) or base_mult)
    if pick == actual:
        outcome = "win"
        payout = _round_payout(amount * multiplier, currency)
    else:
        outcome = "loss"
        payout = 0
    return _finalize_bet(
        user_id,
        "rps_distribution",
        amount,
        outcome,
        payout,
        {
            "prediction": pick,
            "actual": actual,
            "multiplier": multiplier,
            "distribution": distribution.get("percentages") or {},
            "payout_multipliers": mults,
            "distribution_source": distribution.get("source"),
            "window_label": distribution.get("window_label"),
            "difficulty": distribution.get("difficulty"),
            "player_move": distribution.get("player_move"),
            "signal_label": distribution.get("signal_label"),
        },
        currency=currency,
    )


def _week_key(dt: Optional[datetime] = None) -> str:
    dt = dt or _utcnow()
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _weekly_challenge_config() -> Dict[str, Any]:
    cfg = _load_config()
    wc = cfg.get("weekly_challenge") if isinstance(cfg.get("weekly_challenge"), dict) else {}
    return {
        "id": str(wc.get("id") or "weekly_wins"),
        "title": wc.get("title") or "Weekly grinder",
        "description": wc.get("description") or "Win casino games this week",
        "metric": str(wc.get("metric") or "wins"),
        "target": int(wc.get("target") or 15),
        "reward_coins": int(wc.get("reward_coins") or 50),
        "badge": wc.get("badge") or "weekly_grinder",
    }


def _free_bet_config() -> Dict[str, Any]:
    cfg = _load_config()
    fb = cfg.get("free_daily_bet") if isinstance(cfg.get("free_daily_bet"), dict) else {}
    return {
        "coins": int(fb.get("coins") or 5),
        "payout_multiplier": float(fb.get("payout_multiplier") or 1.9),
    }


def _double_config() -> Dict[str, int]:
    cfg = _load_config()
    dbl = cfg.get("double_or_nothing") if isinstance(cfg.get("double_or_nothing"), dict) else {}
    return {"max_steps": int(dbl.get("max_steps") or 3)}


def _row_iso_week(row: Dict[str, Any]) -> Optional[str]:
    dt = _parse_iso(str(row.get("created_at") or ""))
    if not dt:
        return None
    return _week_key(dt)


def _read_user_ledger(user_id: str) -> List[Dict[str, Any]]:
    path = _ledger_path()
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("user_id") == user_id:
                    rows.append(row)
    except OSError:
        return []
    return rows


def _ledger_row_by_id(bet_id: str) -> Optional[Dict[str, Any]]:
    if not bet_id:
        return None
    path = _ledger_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("bet_id") == bet_id:
                    return row
    except OSError:
        return None
    return None


def _has_child_double(bet_id: str) -> bool:
    path = _ledger_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    row = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("parent_bet_id") == bet_id:
                    return True
    except OSError:
        return False
    return False


def _double_offer(row: Dict[str, Any]) -> Dict[str, Any]:
    max_steps = _double_config()["max_steps"]
    if row.get("outcome") != "win":
        return {"can_double": False, "double_step": int(row.get("double_step") or 0)}
    if row.get("exclude_leaderboard"):
        return {"can_double": False, "double_step": 0}
    if int(row.get("payout") or 0) <= 0:
        return {"can_double": False, "double_step": int(row.get("double_step") or 0)}
    if _has_child_double(row.get("bet_id") or ""):
        return {"can_double": False, "double_step": int(row.get("double_step") or 0)}
    step = int(row.get("double_step") or 0)
    if row.get("game") != "double_or_nothing":
        next_step = 1
    else:
        next_step = step + 1
    can = next_step <= max_steps
    return {
        "can_double": can,
        "double_step": step,
        "double_stake": int(row.get("payout") or 0) if can else 0,
        "double_steps_remaining": max(0, max_steps - step) if row.get("game") != "double_or_nothing" else max(0, max_steps - next_step + 1),
    }


def _weekly_claimed(user_id: str) -> bool:
    data = _load_quest_claims()
    week = _week_key()
    claimed = ((data.get(user_id) or {}).get("_weekly") or {}).get(week)
    return bool(claimed)


def _mark_weekly_claimed(user_id: str) -> None:
    data = _load_quest_claims()
    user_map = data.setdefault(user_id, {})
    weekly = user_map.setdefault("_weekly", {})
    weekly[_week_key()] = True
    _save_quest_claims(data)


def _free_bet_used_today(user_id: str) -> bool:
    data = _load_quest_claims()
    return bool(((data.get(user_id) or {}).get("_free_bet") or {}).get(_today_key()))


def _mark_free_bet_used(user_id: str) -> None:
    data = _load_quest_claims()
    user_map = data.setdefault(user_id, {})
    free = user_map.setdefault("_free_bet", {})
    free[_today_key()] = True
    _save_quest_claims(data)


def _week_metrics(user_id: str) -> Dict[str, int]:
    week = _week_key()
    rows = [r for r in _read_user_ledger(user_id) if _row_iso_week(r) == week]
    wins = sum(1 for r in rows if r.get("outcome") == "win")
    bets = len(rows)
    net = sum(int(r.get("net") or 0) for r in rows)
    return {"bets": bets, "wins": wins, "net": net}


def get_weekly_challenge(user_id: str) -> Dict[str, Any]:
    wc = _weekly_challenge_config()
    metrics = _week_metrics(user_id)
    metric = wc["metric"]
    progress = int(metrics.get(metric, 0))
    target = wc["target"]
    return {
        "id": wc["id"],
        "title": wc["title"],
        "description": wc["description"],
        "metric": metric,
        "target": target,
        "progress": min(progress, target),
        "reward_coins": wc["reward_coins"],
        "badge": wc["badge"],
        "week": _week_key(),
        "completed": progress >= target,
        "claimed": _weekly_claimed(user_id),
    }


def claim_weekly_challenge(user_id: str) -> Dict[str, Any]:
    status = get_weekly_challenge(user_id)
    if not status.get("completed"):
        return {"success": False, "error": "Weekly challenge not completed yet"}
    if status.get("claimed"):
        return {"success": False, "error": "Weekly challenge already claimed"}
    reward = int(status.get("reward_coins") or 0)
    if reward > 0:
        _apply_coin_delta(user_id, reward, "weekly_challenge", {"week": _week_key(), "badge": status.get("badge")})
    _mark_weekly_claimed(user_id)
    return {
        "success": True,
        "user_id": user_id,
        "quest_id": status["id"],
        "reward_coins": reward,
        "badge": status.get("badge"),
        "balance": _user_coins(user_id),
    }


def get_free_daily_bet_status(user_id: str) -> Dict[str, Any]:
    fb = _free_bet_config()
    used = _free_bet_used_today(user_id)
    return {
        "available": not used,
        "used_today": used,
        "coins": fb["coins"],
        "payout_multiplier": fb["payout_multiplier"],
    }


def play_free_daily_bet(user_id: str, choice: str) -> Dict[str, Any]:
    if _free_bet_used_today(user_id):
        return {"success": False, "error": "Free daily bet already used today"}
    fb = _free_bet_config()
    pick = (choice or "").strip().lower()
    if pick not in ("heads", "tails"):
        return {"success": False, "error": "choice must be heads or tails"}
    amount = fb["coins"]
    result = random.choice(["heads", "tails"])
    multiplier = fb["payout_multiplier"]
    payout = int(round(amount * multiplier)) if result == pick else 0
    outcome = "win" if payout > 0 else "loss"
    _mark_free_bet_used(user_id)
    return _finalize_bet(
        user_id,
        "free_daily_bet",
        amount,
        outcome,
        payout,
        {"choice": pick, "result": result, "multiplier": multiplier, "free_bet": True},
        skip_stake=True,
        exclude_leaderboard=True,
    )


def play_double_or_nothing(user_id: str, bet_id: str) -> Dict[str, Any]:
    bet_id = (bet_id or "").strip()
    parent = _ledger_row_by_id(bet_id)
    if not parent or parent.get("user_id") != user_id:
        return {"success": False, "error": "Bet not found"}
    if parent.get("outcome") != "win":
        return {"success": False, "error": "Only winning bets can be doubled"}
    if _has_child_double(bet_id):
        return {"success": False, "error": "Already doubled this win"}
    offer = _double_offer(parent)
    if not offer.get("can_double"):
        return {"success": False, "error": "Double-or-nothing not available"}
    currency = _normalize_currency(parent.get("currency") or "coins")
    stake = float(parent.get("payout") or 0)
    if stake <= 0 or _user_balance(user_id, currency) < stake:
        return {"success": False, "error": f"Insufficient {_currency_label(currency)} to double"}
    parent_step = int(parent.get("double_step") or 0)
    next_step = parent_step + 1 if parent.get("game") == "double_or_nothing" else 1
    win = random.random() < 0.5
    payout = _round_payout(stake * 2, currency) if win else 0
    outcome = "win" if win else "loss"
    return _finalize_bet(
        user_id,
        "double_or_nothing",
        stake,
        outcome,
        payout,
        {"parent_bet_id": bet_id, "step": next_step},
        parent_bet_id=bet_id,
        double_step=next_step,
        currency=currency,
    )


def get_personal_bests(user_id: str) -> Dict[str, Any]:
    rows = _read_user_ledger(user_id)
    if not rows:
        return {
            "success": True,
            "user_id": user_id,
            "best_day_net": 0,
            "longest_win_streak": 0,
            "biggest_single_win": 0,
            "total_bets": 0,
        }
    day_net: Dict[str, int] = defaultdict(int)
    biggest = 0
    for row in rows:
        day = str(row.get("created_at") or "")[:10]
        if day:
            day_net[day] += int(row.get("net") or 0)
        if row.get("outcome") == "win":
            biggest = max(biggest, int(row.get("payout") or 0))
    longest = 0
    current = 0
    for row in rows:
        if row.get("outcome") == "win":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {
        "success": True,
        "user_id": user_id,
        "best_day_net": max(day_net.values()) if day_net else 0,
        "best_day": max(day_net.items(), key=lambda x: x[1])[0] if day_net else None,
        "longest_win_streak": longest,
        "biggest_single_win": biggest,
        "total_bets": len(rows),
    }


def _hall_of_fame_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_hall_of_fame.json")


def _load_hall_of_fame() -> Dict[str, Any]:
    path = _hall_of_fame_path()
    if not os.path.isfile(path):
        return {"weeks": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("weeks", {})
            return data
    except Exception:
        pass
    return {"weeks": {}}


def _save_hall_of_fame(data: Dict[str, Any]) -> None:
    try:
        with open(_hall_of_fame_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _leaderboard_for_iso_week(week_key: str, limit: int = 10) -> List[Dict[str, Any]]:
    path = _ledger_path()
    agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"net": 0, "wins": 0, "bets": 0})
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        row = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict) or not row.get("user_id"):
                        continue
                    if row.get("exclude_leaderboard"):
                        continue
                    if _row_iso_week(row) != week_key:
                        continue
                    uid = str(row["user_id"])
                    agg[uid]["net"] += int(row.get("net") or 0)
                    agg[uid]["bets"] += 1
                    if row.get("outcome") == "win":
                        agg[uid]["wins"] += 1
        except OSError:
            pass
    ranked = sorted(agg.items(), key=lambda item: (item[1]["net"], item[1]["wins"]), reverse=True)
    out = []
    for rank, (uid, stats) in enumerate(ranked[:limit], start=1):
        out.append({"rank": rank, "user_id": uid, "net": stats["net"], "wins": stats["wins"], "bets": stats["bets"]})
    return out


def _maybe_snapshot_hall_of_fame() -> None:
    data = _load_hall_of_fame()
    weeks = data.setdefault("weeks", {})
    now = _utcnow()
    prev_week = _week_key(now - timedelta(days=7))
    if prev_week in weeks:
        return
    snapshot = _leaderboard_for_iso_week(prev_week, limit=10)
    if not snapshot:
        return
    weeks[prev_week] = {
        "snapshotted_at": _iso(),
        "leaderboard": snapshot,
    }
    _save_hall_of_fame(data)


def get_hall_of_fame(limit: int = 3) -> Dict[str, Any]:
    _maybe_snapshot_hall_of_fame()
    data = _load_hall_of_fame()
    weeks = data.get("weeks") or {}
    keys = sorted(weeks.keys(), reverse=True)[: max(1, min(int(limit or 3), 12))]
    entries = []
    for key in keys:
        block = weeks.get(key) or {}
        entries.append({
            "week": key,
            "snapshotted_at": block.get("snapshotted_at"),
            "leaderboard": block.get("leaderboard") or [],
        })
    return {"success": True, "weeks": entries}


def get_big_win_hall_of_fame(days: int = 7, limit: int = 15, currency: Optional[str] = None) -> Dict[str, Any]:
    """Top payout multipliers from the ledger mirror (last N days)."""
    from backend.services import casino_ledger

    rows = casino_ledger.top_big_wins(days=days, limit=limit, currency=currency)
    feed = []
    for idx, row in enumerate(rows, start=1):
        feed.append({
            "rank": idx,
            "user_id": row.get("user_id"),
            "game": row.get("game"),
            "currency": row.get("currency"),
            "bet": row.get("bet"),
            "payout": row.get("payout"),
            "net": row.get("net"),
            "multiplier": row.get("multiplier"),
            "created_at": row.get("created_at"),
        })
    return {
        "success": True,
        "days": max(1, min(int(days or 7), 30)),
        "wins": feed,
        "count": len(feed),
    }


def get_slot_of_the_day() -> Dict[str, Any]:
    """Featured rotating slot — deterministic daily pick from configured machines."""
    from datetime import datetime, timezone

    cfg = _load_config()
    sod = cfg.get("slot_of_the_day") if isinstance(cfg.get("slot_of_the_day"), dict) else {}
    if sod.get("enabled") is False:
        return {"success": True, "enabled": False, "slot": None}

    machines = list_slot_machines().get("slots") or []
    if not machines:
        return {"success": True, "enabled": True, "slot": None, "message": "No slots configured"}

    override_id = (sod.get("slot_id") or "").strip()
    rotate = sod.get("rotate_daily", True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    picked = None
    if override_id and not rotate:
        picked = next((m for m in machines if m.get("id") == override_id), None)
        if not picked:
            return {"success": True, "enabled": True, "slot": None, "error": "slot_id not found"}
    else:
        idx = sum(ord(c) for c in day) % len(machines)
        picked = machines[idx]

    games = (cfg.get("games") or {})
    game_cfg = games.get(picked["id"]) if isinstance(games, dict) else {}
    return {
        "success": True,
        "enabled": True,
        "day": day,
        "badge_label": sod.get("badge_label") or "Slot of the Day",
        "slot": {
            **picked,
            "blurb": (game_cfg or {}).get("blurb") or f"Today's featured machine — {picked.get('label')}",
        },
    }


def get_seasonal_slots() -> Dict[str, Any]:
    """Active seasonal slot overlays from casino_config — limited-time reskins only."""
    from datetime import datetime, timezone

    cfg = _load_config()
    seasonal = cfg.get("seasonal_overlays") if isinstance(cfg.get("seasonal_overlays"), dict) else {}
    if seasonal.get("enabled") is False:
        return {"success": True, "enabled": False, "active_windows": [], "slots": []}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    windows_cfg = seasonal.get("windows") if isinstance(seasonal.get("windows"), list) else []
    machines = {m["id"]: m for m in (list_slot_machines().get("slots") or []) if m.get("id")}
    active_windows: List[Dict[str, Any]] = []
    merged_slots: Dict[str, Dict[str, Any]] = {}

    for win in windows_cfg:
        if not isinstance(win, dict):
            continue
        start = str(win.get("starts_at") or "")[:10]
        end = str(win.get("ends_at") or "")[:10]
        if start and today < start:
            continue
        if end and today > end:
            continue
        overlays = win.get("overlays") if isinstance(win.get("overlays"), dict) else {}
        if not overlays:
            continue
        active_windows.append({
            "id": win.get("id"),
            "label": win.get("label"),
            "starts_at": start,
            "ends_at": end,
        })
        for slot_id, overlay in overlays.items():
            if not isinstance(overlay, dict):
                continue
            base = machines.get(slot_id) or {"id": slot_id, "label": slot_id, "icon": "🎰"}
            existing = merged_slots.get(slot_id) or dict(base)
            label = (base.get("label") or slot_id) + str(overlay.get("label_suffix") or "")
            merged_slots[slot_id] = {
                **existing,
                "id": slot_id,
                "label": label.strip(),
                "icon": overlay.get("icon") or existing.get("icon") or "🎰",
                "theme_color": overlay.get("theme_color") or existing.get("theme_color"),
                "accent": overlay.get("accent") or existing.get("accent"),
                "glow_color": overlay.get("glow_color") or existing.get("glow_color"),
                "seasonal": True,
                "seasonal_window": win.get("id"),
                "seasonal_label": win.get("label"),
            }

    return {
        "success": True,
        "enabled": True,
        "badge_label": seasonal.get("badge_label") or "Seasonal",
        "day": today,
        "active_windows": active_windows,
        "slots": list(merged_slots.values()),
        "count": len(merged_slots),
    }


def get_vip_lounge(user_id: str) -> Dict[str, Any]:
    """VIP lounge state — gated by XP threshold; cosmetic frames + daily wheel link only."""
    from backend.services import casino_progression

    cfg = _load_config()
    lounge = cfg.get("vip_lounge") if isinstance(cfg.get("vip_lounge"), dict) else {}
    if lounge.get("enabled") is False:
        return {"success": True, "enabled": False, "unlocked": False}

    min_xp = float(lounge.get("min_xp") or 5000)
    profile = casino_progression.get_profile(user_id)
    xp_block = profile.get("xp") if isinstance(profile.get("xp"), dict) else {}
    user_xp = float(xp_block.get("xp") or 0)
    unlocked = user_xp >= min_xp
    frames = lounge.get("frame_previews") if isinstance(lounge.get("frame_previews"), list) else []
    wheel_spun = bool(profile.get("daily_wheel_spun_today"))

    return {
        "success": True,
        "enabled": True,
        "user_id": user_id,
        "unlocked": unlocked,
        "min_xp": min_xp,
        "user_xp": round(user_xp, 2),
        "xp_to_unlock": max(0, round(min_xp - user_xp, 2)),
        "level": xp_block.get("level"),
        "level_title": xp_block.get("title"),
        "vip_tier": profile.get("vip"),
        "title": lounge.get("title") or "VIP Lounge",
        "subtitle": lounge.get("subtitle") or "Cosmetic perks only — house edge unchanged.",
        "frame_previews": frames if unlocked else [],
        "frame_previews_locked": [] if unlocked else frames[:2],
        "daily_wheel": {
            "href": lounge.get("daily_wheel_href") or "/casino/?tab=home",
            "available": unlocked and not wheel_spun,
            "spun_today": wheel_spun,
            "note": "Same wheel odds for all players — VIP unlocks lounge access only.",
        },
        "shop_frames_href": lounge.get("shop_frames_href") or "/casino/?tab=compete",
        "note": "No RTP or house-edge perks from VIP lounge.",
    }


def export_fairness_audit(user_id: str, limit: int = 100) -> Dict[str, Any]:
    """Build provably-fair audit rows for CSV export."""
    from backend.services import casino_ledger

    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = casino_ledger.user_bets_for_export(uid, limit=safe_limit)
    audit_rows: List[Dict[str, Any]] = []
    for row in rows:
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        fairness = details.get("fairness") if isinstance(details.get("fairness"), dict) else {}
        if not fairness and isinstance(details, dict):
            fairness = {
                k: details[k]
                for k in ("server_seed_hash", "client_seed", "nonce", "server_seed")
                if k in details
            }
        audit_rows.append({
            "bet_id": row.get("bet_id"),
            "created_at": row.get("created_at"),
            "game": row.get("game"),
            "currency": row.get("currency"),
            "bet": row.get("bet"),
            "payout": row.get("payout"),
            "net": row.get("net"),
            "outcome": row.get("outcome"),
            "server_seed_hash": fairness.get("server_seed_hash") or "",
            "server_seed": fairness.get("server_seed") or "",
            "client_seed": fairness.get("client_seed") or "",
            "nonce": fairness.get("nonce"),
        })
    return {
        "success": True,
        "user_id": uid,
        "count": len(audit_rows),
        "rows": audit_rows,
    }


def fairness_audit_csv(user_id: str, limit: int = 100) -> str:
    """CSV string for provably-fair audit download."""
    import csv
    import io

    payload = export_fairness_audit(user_id, limit=limit)
    if not payload.get("success"):
        return "error,user_id required\n"
    buf = io.StringIO()
    fields = [
        "bet_id", "created_at", "game", "currency", "bet", "payout", "net", "outcome",
        "server_seed_hash", "server_seed", "client_seed", "nonce",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in payload.get("rows") or []:
        writer.writerow(row)
    return buf.getvalue()


_BATTLE_OUTCOMES = ("win", "draw", "loss")


def _outcome_rarity_multipliers(percentages: Dict[str, float]) -> Dict[str, float]:
    meta = _battle_meta_config()
    mults: Dict[str, float] = {}
    for outcome in _BATTLE_OUTCOMES:
        pct = max(float(percentages.get(outcome) or 0), 0.01)
        raw = meta["rarity_base_multiplier"] / pct
        mults[outcome] = round(
            min(max(raw, meta["rarity_min_multiplier"]), meta["rarity_max_multiplier"]),
            2,
        )
    return mults


def get_battle_outcome_distribution(difficulty: Optional[str] = None) -> Dict[str, Any]:
    meta = _battle_meta_config()
    events = _collect_battle_telemetry(require_result=True, difficulty=difficulty)
    selected = _select_battle_window(events)
    counts = {outcome: 0 for outcome in _BATTLE_OUTCOMES}
    total = 0
    for row in selected:
        result = str(row.get("result") or "").strip().lower()
        if result in counts:
            counts[result] += 1
            total += 1
    source = "battle_telemetry"
    lane = (difficulty or "").strip().lower() or None
    if total == 0:
        counts = {outcome: 1 for outcome in _BATTLE_OUTCOMES}
        total = 3
        source = "uniform_fallback"
    percentages = {outcome: round(counts[outcome] / total, 4) for outcome in _BATTLE_OUTCOMES}
    cfg = _load_config()
    game_cfg = (cfg.get("games") or {}).get("battle_outcome") or {}
    base_mults = game_cfg.get("payout_multipliers") if isinstance(game_cfg.get("payout_multipliers"), dict) else {}
    rarity_mults = _outcome_rarity_multipliers(percentages)
    payout_multipliers = {}
    for outcome in _BATTLE_OUTCOMES:
        payout_multipliers[outcome] = float(base_mults.get(outcome) or rarity_mults[outcome])
    lane_label = lane if lane in ("easy", "balanced", "hard") else "all lanes"
    return {
        "success": True,
        "total": total,
        "counts": counts,
        "percentages": percentages,
        "payout_multipliers": payout_multipliers,
        "source": source,
        "window_hours": meta["window_hours"],
        "max_events": meta["max_events"],
        "window_label": f"Last {meta['window_hours']}h · up to {meta['max_events']} battles",
        "difficulty": lane,
        "difficulty_label": lane_label,
        "difficulty_lanes": meta.get("difficulty_lanes") or ["easy", "balanced", "hard"],
    }


def _weighted_outcome_pick(counts: Dict[str, int]) -> str:
    total = sum(counts.get(outcome, 0) for outcome in _BATTLE_OUTCOMES) or 1
    pick = random.uniform(0, total)
    cumulative = 0.0
    for outcome in _BATTLE_OUTCOMES:
        cumulative += counts.get(outcome, 0)
        if pick <= cumulative:
            return outcome
    return random.choice(list(_BATTLE_OUTCOMES))


def play_battle_outcome_bet(
    user_id: str,
    bet: float,
    prediction: str,
    difficulty: Optional[str] = None,
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("battle_outcome") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or list(_BATTLE_OUTCOMES))]
    pick = (prediction or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"prediction must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    distribution = get_battle_outcome_distribution(difficulty=difficulty)
    actual = _weighted_outcome_pick(distribution.get("counts") or {})
    mults = distribution.get("payout_multipliers") or {}
    multiplier = float(mults.get(pick) or 2.0)
    if pick == actual:
        outcome = "win"
        payout = _round_payout(amount * multiplier, currency)
    else:
        outcome = "loss"
        payout = 0
    return _finalize_bet(
        user_id,
        "battle_outcome",
        amount,
        outcome,
        payout,
        {
            "prediction": pick,
            "actual": actual,
            "multiplier": multiplier,
            "distribution": distribution.get("percentages") or {},
            "difficulty": distribution.get("difficulty"),
            "window_label": distribution.get("window_label"),
        },
        currency=currency,
    )


def play_mystery_coin_flip(user_id: str, bet: float, choice: str, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("mystery_coin_flip") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or ["heads", "tails"])]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    min_mult = float(game_cfg.get("min_multiplier") or 1.5)
    max_mult = float(game_cfg.get("max_multiplier") or 3.0)
    if min_mult > max_mult:
        min_mult, max_mult = max_mult, min_mult
    multiplier = round(random.uniform(min_mult, max_mult), 1)
    result = random.choice(allowed)
    payout = _round_payout(amount * multiplier, currency) if result == pick else 0
    outcome = "win" if payout > 0 else "loss"
    return _finalize_bet(
        user_id,
        "mystery_coin_flip",
        amount,
        outcome,
        payout,
        {"choice": pick, "result": result, "multiplier": multiplier},
        currency=currency,
    )


def play_scratch_card(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("scratch_card") or {}
    symbols = [str(s) for s in (game_cfg.get("symbols") or ["7", "star", "gem", "coin", "bell"])]
    if len(symbols) < 2:
        symbols = ["7", "star", "gem"]
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    tiles = [random.choice(symbols) for _ in range(3)]
    match_2 = float(game_cfg.get("match_2_multiplier") or 1.5)
    match_3 = float(game_cfg.get("match_3_multiplier") or 8.0)
    counts: Dict[str, int] = defaultdict(int)
    for tile in tiles:
        counts[tile] += 1
    best_match = max(counts.values()) if counts else 0
    if best_match >= 3:
        payout = _round_payout(amount * match_3, currency)
        outcome = "win"
        match_label = "3-match"
    elif best_match >= 2:
        payout = _round_payout(amount * match_2, currency)
        outcome = "win"
        match_label = "2-match"
    else:
        payout = 0
        outcome = "loss"
        match_label = "no-match"
    return _finalize_bet(
        user_id,
        "scratch_card",
        amount,
        outcome,
        payout,
        {
            "tiles": tiles,
            "best_match": best_match,
            "match_label": match_label,
            "match_2_multiplier": match_2,
            "match_3_multiplier": match_3,
        },
        currency=currency,
    )


_RPS_COUNTERS = {"rock": "paper", "paper": "scissors", "scissors": "rock"}


def get_counter_pick_hint(
    difficulty: Optional[str] = None,
    player_move: Optional[str] = None,
) -> Dict[str, Any]:
    distribution = get_battle_rps_distribution(difficulty=difficulty, player_move=player_move)
    counts = distribution.get("counts") or {}
    common_move = max(_RPS_MOVES, key=lambda move: counts.get(move, 0))
    counter_move = _RPS_COUNTERS[common_move]
    total = max(int(distribution.get("total") or 0), 1)
    common_pct = round(100.0 * counts.get(common_move, 0) / total, 1)
    return {
        "success": True,
        "common_opener": common_move,
        "common_opener_pct": common_pct,
        "counter_pick": counter_move,
        "hint": f"Most common AI opener is {common_move} ({common_pct}%). {counter_move.title()} beats it.",
        "distribution": distribution,
    }


def play_rps_counter_pick(
    user_id: str,
    bet: float,
    choice: str,
    difficulty: Optional[str] = None,
    player_move: Optional[str] = None,
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("rps_counter_pick") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or list(_RPS_MOVES))]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    distribution = get_battle_rps_distribution(difficulty=difficulty, player_move=player_move)
    house_move = _weighted_rps_move(distribution.get("counts") or {})
    multiplier = float(game_cfg.get("payout_multiplier") or 2.0)
    if pick == house_move:
        outcome = "draw"
        payout = amount
    elif _RPS_BEATS.get(pick) == house_move:
        outcome = "win"
        payout = _round_payout(amount * multiplier, currency)
    else:
        outcome = "loss"
        payout = 0
    hint = get_counter_pick_hint(difficulty=difficulty, player_move=player_move)
    return _finalize_bet(
        user_id,
        "rps_counter_pick",
        amount,
        outcome,
        payout,
        {
            "choice": pick,
            "house_move": house_move,
            "multiplier": multiplier,
            "common_opener": hint.get("common_opener"),
            "counter_pick": hint.get("counter_pick"),
            "mode": "counter_pick",
        },
        currency=currency,
    )


def _load_social_data() -> Dict[str, Any]:
    if not os.path.isfile(_SOCIAL_DATA_PATH):
        return {"friends": {}, "crews": [], "user_crews": {}}
    try:
        with open(_SOCIAL_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"friends": {}, "crews": [], "user_crews": {}}
    except Exception:
        return {"friends": {}, "crews": [], "user_crews": {}}


def _social_peer_ids(user_id: str) -> List[str]:
    social = _load_social_data()
    peers = set((social.get("friends") or {}).get(user_id, []) or [])
    crew_id = (social.get("user_crews") or {}).get(user_id)
    if crew_id:
        for crew in social.get("crews") or []:
            if isinstance(crew, dict) and crew.get("id") == crew_id:
                for member in crew.get("members") or []:
                    if member:
                        peers.add(str(member))
                break
    peers.discard(user_id)
    return sorted(peers)


def get_social_mini_board(
    user_id: str,
    period: str = "today",
    limit: int = 5,
    currency: str = "coins",
) -> Dict[str, Any]:
    peers = _social_peer_ids(user_id)
    board = get_leaderboard(period=period, limit=50, currency=currency).get("leaderboard") or []
    filtered = [row for row in board if row.get("user_id") in peers][: max(1, min(int(limit or 5), 10))]
    return {
        "success": True,
        "user_id": user_id,
        "period": period,
        "currency": _normalize_currency(currency),
        "peer_count": len(peers),
        "leaderboard": filtered,
    }


def get_house_stats(user_id: str, currency: str = "coins") -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    today = _today_key()
    path = _ledger_path()
    player_net = 0.0
    games = 0
    wagered = 0.0
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        row = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    if _normalize_currency(row.get("currency") or "coins") != currency:
                        continue
                    if not str(row.get("created_at") or "").startswith(today):
                        continue
                    games += 1
                    player_net += float(row.get("net") or 0)
                    wagered += float(row.get("bet") or 0)
        except OSError:
            pass
    user_rows = _read_today_rows(user_id)
    your_net = sum(
        float(r.get("net") or 0)
        for r in user_rows
        if _normalize_currency(r.get("currency") or "coins") == currency
    )
    your_games = sum(
        1 for r in user_rows if _normalize_currency(r.get("currency") or "coins") == currency
    )
    house_net = -player_net
    return {
        "success": True,
        "date": today,
        "currency": currency,
        "your_net": round(your_net, 8) if currency == "mn2" else (round(your_net, 2) if currency == "usd" else int(your_net)),
        "your_games": your_games,
        "global_player_net": round(player_net, 8) if currency == "mn2" else (round(player_net, 2) if currency == "usd" else int(player_net)),
        "house_net": round(house_net, 8) if currency == "mn2" else (round(house_net, 2) if currency == "usd" else int(house_net)),
        "games_played": games,
        "total_wagered": round(wagered, 8) if currency == "mn2" else (round(wagered, 2) if currency == "usd" else int(wagered)),
    }


def _paypal_deposits_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_paypal_deposits.json")


def _load_paypal_deposits() -> Dict[str, Any]:
    path = _paypal_deposits_path()
    if not os.path.isfile(path):
        return {"pending": {}, "captured": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("pending", {})
            data.setdefault("captured", {})
            return data
    except Exception:
        pass
    return {"pending": {}, "captured": {}}


def _save_paypal_deposits(data: Dict[str, Any]) -> None:
    try:
        with open(_paypal_deposits_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get_paypal_deposit_packs() -> Dict[str, Any]:
    pay = _payment_config()
    packs = []
    for row in pay.get("paypal_deposit_packs") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        packs.append({
            "id": str(row["id"]),
            "label": row.get("label") or row["id"],
            "amount_usd": float(row.get("amount_usd") or 0),
        })
    return {
        "success": True,
        "enabled": _paypal_enabled(),
        "currency": pay["paypal_currency"],
        "packs": packs,
    }


def get_mn2_buyin_packs() -> Dict[str, Any]:
    """B6 — MN2-priced packs that credit casino USD play balance."""
    pay = _payment_config()
    packs = []
    for row in pay.get("mn2_buyin_packs") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        packs.append({
            "id": str(row["id"]),
            "label": row.get("label") or row["id"],
            "price_mn2": float(row.get("price_mn2") or 0),
            "casino_usd_credit": float(row.get("casino_usd_credit") or 0),
        })
    return {"success": True, "packs": packs, "rail": "mn2"}


def _mn2_buyin_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    for row in get_mn2_buyin_packs().get("packs") or []:
        if row.get("id") == pack_id:
            return row
    return None


def purchase_mn2_buyin_pack(user_id: str, pack_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    pack = _mn2_buyin_pack((pack_id or "").strip())
    if not pack:
        return {"success": False, "error": "unknown_pack"}
    price = float(pack.get("price_mn2") or 0)
    credit = float(pack.get("casino_usd_credit") or 0)
    if price <= 0 or credit <= 0:
        return {"success": False, "error": "invalid_pack"}
    try:
        from backend.services.unified_points_database import unified_points_db

        snap = unified_points_db.get_all_points(uid) or {}
        bal = float((snap.get("points") or {}).get("mn2_balance") or 0)
        if bal < price:
            return {"success": False, "error": f"Insufficient MN2. Need {price:.4f}"}
        unified_points_db.add_points(
            uid, "mn2_balance", -price, source="casino_mn2_buyin", metadata={"pack_id": pack_id}
        )
        unified_points_db.add_points(
            uid,
            "casino_fiat_balance",
            credit,
            source="casino_mn2_buyin",
            metadata={"pack_id": pack_id, "price_mn2": price},
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {
        "success": True,
        "pack_id": pack_id,
        "price_mn2": price,
        "casino_usd_credited": credit,
    }


def _deposit_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    for row in get_paypal_deposit_packs().get("packs") or []:
        if row.get("id") == pack_id:
            return row
    return None


def create_paypal_deposit_order(user_id: str, pack_id: str, base_url: str) -> Dict[str, Any]:
    if not _paypal_enabled():
        return {"success": False, "error": "PayPal casino deposits are not enabled"}
    pack = _deposit_pack((pack_id or "").strip())
    if not pack:
        return {"success": False, "error": "Unknown deposit pack"}
    amount = float(pack.get("amount_usd") or 0)
    if amount <= 0:
        return {"success": False, "error": "Invalid pack amount"}
    try:
        from backend.services.paypal_service import create_order
        import urllib.parse

        return_url = (
            f"{base_url.rstrip('/')}/casino/?paypal=success"
            f"&pack_id={urllib.parse.quote(pack['id'])}"
            f"&user_id={urllib.parse.quote(user_id)}"
        )
        cancel_url = f"{base_url.rstrip('/')}/casino/?paypal=cancel"
        result = create_order(
            amount=amount,
            currency=_payment_config()["paypal_currency"],
            item_name=pack.get("label") or "Casino USD balance",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": pack["id"], "user_id": user_id, "casino_deposit": True},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if not result.get("success"):
        return result
    order_id = result.get("order_id")
    if order_id:
        data = _load_paypal_deposits()
        data["pending"][order_id] = {
            "user_id": user_id,
            "pack_id": pack["id"],
            "amount_usd": amount,
            "created_at": _iso(),
        }
        _save_paypal_deposits(data)
    return {
        "success": True,
        "order_id": order_id,
        "approve_url": result.get("approve_url"),
        "pack_id": pack["id"],
        "amount_usd": amount,
    }


def capture_paypal_deposit(user_id: str, order_id: str, pack_id: Optional[str] = None) -> Dict[str, Any]:
    if not _paypal_enabled():
        return {"success": False, "error": "PayPal casino deposits are not enabled"}
    order_id = (order_id or "").strip()
    if not order_id:
        return {"success": False, "error": "order_id required"}
    deposits = _load_paypal_deposits()
    if order_id in deposits.get("captured", {}):
        captured = deposits["captured"][order_id]
        return {
            "success": True,
            "already_captured": True,
            "fiat_balance": _user_fiat_balance(user_id),
            "amount_usd": captured.get("amount_usd"),
        }
    pending = (deposits.get("pending") or {}).get(order_id)
    if pending and pending.get("user_id") != user_id:
        return {"success": False, "error": "Order does not belong to this user"}
    pack = _deposit_pack((pack_id or (pending or {}).get("pack_id") or "").strip())
    if not pack:
        return {"success": False, "error": "Unknown deposit pack"}
    try:
        from backend.services.paypal_service import capture_order

        result = capture_order(order_id)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Capture failed")}
    amount = round(float(result.get("amount") or pack.get("amount_usd") or 0), 2)
    if amount <= 0:
        return {"success": False, "error": "Invalid captured amount"}
    _apply_balance_delta(
        user_id,
        amount,
        "usd",
        "paypal_deposit",
        {
            "order_id": order_id,
            "capture_id": result.get("capture_id"),
            "pack_id": pack["id"],
        },
    )
    deposits.setdefault("pending", {}).pop(order_id, None)
    deposits.setdefault("captured", {})[order_id] = {
        "user_id": user_id,
        "pack_id": pack["id"],
        "amount_usd": amount,
        "capture_id": result.get("capture_id"),
        "captured_at": _iso(),
    }
    _save_paypal_deposits(deposits)
    try:
        from backend.services.monetization_ledger_service import append_payment_event

        append_payment_event(
            provider="paypal",
            user_id=user_id,
            order_id=order_id,
            capture_id=result.get("capture_id"),
            amount_usd=amount,
            currency=str(result.get("currency") or "USD"),
            item_id=pack["id"],
            item_name=pack.get("label") or pack["id"],
            coins_granted=0,
            generation_credits_granted=0.0,
        )
    except Exception:
        pass
    return {
        "success": True,
        "order_id": order_id,
        "amount_usd": amount,
        "fiat_balance": _user_fiat_balance(user_id),
        "capture_id": result.get("capture_id"),
    }


def _slot_payout(reels: list, paytable: dict, bet_amount: float, currency: str, wild_symbols: Optional[list] = None) -> tuple:
    """Evaluate 3-reel line with optional wild substitution. Returns (outcome, payout, details)."""
    wilds = set(wild_symbols or [])

    def _resolve_symbol(idx: int) -> str:
        sym = reels[idx]
        if sym not in wilds:
            return sym
        for j in (0, 1, 2):
            if j != idx and reels[j] not in wilds:
                return reels[j]
        return sym

    resolved = [_resolve_symbol(i) for i in range(len(reels))]
    symbol = resolved[0] if resolved[0] == resolved[1] == resolved[2] else None
    pair = None
    pair_pos = None
    if not symbol:
        if resolved[0] == resolved[1]:
            pair, pair_pos = resolved[0], "left"
        elif resolved[1] == resolved[2]:
            pair, pair_pos = resolved[1], "right"
        elif resolved[0] == resolved[2]:
            pair, pair_pos = resolved[0], "outer"

    near_miss = False
    if not symbol and not pair and len(reels) >= 3:
        base = [r for r in reels if r not in wilds]
        if len(set(base)) == 2 and len(base) >= 2:
            near_miss = True

    details_base = {
        "reels": reels,
        "resolved_reels": resolved,
        "near_miss": near_miss,
    }

    if symbol:
        mult = float((paytable.get("three") or {}).get(symbol) or paytable.get("default_three") or 5.0)
        payout = _round_payout(bet_amount * mult, currency)
        win_pos = [0, 1, 2]
        return "win", payout, {**details_base, "match": "three", "symbol": symbol, "multiplier": mult, "win_positions": win_pos}
    if pair:
        mult = float((paytable.get("two") or {}).get(pair) or paytable.get("default_two") or 1.2)
        payout = _round_payout(bet_amount * mult, currency)
        win_pos = [0, 1] if pair_pos == "left" else ([1, 2] if pair_pos == "right" else [0, 2])
        return "win", payout, {**details_base, "match": "two", "symbol": pair, "multiplier": mult, "win_positions": win_pos}
    return "loss", 0, {**details_base, "match": "none", "symbol": None, "multiplier": 0, "win_positions": []}


def _pick_weighted_symbol(symbols: list, weights: dict) -> str:
    if weights:
        pool, wts = [], []
        for sym in symbols:
            pool.append(sym)
            wts.append(float(weights.get(sym) or 1))
        total = sum(wts) or 1
        r = random.uniform(0, total)
        acc = 0
        for sym, wt in zip(pool, wts):
            acc += wt
            if r <= acc:
                return sym
    return random.choice(symbols)


def _scatter_bonus(reels: list, game_cfg: dict, bet_amount: float, currency: str) -> tuple:
    scatter = game_cfg.get("scatter_symbol")
    if not scatter:
        return 0, {}
    count = sum(1 for r in reels if r == scatter)
    min_scatter = int(game_cfg.get("scatter_min") or 3)
    if count < min_scatter:
        return 0, {}
    mult = float(game_cfg.get("scatter_multiplier") or 2.0)
    bonus = _round_payout(bet_amount * mult, currency)
    return bonus, {"scatter_count": count, "scatter_bonus": bonus, "scatter_multiplier": mult}


def play_slot(user_id: str, slot_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    """Unified slot engine — config-driven reels, wilds, scatters, jackpots."""
    from backend.services import casino_rng
    from backend.services.engines import slots as slots_engine

    currency = _normalize_currency(currency)
    slot_id = (slot_id or "").strip()
    cfg = get_public_config()
    games = cfg.get("games") or {}
    if slot_id not in games:
        return {"success": False, "error": f"Unknown slot: {slot_id}"}
    game_cfg = games.get(slot_id) or {}

    symbols = [str(s) for s in (game_cfg.get("symbols") or ["7", "bar", "cherry"])]
    weights = game_cfg.get("weights") or {}
    paytable = game_cfg.get("paytable") or {}
    wild_symbols = [str(w) for w in (game_cfg.get("wild_symbols") or [])]
    reel_count = int(game_cfg.get("reels") or 3)
    symbol_display = game_cfg.get("symbol_display") or {}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    floats = [proof["float"]]
    for i in range(1, reel_count):
        extra = casino_rng.draw(user_id)
        floats.append(extra["float"])
    reels = slots_engine.spin_reels(reel_count, symbols, weights, floats)
    _, mult, match_info = slots_engine.evaluate_line(reels, paytable, wild_symbols=wild_symbols)
    outcome = "win" if mult > 0 else "loss"
    payout = _round_payout(amount * mult, currency) if mult > 0 else 0

    jackpot_sym = game_cfg.get("jackpot_symbol")
    if jackpot_sym and len(reels) >= 3 and all(r == jackpot_sym for r in reels[:3]):
        bonus_mult = float(game_cfg.get("jackpot_multiplier") or 15.0)
        payout = _round_payout(amount * bonus_mult, currency)
        outcome = "win"
        match_info = {
            **match_info,
            "match": "jackpot",
            "symbol": jackpot_sym,
            "multiplier": bonus_mult,
            "win_positions": list(range(reel_count)),
        }

    scatter_sym = game_cfg.get("scatter_symbol")
    if scatter_sym:
        sc_count, sc_mult = slots_engine.scatter_bonus(
            reels, scatter_sym, int(game_cfg.get("scatter_min") or 3), float(game_cfg.get("scatter_multiplier") or 2.0)
        )
        if sc_count > 0:
            scatter_pay = _round_payout(amount * sc_mult, currency)
            payout = _round_payout(payout + scatter_pay, currency)
            if outcome == "loss":
                outcome = "win"
            match_info = {**match_info, "scatter_count": sc_count, "scatter_bonus": scatter_pay, "scatter_multiplier": sc_mult}

    return _finalize_bet(
        user_id,
        slot_id,
        amount,
        outcome,
        payout,
        {
            **match_info,
            "slot": slot_id.replace("slot_", ""),
            "slot_id": slot_id,
            "label": game_cfg.get("label") or slot_id,
            "volatility": game_cfg.get("volatility"),
            "rtp_estimate": game_cfg.get("rtp_estimate"),
            "symbol_display": symbol_display,
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


def play_slot_classic(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    return play_slot(user_id, "slot_classic", bet, currency)


def play_slot_diamond(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    return play_slot(user_id, "slot_diamond", bet, currency)


# ---------------------------------------------------------------------------
# Wheel of Fortune — single-call weighted spin (provably fair)
# ---------------------------------------------------------------------------

def _wheel_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("wheel") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    tables = game.get("risk_tables") if isinstance(game.get("risk_tables"), dict) else {}
    clean: Dict[str, List[Dict[str, float]]] = {}
    for risk, segs in tables.items():
        if isinstance(segs, list):
            clean[str(risk).lower()] = [
                {"multiplier": float(s.get("multiplier", 0)), "weight": float(s.get("weight", 1))}
                for s in segs if isinstance(s, dict)
            ]
    return {
        "label": game.get("label") or "Wheel of Fortune",
        "icon": game.get("icon") or "🎡",
        "rtp_estimate": float(game.get("rtp_estimate") or 98.0),
        "risk_tables": clean,
    }


def play_wheel(user_id: str, bet: float, risk: str = "medium", currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import wheel as wheel_engine

    currency = _normalize_currency(currency)
    conf = _wheel_config()
    risk = (risk or "medium").strip().lower()
    segments = conf["risk_tables"].get(risk)
    if not segments:
        return {"success": False, "error": f"risk must be one of {sorted(conf['risk_tables'].keys())}"}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    res = wheel_engine.spin(proof["float"], segments)
    multiplier = float(res["multiplier"])
    payout = _round_payout(amount * multiplier, currency)
    if payout > amount:
        outcome = "win"
    elif payout == amount:
        outcome = "draw"
    else:
        outcome = "loss"

    return _finalize_bet(
        user_id,
        "wheel",
        amount,
        outcome,
        payout,
        {
            "risk": risk,
            "index": res["index"],
            "multiplier": multiplier,
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Mines — stateful reveal / cash-out (provably-fair board)
# ---------------------------------------------------------------------------

def _mines_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("mines") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Mines",
        "icon": game.get("icon") or "💣",
        "tiles": int(game.get("tiles") or 25),
        "default_mines": int(game.get("default_mines") or 3),
        "min_mines": int(game.get("min_mines") or 1),
        "max_mines": int(game.get("max_mines") or 24),
        "house_edge": float(game.get("house_edge") if game.get("house_edge") is not None else 0.01),
        "max_round_seconds": float(game.get("max_round_seconds") or 7200),
        "rtp_estimate": float(game.get("rtp_estimate") or 99.0),
    }


def _mines_rounds_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_mines_rounds.json")


def _load_mines_rounds() -> Dict[str, Any]:
    path = _mines_rounds_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_mines_rounds(data: Dict[str, Any]) -> None:
    try:
        with open(_mines_rounds_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _mines_elapsed_seconds(round_state: Dict[str, Any]) -> float:
    try:
        started = datetime.fromisoformat(round_state.get("started_at"))
    except Exception:
        return 0.0
    return max(0.0, (_utcnow() - started).total_seconds())


def _settle_mines_round(round_state: Dict[str, Any], payout: float, outcome: str) -> Dict[str, Any]:
    """Credit payout for a pre-staked mines round and write a correct ledger row."""
    user_id = round_state["user_id"]
    currency = _normalize_currency(round_state.get("currency"))
    bet = _parse_bet_amount(round_state.get("bet"), currency) or 0
    payout = _round_payout(payout, currency)
    net = _round_payout(payout - bet, currency)
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, "mines", {"phase": "payout"})
    revealed = round_state.get("revealed") or []
    details = {
        "tiles": round_state.get("tiles"),
        "mines": round_state.get("mines"),
        "mine_positions": round_state.get("mine_positions"),
        "revealed": revealed,
        "revealed_count": len(revealed),
        "multiplier": round_state.get("cashout_multiplier"),
        "fairness": round_state.get("fairness"),
    }
    row = {
        "bet_id": round_state.get("round_id") or str(uuid.uuid4()),
        "user_id": user_id,
        "game": "mines",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": False,
        "parent_bet_id": None,
        "double_step": 0,
    }
    jackpot_award = _append_ledger(row)
    result = {
        "success": True,
        "bet_id": row["bet_id"],
        "round_id": round_state.get("round_id"),
        "game": "mines",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "multiplier": round_state.get("cashout_multiplier"),
        "mine_positions": round_state.get("mine_positions"),
        "revealed": revealed,
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
    return result


def _expire_stale_mines_rounds() -> None:
    rounds = _load_mines_rounds()
    conf = _mines_config()
    grace = conf["max_round_seconds"]
    changed = False
    for rid in list(rounds.keys()):
        state = rounds.get(rid)
        if not isinstance(state, dict) or state.get("settled"):
            rounds.pop(rid, None)
            changed = True
            continue
        if _mines_elapsed_seconds(state) > grace:
            state["cashout_multiplier"] = 0.0
            _settle_mines_round(state, payout=0.0, outcome="loss")
            rounds.pop(rid, None)
            changed = True
    if changed:
        _save_mines_rounds(rounds)


def start_mines_round(
    user_id: str,
    bet: float,
    mines: int = 3,
    currency: str = "coins",
) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import mines as mines_engine

    currency = _normalize_currency(currency)
    conf = _mines_config()
    _expire_stale_mines_rounds()

    try:
        mine_count = int(mines)
    except (TypeError, ValueError):
        mine_count = conf["default_mines"]
    if mine_count < conf["min_mines"] or mine_count > conf["max_mines"]:
        return {"success": False, "error": f"mines must be between {conf['min_mines']} and {conf['max_mines']}"}

    rounds = _load_mines_rounds()
    for rid, state in rounds.items():
        if isinstance(state, dict) and state.get("user_id") == user_id and not state.get("settled"):
            return {
                "success": False,
                "error": "Finish your active mines round first",
                "code": "MINES_ROUND_ACTIVE",
                "round_id": rid,
            }

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    positions = mines_engine.mine_positions(proof["float"], conf["tiles"], mine_count)

    _apply_balance_delta(user_id, -amount, currency, "mines", {"phase": "stake"})

    round_id = str(uuid.uuid4())
    round_state = {
        "round_id": round_id,
        "user_id": user_id,
        "bet": amount,
        "currency": currency,
        "tiles": conf["tiles"],
        "mines": mine_count,
        "house_edge": conf["house_edge"],
        "mine_positions": positions,
        "revealed": [],
        "cashout_multiplier": 1.0,
        "settled": False,
        "started_at": _iso(),
        "fairness": {
            "server_seed_hash": proof["server_seed_hash"],
            "client_seed": proof["client_seed"],
            "nonce": proof["nonce"],
        },
    }
    rounds[round_id] = round_state
    _save_mines_rounds(rounds)

    next_mult = mines_engine.multiplier(conf["tiles"], mine_count, 1, conf["house_edge"])
    return {
        "success": True,
        "round_id": round_id,
        "bet": amount,
        "currency": currency,
        "tiles": conf["tiles"],
        "mines": mine_count,
        "safe_tiles": mines_engine.safe_tiles(conf["tiles"], mine_count),
        "multiplier": 1.0,
        "next_multiplier": next_mult,
        "fairness": round_state["fairness"],
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
    }


def reveal_mines_tile(user_id: str, round_id: str, tile: int) -> Dict[str, Any]:
    from backend.services.engines import mines as mines_engine

    rounds = _load_mines_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "MINES_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "MINES_ALREADY_SETTLED"}

    try:
        idx = int(tile)
    except (TypeError, ValueError):
        return {"success": False, "error": "tile must be an integer"}
    tiles = int(state.get("tiles") or 25)
    if idx < 0 or idx >= tiles:
        return {"success": False, "error": f"tile must be between 0 and {tiles - 1}"}
    revealed = state.get("revealed") or []
    if idx in revealed:
        return {"success": False, "error": "Tile already revealed"}

    mine_count = int(state.get("mines") or 3)
    house_edge = float(state.get("house_edge") or 0.01)
    positions = state.get("mine_positions") or []

    if idx in positions:
        state["settled"] = True
        state["cashout_multiplier"] = 0.0
        result = _settle_mines_round(state, payout=0.0, outcome="loss")
        rounds.pop(round_id, None)
        _save_mines_rounds(rounds)
        result["hit_mine"] = True
        result["tile"] = idx
        return result

    revealed.append(idx)
    state["revealed"] = revealed
    k = len(revealed)
    current_mult = mines_engine.multiplier(tiles, mine_count, k, house_edge)
    state["cashout_multiplier"] = current_mult
    safe_total = mines_engine.safe_tiles(tiles, mine_count)

    if k >= safe_total:
        # All safe tiles cleared — auto cash out at the maximum multiplier.
        state["settled"] = True
        bet_currency = _normalize_currency(state.get("currency"))
        bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
        payout = bet_amount * current_mult
        result = _settle_mines_round(state, payout=payout, outcome="win")
        rounds.pop(round_id, None)
        _save_mines_rounds(rounds)
        result["hit_mine"] = False
        result["tile"] = idx
        result["cleared"] = True
        return result

    _save_mines_rounds(rounds)
    next_mult = mines_engine.multiplier(tiles, mine_count, k + 1, house_edge)
    bet_currency = _normalize_currency(state.get("currency"))
    bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
    return {
        "success": True,
        "hit_mine": False,
        "round_id": round_id,
        "tile": idx,
        "revealed": revealed,
        "revealed_count": k,
        "safe_tiles": safe_total,
        "multiplier": current_mult,
        "next_multiplier": next_mult,
        "potential_payout": _round_payout(bet_amount * current_mult, bet_currency),
        "can_cashout": True,
        "currency": bet_currency,
    }


def cashout_mines_round(user_id: str, round_id: str) -> Dict[str, Any]:
    from backend.services.engines import mines as mines_engine

    rounds = _load_mines_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "MINES_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "MINES_ALREADY_SETTLED"}

    tiles = int(state.get("tiles") or 25)
    mine_count = int(state.get("mines") or 3)
    house_edge = float(state.get("house_edge") or 0.01)
    k = len(state.get("revealed") or [])
    mult = mines_engine.multiplier(tiles, mine_count, k, house_edge)
    state["cashout_multiplier"] = mult
    state["settled"] = True

    bet_currency = _normalize_currency(state.get("currency"))
    bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
    payout = bet_amount * mult
    outcome = "win" if payout > bet_amount else "draw"
    result = _settle_mines_round(state, payout=payout, outcome=outcome)
    rounds.pop(round_id, None)
    _save_mines_rounds(rounds)
    result["hit_mine"] = False
    result["cashed_out"] = True
    return result


def list_slot_machines() -> Dict[str, Any]:
    """Public metadata for all configured slot machines."""
    cfg = get_public_config()
    games = cfg.get("games") or {}
    slots = []
    for key, game in sorted(games.items()):
        if not str(key).startswith("slot_"):
            continue
        slots.append({
            "id": key,
            "label": game.get("label") or key,
            "icon": game.get("icon") or "🎰",
            "volatility": game.get("volatility") or "medium",
            "rtp_estimate": game.get("rtp_estimate"),
            "reels": int(game.get("reels") or 3),
            "symbol_display": game.get("symbol_display") or {},
            "has_wild": bool(game.get("wild_symbols")),
            "has_scatter": bool(game.get("scatter_symbol")),
            "scatter_symbol": game.get("scatter_symbol"),
            "jackpot_symbol": game.get("jackpot_symbol"),
            "jackpot_multiplier": game.get("jackpot_multiplier"),
            "theme_color": game.get("theme_color"),
            "accent": game.get("accent"),
            "glow_color": game.get("glow_color"),
        })
    return {"success": True, "slots": slots, "count": len(slots)}


# ---------------------------------------------------------------------------
# Keno — single-call (provably-fair draw, hypergeometric pay table)
# ---------------------------------------------------------------------------

def _keno_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("keno") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Keno",
        "icon": game.get("icon") or "🔢",
        "pool": int(game.get("pool") or 40),
        "draw": int(game.get("draw") or 10),
        "max_spots": int(game.get("max_spots") or 6),
        "rtp_estimate": float(game.get("rtp_estimate") or 94.0),
        "pay_table": game.get("pay_table") if isinstance(game.get("pay_table"), dict) else {},
    }


def play_keno(user_id: str, bet: float, spots: List[int], currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import keno as keno_engine

    currency = _normalize_currency(currency)
    conf = _keno_config()

    if not isinstance(spots, (list, tuple)):
        return {"success": False, "error": "spots must be a list of numbers"}
    try:
        picks = sorted({int(s) for s in spots})
    except (TypeError, ValueError):
        return {"success": False, "error": "spots must be integers"}
    if not picks:
        return {"success": False, "error": "Pick at least one number"}
    if len(picks) > conf["max_spots"]:
        return {"success": False, "error": f"Pick at most {conf['max_spots']} numbers"}
    if picks[0] < 1 or picks[-1] > conf["pool"]:
        return {"success": False, "error": f"Numbers must be between 1 and {conf['pool']}"}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    drawn = keno_engine.draw_numbers(proof["float"], conf["pool"], conf["draw"])
    hits = keno_engine.count_hits(picks, drawn)
    multiplier = keno_engine.payout_multiplier(len(picks), hits, conf["pay_table"])
    payout = _round_payout(amount * multiplier, currency)
    if payout > amount:
        outcome = "win"
    elif payout == amount:
        outcome = "draw"
    else:
        outcome = "loss"

    return _finalize_bet(
        user_id,
        "keno",
        amount,
        outcome,
        payout,
        {
            "spots": picks,
            "drawn": drawn,
            "hits": hits,
            "multiplier": multiplier,
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Roulette — single-call (European single-zero, provably-fair pocket)
# ---------------------------------------------------------------------------

def _roulette_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("roulette") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Roulette",
        "icon": game.get("icon") or "🎯",
        "pockets": int(game.get("pockets") or 37),
        "rtp_estimate": float(game.get("rtp_estimate") or 97.3),
    }


def play_roulette(
    user_id: str,
    bet: float,
    bet_type: str,
    selection: Any = None,
    currency: str = "coins",
) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import roulette as roulette_engine

    currency = _normalize_currency(currency)
    conf = _roulette_config()
    bt = (bet_type or "").strip().lower()
    valid = ("straight",) + roulette_engine.OUTSIDE_BETS
    if bt not in valid:
        return {"success": False, "error": f"bet_type must be one of {sorted(valid)}"}

    sel: Optional[int] = None
    if bt == "straight":
        try:
            sel = int(selection)
        except (TypeError, ValueError):
            return {"success": False, "error": "straight bet needs a number 0–36"}
        if sel < 0 or sel > conf["pockets"] - 1:
            return {"success": False, "error": f"number must be between 0 and {conf['pockets'] - 1}"}
    elif bt in ("dozen", "column"):
        try:
            sel = int(selection)
        except (TypeError, ValueError):
            return {"success": False, "error": f"{bt} bet needs a selection of 1, 2 or 3"}
        if sel not in (1, 2, 3):
            return {"success": False, "error": f"{bt} selection must be 1, 2 or 3"}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    pocket = roulette_engine.spin(proof["float"], conf["pockets"])
    multiplier = roulette_engine.evaluate(pocket, bt, sel)
    payout = _round_payout(amount * multiplier, currency)
    outcome = "win" if payout > amount else "loss"

    return _finalize_bet(
        user_id,
        "roulette",
        amount,
        outcome,
        payout,
        {
            "pocket": pocket,
            "color": roulette_engine.color(pocket),
            "bet_type": bt,
            "selection": sel,
            "multiplier": multiplier,
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Hi-Lo — stateful guess / cash-out (provably-fair card stream)
# ---------------------------------------------------------------------------

def _hilo_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("hilo") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Hi-Lo",
        "icon": game.get("icon") or "🃏",
        "ranks": int(game.get("ranks") or 13),
        "house_edge": float(game.get("house_edge") if game.get("house_edge") is not None else 0.02),
        "max_round_seconds": float(game.get("max_round_seconds") or 7200),
        "rtp_estimate": float(game.get("rtp_estimate") or 98.0),
    }


def _hilo_rounds_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_hilo_rounds.json")


def _load_hilo_rounds() -> Dict[str, Any]:
    path = _hilo_rounds_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_hilo_rounds(data: Dict[str, Any]) -> None:
    try:
        with open(_hilo_rounds_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _hilo_elapsed_seconds(round_state: Dict[str, Any]) -> float:
    try:
        started = datetime.fromisoformat(round_state.get("started_at"))
    except Exception:
        return 0.0
    return max(0.0, (_utcnow() - started).total_seconds())


def _hilo_step_multipliers(card: int, conf: Dict[str, Any]) -> Dict[str, float]:
    from backend.services.engines import hilo as hilo_engine

    ranks = conf["ranks"]
    edge = conf["house_edge"]
    return {
        "higher": hilo_engine.step_multiplier(card, "higher", edge, ranks),
        "lower": hilo_engine.step_multiplier(card, "lower", edge, ranks),
    }


def _settle_hilo_round(round_state: Dict[str, Any], payout: float, outcome: str) -> Dict[str, Any]:
    user_id = round_state["user_id"]
    currency = _normalize_currency(round_state.get("currency"))
    bet = _parse_bet_amount(round_state.get("bet"), currency) or 0
    payout = _round_payout(payout, currency)
    net = _round_payout(payout - bet, currency)
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, "hilo", {"phase": "payout"})
    details = {
        "cards": round_state.get("cards"),
        "steps": round_state.get("steps"),
        "multiplier": round_state.get("multiplier"),
        "fairness": round_state.get("fairness"),
    }
    row = {
        "bet_id": round_state.get("round_id") or str(uuid.uuid4()),
        "user_id": user_id,
        "game": "hilo",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": False,
        "parent_bet_id": None,
        "double_step": 0,
    }
    jackpot_award = _append_ledger(row)
    result = {
        "success": True,
        "bet_id": row["bet_id"],
        "round_id": round_state.get("round_id"),
        "game": "hilo",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "multiplier": round_state.get("multiplier"),
        "cards": round_state.get("cards"),
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
    return result


def _expire_stale_hilo_rounds() -> None:
    rounds = _load_hilo_rounds()
    conf = _hilo_config()
    grace = conf["max_round_seconds"]
    changed = False
    for rid in list(rounds.keys()):
        state = rounds.get(rid)
        if not isinstance(state, dict) or state.get("settled"):
            rounds.pop(rid, None)
            changed = True
            continue
        if _hilo_elapsed_seconds(state) > grace:
            state["settled"] = True
            _settle_hilo_round(state, payout=0.0, outcome="loss")
            rounds.pop(rid, None)
            changed = True
    if changed:
        _save_hilo_rounds(rounds)


def start_hilo_round(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import hilo as hilo_engine

    currency = _normalize_currency(currency)
    conf = _hilo_config()
    _expire_stale_hilo_rounds()

    rounds = _load_hilo_rounds()
    for rid, state in rounds.items():
        if isinstance(state, dict) and state.get("user_id") == user_id and not state.get("settled"):
            return {
                "success": False,
                "error": "Finish your active Hi-Lo round first",
                "code": "HILO_ROUND_ACTIVE",
                "round_id": rid,
            }

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0

    proof = casino_rng.draw(user_id)
    first_card = hilo_engine.card_from_float(proof["float"], conf["ranks"])

    _apply_balance_delta(user_id, -amount, currency, "hilo", {"phase": "stake"})

    round_id = str(uuid.uuid4())
    round_state = {
        "round_id": round_id,
        "user_id": user_id,
        "bet": amount,
        "currency": currency,
        "ranks": conf["ranks"],
        "house_edge": conf["house_edge"],
        "current_card": first_card,
        "cards": [first_card],
        "steps": [],
        "multiplier": 1.0,
        "settled": False,
        "started_at": _iso(),
        "fairness": {
            "server_seed_hash": proof["server_seed_hash"],
            "client_seed": proof["client_seed"],
            "nonce": proof["nonce"],
        },
    }
    rounds[round_id] = round_state
    _save_hilo_rounds(rounds)

    return {
        "success": True,
        "round_id": round_id,
        "bet": amount,
        "currency": currency,
        "card": first_card,
        "ranks": conf["ranks"],
        "multiplier": 1.0,
        "next_multipliers": _hilo_step_multipliers(first_card, conf),
        "fairness": round_state["fairness"],
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
    }


def hilo_guess(user_id: str, round_id: str, direction: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import hilo as hilo_engine

    direction = (direction or "").strip().lower()
    if direction not in ("higher", "lower"):
        return {"success": False, "error": "direction must be 'higher' or 'lower'"}

    rounds = _load_hilo_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "HILO_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "HILO_ALREADY_SETTLED"}

    conf = _hilo_config()
    ranks = int(state.get("ranks") or conf["ranks"])
    edge = float(state.get("house_edge") or conf["house_edge"])
    current = int(state.get("current_card"))

    proof = casino_rng.draw(user_id)
    next_card = hilo_engine.card_from_float(proof["float"], ranks)
    state.setdefault("cards", []).append(next_card)
    state.setdefault("steps", []).append({"direction": direction, "from": current, "to": next_card})

    if not hilo_engine.wins(current, next_card, direction):
        state["settled"] = True
        state["multiplier"] = 0.0
        result = _settle_hilo_round(state, payout=0.0, outcome="loss")
        rounds.pop(round_id, None)
        _save_hilo_rounds(rounds)
        result["busted"] = True
        result["card"] = next_card
        return result

    step_mult = hilo_engine.step_multiplier(current, direction, edge, ranks)
    new_mult = round(float(state.get("multiplier") or 1.0) * step_mult, 6)
    state["multiplier"] = new_mult
    state["current_card"] = next_card
    _save_hilo_rounds(rounds)

    bet_currency = _normalize_currency(state.get("currency"))
    bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
    return {
        "success": True,
        "busted": False,
        "round_id": round_id,
        "card": next_card,
        "previous_card": current,
        "direction": direction,
        "step_multiplier": step_mult,
        "multiplier": new_mult,
        "next_multipliers": _hilo_step_multipliers(next_card, conf),
        "potential_payout": _round_payout(bet_amount * new_mult, bet_currency),
        "can_cashout": True,
        "currency": bet_currency,
    }


def hilo_cashout(user_id: str, round_id: str) -> Dict[str, Any]:
    rounds = _load_hilo_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "HILO_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "HILO_ALREADY_SETTLED"}

    bet_currency = _normalize_currency(state.get("currency"))
    bet_amount = _parse_bet_amount(state.get("bet"), bet_currency) or 0
    mult = float(state.get("multiplier") or 1.0)
    state["settled"] = True
    payout = bet_amount * mult
    outcome = "win" if payout > bet_amount else "draw"
    result = _settle_hilo_round(state, payout=payout, outcome=outcome)
    rounds.pop(round_id, None)
    _save_hilo_rounds(rounds)
    result["cashed_out"] = True
    return result


# ---------------------------------------------------------------------------
# Blackjack — stateful hit / stand / double
# ---------------------------------------------------------------------------

def _blackjack_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("blackjack") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Blackjack",
        "icon": game.get("icon") or "🃏",
        "rtp_estimate": float(game.get("rtp_estimate") or 99.5),
        "blackjack_payout": float(game.get("blackjack_payout") or 1.5),
        "hit_soft_17": bool(game.get("hit_soft_17", True)),
        "max_round_seconds": float(game.get("max_round_seconds") or 7200),
    }


def _bj_rounds_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_blackjack_rounds.json")


def _load_bj_rounds() -> Dict[str, Any]:
    path = _bj_rounds_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_bj_rounds(data: Dict[str, Any]) -> None:
    try:
        with open(_bj_rounds_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _bj_cards_public(cards: List[int]) -> List[str]:
    from backend.services.engines import cards as cards_engine
    return [cards_engine.card_label(c) for c in cards]


def _settle_blackjack_round(state: Dict[str, Any], outcome: str, payout: float) -> Dict[str, Any]:
    user_id = state["user_id"]
    currency = _normalize_currency(state.get("currency"))
    bet = _parse_bet_amount(state.get("bet"), currency) or 0
    payout = _round_payout(payout, currency)
    net = _round_payout(payout - bet, currency)
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, "blackjack", {"phase": "payout"})
    details = {
        "player": _bj_cards_public(state.get("player") or []),
        "dealer": _bj_cards_public(state.get("dealer") or []),
        "dealer_hidden": state.get("dealer_hidden"),
        "doubled": state.get("doubled"),
        "fairness": state.get("fairness"),
    }
    row = {
        "bet_id": state.get("round_id") or str(uuid.uuid4()),
        "user_id": user_id,
        "game": "blackjack",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": False,
        "parent_bet_id": None,
        "double_step": 0,
    }
    jackpot_award = _append_ledger(row)
    result = {
        "success": True,
        "bet_id": row["bet_id"],
        "round_id": state.get("round_id"),
        "game": "blackjack",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "player": details["player"],
        "dealer": details["dealer"],
        "balance": _user_balance(user_id, currency),
        "coins_balance": _user_coins(user_id),
        "mn2_balance": _user_mn2_balance(user_id),
        "fiat_balance": _user_fiat_balance(user_id),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
    return result


def start_blackjack_round(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    currency = _normalize_currency(currency)
    conf = _blackjack_config()
    rounds = _load_bj_rounds()
    for rid, state in rounds.items():
        if isinstance(state, dict) and state.get("user_id") == user_id and not state.get("settled"):
            return {"success": False, "error": "Finish your active blackjack hand first", "code": "BJ_ROUND_ACTIVE", "round_id": rid}

    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    proof = casino_rng.draw(user_id)
    deck = cards_engine.shuffle_deck(proof["float"])
    player, deck = cards_engine.draw_cards(deck, 2)
    dealer, deck = cards_engine.draw_cards(deck, 2)
    _apply_balance_delta(user_id, -amount, currency, "blackjack", {"phase": "stake"})

    round_id = str(uuid.uuid4())
    state = {
        "round_id": round_id,
        "user_id": user_id,
        "bet": amount,
        "currency": currency,
        "player": player,
        "dealer": dealer,
        "deck": deck,
        "dealer_hidden": True,
        "doubled": False,
        "settled": False,
        "can_double": True,
        "started_at": _iso(),
        "fairness": {"server_seed_hash": proof["server_seed_hash"], "client_seed": proof["client_seed"], "nonce": proof["nonce"]},
        "config": conf,
    }

    if cards_engine.is_blackjack(player):
        state["dealer_hidden"] = False
        if cards_engine.is_blackjack(dealer):
            state["settled"] = True
            result = _settle_blackjack_round(state, "push", amount)
            rounds.pop(round_id, None)
            _save_bj_rounds(rounds)
            return result
        state["settled"] = True
        mult = 1.0 + conf["blackjack_payout"]
        result = _settle_blackjack_round(state, "win", amount * mult)
        rounds.pop(round_id, None)
        _save_bj_rounds(rounds)
        return result

    rounds[round_id] = state
    _save_bj_rounds(rounds)
    return {
        "success": True,
        "round_id": round_id,
        "bet": amount,
        "currency": currency,
        "player": _bj_cards_public(player),
        "dealer_up": _bj_cards_public([dealer[0]])[0],
        "player_value": cards_engine.blackjack_value(player),
        "can_hit": True,
        "can_stand": True,
        "can_double": True,
        "fairness": state["fairness"],
        "balance": _user_balance(user_id, currency),
    }


def _bj_get_round(user_id: str, round_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    rounds = _load_bj_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return None, {"success": False, "error": "Round not found", "code": "BJ_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return None, {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return None, {"success": False, "error": "Round already settled", "code": "BJ_ALREADY_SETTLED"}
    return state, None


def blackjack_hit(user_id: str, round_id: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    state, err = _bj_get_round(user_id, round_id)
    if err:
        return err
    proof = casino_rng.draw(user_id)
    deck = state.get("deck") or []
    if not deck:
        deck = cards_engine.shuffle_deck(proof["float"])
    drawn, deck = cards_engine.draw_cards(deck, 1)
    state["player"] = list(state.get("player") or []) + drawn
    state["deck"] = deck
    state["can_double"] = False
    val = cards_engine.blackjack_value(state["player"])
    if val > 21:
        state["settled"] = True
        state["dealer_hidden"] = False
        rounds = _load_bj_rounds()
        result = _settle_blackjack_round(state, "loss", 0.0)
        rounds.pop(round_id, None)
        _save_bj_rounds(rounds)
        result["busted"] = True
        result["player_value"] = val
        return result
    rounds = _load_bj_rounds()
    rounds[round_id] = state
    _save_bj_rounds(rounds)
    return {
        "success": True,
        "round_id": round_id,
        "player": _bj_cards_public(state["player"]),
        "player_value": val,
        "can_hit": True,
        "can_stand": True,
        "can_double": False,
    }


def _blackjack_dealer_play(state: Dict[str, Any]) -> None:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    conf = state.get("config") or _blackjack_config()
    deck = list(state.get("deck") or [])
    while cards_engine.dealer_should_hit(state["dealer"], conf.get("hit_soft_17", True)):
        if not deck:
            proof = casino_rng.draw(state["user_id"])
            deck = cards_engine.shuffle_deck(proof["float"])
        drawn, deck = cards_engine.draw_cards(deck, 1)
        state["dealer"] = list(state.get("dealer") or []) + drawn
    state["deck"] = deck
    state["dealer_hidden"] = False


def blackjack_stand(user_id: str, round_id: str) -> Dict[str, Any]:
    from backend.services.engines import cards as cards_engine

    state, err = _bj_get_round(user_id, round_id)
    if err:
        return err
    _blackjack_dealer_play(state)
    conf = state.get("config") or _blackjack_config()
    outcome, mult = cards_engine.blackjack_outcome(
        state["player"], state["dealer"], blackjack_payout=conf["blackjack_payout"]
    )
    bet = _parse_bet_amount(state.get("bet"), _normalize_currency(state.get("currency"))) or 0
    state["settled"] = True
    result = _settle_blackjack_round(state, outcome, bet * mult)
    rounds = _load_bj_rounds()
    rounds.pop(round_id, None)
    _save_bj_rounds(rounds)
    result["player_value"] = cards_engine.blackjack_value(state["player"])
    result["dealer_value"] = cards_engine.blackjack_value(state["dealer"])
    return result


def blackjack_double(user_id: str, round_id: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    state, err = _bj_get_round(user_id, round_id)
    if err:
        return err
    if not state.get("can_double"):
        return {"success": False, "error": "Double not allowed on this hand"}
    currency = _normalize_currency(state.get("currency"))
    extra = _parse_bet_amount(state.get("bet"), currency) or 0
    bal_err = _validate_bet(user_id, extra, currency)
    if bal_err:
        return {"success": False, "error": bal_err}
    _apply_balance_delta(user_id, -extra, currency, "blackjack", {"phase": "double"})
    state["bet"] = extra * 2
    state["doubled"] = True
    state["can_double"] = False
    proof = casino_rng.draw(user_id)
    deck = state.get("deck") or cards_engine.shuffle_deck(proof["float"])
    drawn, deck = cards_engine.draw_cards(deck, 1)
    state["player"] = list(state.get("player") or []) + drawn
    state["deck"] = deck
    val = cards_engine.blackjack_value(state["player"])
    if val > 21:
        state["settled"] = True
        state["dealer_hidden"] = False
        result = _settle_blackjack_round(state, "loss", 0.0)
        rounds = _load_bj_rounds()
        rounds.pop(round_id, None)
        _save_bj_rounds(rounds)
        result["busted"] = True
        return result
    return blackjack_stand(user_id, round_id)


# ---------------------------------------------------------------------------
# Baccarat — single-call player / banker / tie
# ---------------------------------------------------------------------------

def _baccarat_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("baccarat") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Baccarat",
        "icon": game.get("icon") or "🎴",
        "rtp_estimate": float(game.get("rtp_estimate") or 98.9),
        "banker_commission": float(game.get("banker_commission") or 0.05),
    }


def play_baccarat(user_id: str, bet: float, side: str, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    currency = _normalize_currency(currency)
    conf = _baccarat_config()
    pick = (side or "").strip().lower()
    if pick not in ("player", "banker", "tie"):
        return {"success": False, "error": "side must be player, banker, or tie"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    proof = casino_rng.draw(user_id)
    deal = cards_engine.baccarat_deal(proof["float"])
    winner = str(deal["winner"])
    mult = cards_engine.baccarat_payout(pick, winner, banker_commission=conf["banker_commission"])
    payout = _round_payout(amount * mult, currency)
    if mult == 1.0 and pick in ("player", "banker") and winner == "tie":
        outcome = "push"
    elif mult > 1.0:
        outcome = "win"
    elif mult == 0.0:
        outcome = "loss"
    else:
        outcome = "push"
    return _finalize_bet(
        user_id,
        "baccarat",
        amount,
        outcome,
        payout,
        {
            "side": pick,
            "winner": winner,
            "player": _bj_cards_public(list(deal["player"])),
            "banker": _bj_cards_public(list(deal["banker"])),
            "player_total": deal["player_total"],
            "banker_total": deal["banker_total"],
            "multiplier": mult,
            "rtp_estimate": conf["rtp_estimate"],
            "fairness": {
                "server_seed_hash": proof["server_seed_hash"],
                "client_seed": proof["client_seed"],
                "nonce": proof["nonce"],
            },
        },
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Video poker — Jacks or Better (deal + hold/draw)
# ---------------------------------------------------------------------------

def _vp_rounds_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_video_poker_rounds.json")


def _load_vp_rounds() -> Dict[str, Any]:
    path = _vp_rounds_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_vp_rounds(data: Dict[str, Any]) -> None:
    try:
        with open(_vp_rounds_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _video_poker_config() -> Dict[str, Any]:
    cfg = _load_config()
    game = (cfg.get("games") or {}).get("video_poker") if isinstance(cfg.get("games"), dict) else {}
    game = game if isinstance(game, dict) else {}
    return {
        "label": game.get("label") or "Video Poker",
        "icon": game.get("icon") or "🎴",
        "rtp_estimate": float(game.get("rtp_estimate") or 99.5),
        "paytable": game.get("paytable") or {},
    }


def start_video_poker_round(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    currency = _normalize_currency(currency)
    rounds = _load_vp_rounds()
    for rid, state in rounds.items():
        if isinstance(state, dict) and state.get("user_id") == user_id and not state.get("settled"):
            return {"success": False, "error": "Finish your active video poker hand first", "code": "VP_ROUND_ACTIVE", "round_id": rid}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    proof = casino_rng.draw(user_id)
    hand = cards_engine.video_poker_deal(proof["float"])
    _apply_balance_delta(user_id, -amount, currency, "video_poker", {"phase": "stake"})
    round_id = str(uuid.uuid4())
    state = {
        "round_id": round_id,
        "user_id": user_id,
        "bet": amount,
        "currency": currency,
        "hand": hand,
        "settled": False,
        "fairness": {"server_seed_hash": proof["server_seed_hash"], "client_seed": proof["client_seed"], "nonce": proof["nonce"]},
    }
    rounds[round_id] = state
    _save_vp_rounds(rounds)
    return {
        "success": True,
        "round_id": round_id,
        "bet": amount,
        "currency": currency,
        "hand": _bj_cards_public(hand),
        "fairness": state["fairness"],
        "balance": _user_balance(user_id, currency),
    }


def video_poker_draw(user_id: str, round_id: str, hold: Optional[List[int]] = None) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import cards as cards_engine

    rounds = _load_vp_rounds()
    state = rounds.get(round_id)
    if not isinstance(state, dict):
        return {"success": False, "error": "Round not found", "code": "VP_ROUND_NOT_FOUND"}
    if state.get("user_id") != user_id:
        return {"success": False, "error": "Round does not belong to this user"}
    if state.get("settled"):
        return {"success": False, "error": "Round already settled", "code": "VP_ALREADY_SETTLED"}

    conf = _video_poker_config()
    hold_idx = [int(i) for i in (hold or []) if 0 <= int(i) < 5]
    proof = casino_rng.draw(user_id)
    final_hand = cards_engine.video_poker_draw(state.get("hand") or [], hold_idx, proof["float"])
    hand_name, mult = cards_engine.evaluate_video_poker(final_hand, conf.get("paytable"))
    currency = _normalize_currency(state.get("currency"))
    bet = _parse_bet_amount(state.get("bet"), currency) or 0
    payout = _round_payout(bet * mult, currency) if mult > 0 else 0
    outcome = "win" if payout > bet else ("push" if payout == bet else "loss")
    if payout > 0:
        _apply_balance_delta(user_id, payout, currency, "video_poker", {"phase": "payout"})
    details = {
        "hand": _bj_cards_public(final_hand),
        "hold": hold_idx,
        "hand_name": hand_name,
        "multiplier": mult,
        "fairness": {**state.get("fairness", {}), "draw_nonce": proof["nonce"]},
    }
    row = {
        "bet_id": round_id,
        "user_id": user_id,
        "game": "video_poker",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": _round_payout(payout - bet, currency),
        "details": details,
        "created_at": _iso(),
        "exclude_leaderboard": False,
        "parent_bet_id": None,
        "double_step": 0,
    }
    jackpot_award = _append_ledger(row)
    rounds.pop(round_id, None)
    _save_vp_rounds(rounds)
    result = {
        "success": True,
        "bet_id": round_id,
        "round_id": round_id,
        "game": "video_poker",
        "bet": bet,
        "currency": currency,
        "outcome": outcome,
        "payout": payout,
        "net": row["net"],
        "hand_name": hand_name,
        "multiplier": mult,
        "hand": details["hand"],
        "balance": _user_balance(user_id, currency),
        "details": details,
    }
    if jackpot_award:
        result["jackpot"] = jackpot_award
    return result


# ---------------------------------------------------------------------------
# PvP duels — coin-flip or RPS head-to-head escrow
# ---------------------------------------------------------------------------

def _duels_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_duels.json")


def _load_duels() -> Dict[str, Any]:
    path = _duels_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_duels(data: Dict[str, Any]) -> None:
    try:
        with open(_duels_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _duel_rake() -> float:
    cfg = _load_config()
    social = cfg.get("pvp") if isinstance(cfg.get("pvp"), dict) else {}
    return float(social.get("rake_percent") or 5.0) / 100.0


def create_pvp_duel(
    user_id: str,
    bet: float,
    game: str = "coin_flip",
    choice: str = "",
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = _normalize_currency(currency)
    game = (game or "coin_flip").strip().lower()
    if game not in ("coin_flip", "rps", "dice"):
        return {"success": False, "error": "game must be coin_flip, rps, or dice"}
    pick = (choice or "").strip().lower()
    if game == "coin_flip" and pick not in ("heads", "tails"):
        return {"success": False, "error": "choice must be heads or tails"}
    if game == "rps" and pick not in _RPS_MOVES:
        return {"success": False, "error": f"choice must be one of {_RPS_MOVES}"}
    if game == "dice" and pick not in ("high", "low"):
        return {"success": False, "error": "choice must be high or low"}
    err = _validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = _parse_bet_amount(bet, currency) or 0
    _apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "challenger"})
    duel_id = str(uuid.uuid4())
    duel = {
        "duel_id": duel_id,
        "game": game,
        "bet": amount,
        "currency": currency,
        "challenger_id": user_id,
        "challenger_choice": pick,
        "acceptor_id": None,
        "acceptor_choice": None,
        "status": "open",
        "created_at": _iso(),
    }
    duels = _load_duels()
    duels[duel_id] = duel
    _save_duels(duels)
    return {"success": True, "duel": {**duel, "challenger_choice": None}}


def accept_pvp_duel(user_id: str, duel_id: str, choice: str = "") -> Dict[str, Any]:
    from backend.services import casino_rng

    duels = _load_duels()
    duel = duels.get(duel_id)
    if not isinstance(duel, dict):
        return {"success": False, "error": "Duel not found"}
    if duel.get("status") != "open":
        return {"success": False, "error": "Duel is not open"}
    if duel.get("challenger_id") == user_id:
        return {"success": False, "error": "Cannot accept your own duel"}
    currency = _normalize_currency(duel.get("currency"))
    amount = _parse_bet_amount(duel.get("bet"), currency) or 0
    game = duel.get("game")
    pick = (choice or "").strip().lower()
    if game == "coin_flip":
        if pick not in ("heads", "tails"):
            return {"success": False, "error": "choice must be heads or tails"}
        if pick == duel.get("challenger_choice"):
            return {"success": False, "error": "Pick the opposite side from the challenger"}
    elif game == "rps":
        if pick not in _RPS_MOVES:
            return {"success": False, "error": f"choice must be one of {_RPS_MOVES}"}
    elif game == "dice":
        if pick not in ("high", "low"):
            return {"success": False, "error": "choice must be high or low"}
        opp = "low" if pick == "high" else "high"
        if pick == duel.get("challenger_choice"):
            return {"success": False, "error": f"Pick {opp} — challenger took {pick}"}
    else:
        return {"success": False, "error": "Unknown duel game"}

    err = _validate_bet(user_id, amount, currency)
    if err:
        return {"success": False, "error": err}
    _apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "acceptor"})

    proof = casino_rng.draw(user_id)
    challenger = duel["challenger_id"]
    c_choice = duel["challenger_choice"]
    pot = amount * 2
    rake = round(pot * _duel_rake(), 8 if currency == "mn2" else 2)
    prize = _round_payout(pot - rake, currency)
    winner_id = None
    result_detail: Dict[str, Any] = {"fairness": {"server_seed_hash": proof["server_seed_hash"], "client_seed": proof["client_seed"], "nonce": proof["nonce"]}}

    if game == "coin_flip":
        outcome_face = "heads" if proof["float"] < 0.5 else "tails"
        result_detail["result"] = outcome_face
        if c_choice == outcome_face:
            winner_id = challenger
        elif pick == outcome_face:
            winner_id = user_id
        result_detail["challenger_choice"] = c_choice
        result_detail["acceptor_choice"] = pick
    elif game == "rps":
        if _RPS_BEATS.get(pick) == c_choice:
            winner_id = user_id
        elif _RPS_BEATS.get(c_choice) == pick:
            winner_id = challenger
        result_detail["challenger_choice"] = c_choice
        result_detail["acceptor_choice"] = pick
    elif game == "dice":
        roll = int(proof["float"] * 6) + 1
        result_detail["roll"] = roll
        high_wins = roll >= 4
        c_wins = (c_choice == "high" and high_wins) or (c_choice == "low" and not high_wins)
        a_wins = (pick == "high" and high_wins) or (pick == "low" and not high_wins)
        if c_wins and not a_wins:
            winner_id = challenger
        elif a_wins and not c_wins:
            winner_id = user_id
        result_detail["challenger_choice"] = c_choice
        result_detail["acceptor_choice"] = pick

    if winner_id:
        _apply_balance_delta(winner_id, prize, currency, "pvp_duel", {"phase": "payout", "duel_id": duel_id})
        outcome = "win"
    else:
        # tie — refund both minus rake split
        half = _round_payout((pot - rake) / 2, currency)
        _apply_balance_delta(challenger, half, currency, "pvp_duel", {"phase": "refund", "duel_id": duel_id})
        _apply_balance_delta(user_id, half, currency, "pvp_duel", {"phase": "refund", "duel_id": duel_id})
        outcome = "push"
        winner_id = None

    duel["status"] = "resolved"
    duel["acceptor_id"] = user_id
    duel["acceptor_choice"] = pick
    duel["winner_id"] = winner_id
    duel["resolved_at"] = _iso()
    duels[duel_id] = duel
    _save_duels(duels)

    for uid, role in ((challenger, "challenger"), (user_id, "acceptor")):
        net = prize - amount if winner_id == uid else (-amount if winner_id else -rake / 2)
        if winner_id is None:
            net = half - amount
        row = {
            "bet_id": str(uuid.uuid4()),
            "user_id": uid,
            "game": "pvp_duel",
            "bet": amount,
            "currency": currency,
            "outcome": outcome if (winner_id == uid or winner_id is None) else "loss",
            "payout": prize if winner_id == uid else (half if winner_id is None else 0),
            "net": net,
            "details": {**result_detail, "duel_id": duel_id, "role": role, "game_type": game},
            "created_at": _iso(),
            "exclude_leaderboard": False,
            "parent_bet_id": None,
            "double_step": 0,
        }
        _append_ledger(row)

    try:
        from backend.services import casino_competition_service
        loser = None
        if winner_id:
            loser = user_id if winner_id == challenger else challenger
        casino_competition_service.on_duel_settled(winner_id, loser, challenger, user_id)
    except Exception:
        pass

    return {
        "success": True,
        "duel_id": duel_id,
        "winner_id": winner_id,
        "prize": prize if winner_id else None,
        "rake": rake,
        "outcome": outcome,
        "details": result_detail,
        "balance": _user_balance(user_id, currency),
    }


def list_pvp_duels(status: str = "open") -> Dict[str, Any]:
    duels = _load_duels()
    status = (status or "open").lower()
    rows = []
    for d in duels.values():
        if not isinstance(d, dict):
            continue
        if status != "all" and d.get("status") != status:
            continue
        pub = {k: v for k, v in d.items() if k != "challenger_choice"}
        rows.append(pub)
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"success": True, "duels": rows, "count": len(rows)}


# ---------------------------------------------------------------------------
# Tournaments — thin wrappers over the casino_tournaments module
# ---------------------------------------------------------------------------

def list_tournaments(user_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_tournaments
    return casino_tournaments.list_tournaments(user_id=user_id)


def get_tournament(tournament_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_tournaments
    return casino_tournaments.get_tournament(tournament_id, user_id=user_id)


def join_tournament(user_id: str, tournament_id: str) -> Dict[str, Any]:
    from backend.services import casino_tournaments
    return casino_tournaments.join_tournament(user_id, tournament_id)


def reconcile_tournaments() -> Dict[str, Any]:
    from backend.services import casino_tournaments
    return casino_tournaments.reconcile()


def get_progression(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_progression
    return casino_progression.get_profile(user_id)


def get_achievements(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_progression
    return casino_progression.list_achievements(user_id)


def spin_daily_wheel(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_progression
    return casino_progression.spin_daily_wheel(user_id)


def get_shop_catalog(user_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_shop_service
    return casino_shop_service.list_catalog(user_id)


def get_shop_owned(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_shop_service
    return casino_shop_service.list_owned(user_id)


def purchase_shop_item(user_id: str, item_id: str, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_shop_service
    return casino_shop_service.purchase(user_id, item_id, currency)


def get_casino_trophies(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_trophies_service
    return casino_trophies_service.list_trophies(user_id)


def get_rival_board(user_id: str, period: str = "week", currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_competition_service
    return casino_competition_service.get_rival_board(user_id, period=period, currency=currency)


def get_achievement_races(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_competition_service
    return casino_competition_service.get_achievement_races(user_id)


def get_crew_casino_leaderboard(user_id: str, currency: str = "coins") -> Dict[str, Any]:
    from backend.services import casino_competition_service
    return casino_competition_service.get_crew_casino_leaderboard(user_id, currency=currency)
