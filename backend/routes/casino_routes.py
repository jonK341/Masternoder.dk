"""
Virtual-coins casino API with optional MN2 and PayPal USD rails.
"""
import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.casino_service as casino_service


casino_bp = Blueprint("virtual_casino", __name__)


def _resolve_casino_user_id(from_body: bool = False, from_query: bool = True) -> str:
    """Use explicit user_id from the client; accept default_user without re-identification."""
    uid = None
    if from_query:
        uid = request.args.get("user_id")
    if not uid and from_body:
        data = request.get_json(silent=True) or {}
        uid = data.get("user_id")
    if uid and str(uid).strip():
        return str(uid).strip()
    return resolve_user_id(from_body=from_body, from_query=from_query)


def _currency_from_body(data: dict) -> str:
    return (data.get("currency") or "coins").strip().lower()


def _currency_from_query() -> str:
    return (request.args.get("currency") or "coins").strip().lower()


def _casino_base_url() -> str:
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


def _casino_settings_payload():
    payload = casino_service.get_public_config()
    payload["success"] = True
    return payload


@casino_bp.route("/api/casino/settings", methods=["GET"])
def casino_settings():
    try:
        return jsonify(_casino_settings_payload()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/config", methods=["GET"])
def casino_config_compat():
    """Backward-compatible alias for older clients."""
    return casino_settings()


@casino_bp.route("/api/casino/balance", methods=["GET"])
def casino_balance():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_balance(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/history", methods=["GET"])
def casino_history():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        limit = request.args.get("limit", 25)
        return jsonify(casino_service.get_history(user_id, limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/coin-flip", methods=["POST"])
def casino_coin_flip():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_coin_flip(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/dice", methods=["POST"])
def casino_dice():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_dice(
            user_id=user_id,
            bet=data.get("bet"),
            guess=data.get("guess"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/rps-bet", methods=["POST"])
def casino_rps_bet():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_rps_bet(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/battle-rps-distribution", methods=["GET"])
def casino_battle_rps_distribution():
    try:
        difficulty = request.args.get("difficulty")
        player_move = request.args.get("player_move")
        return jsonify(casino_service.get_battle_rps_distribution(
            difficulty=difficulty,
            player_move=player_move,
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/battle-outcome-distribution", methods=["GET"])
def casino_battle_outcome_distribution():
    try:
        difficulty = request.args.get("difficulty")
        return jsonify(casino_service.get_battle_outcome_distribution(difficulty=difficulty)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/rps-distribution", methods=["POST"])
def casino_rps_distribution_bet():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_rps_distribution_bet(
            user_id=user_id,
            bet=data.get("bet"),
            prediction=(data.get("prediction") or data.get("choice") or "").strip(),
            difficulty=(data.get("difficulty") or "").strip() or None,
            player_move=(data.get("player_move") or "").strip() or None,
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/quests", methods=["GET"])
def casino_quests():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_daily_quests(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/quests/claim", methods=["POST"])
def casino_quest_claim():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.claim_daily_quest(user_id, data.get("quest_id"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/leaderboard", methods=["GET"])
def casino_leaderboard():
    try:
        period = request.args.get("period", "today")
        limit = request.args.get("limit", 10)
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_leaderboard(
            period=period,
            limit=limit,
            user_id=user_id,
            currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/free-daily-bet", methods=["POST"])
def casino_free_daily_bet():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_free_daily_bet(
            user_id=user_id,
            choice=(data.get("choice") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/double-or-nothing", methods=["POST"])
def casino_double_or_nothing():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_double_or_nothing(user_id, data.get("bet_id"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/personal-bests", methods=["GET"])
def casino_personal_bests():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_personal_bests(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/hall-of-fame", methods=["GET"])
def casino_hall_of_fame():
    try:
        limit = request.args.get("limit", 3)
        return jsonify(casino_service.get_hall_of_fame(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/mystery-coin-flip", methods=["POST"])
def casino_mystery_coin_flip():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_mystery_coin_flip(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/scratch-card", methods=["POST"])
def casino_scratch_card():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_scratch_card(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/battle-outcome", methods=["POST"])
def casino_battle_outcome_bet():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_battle_outcome_bet(
            user_id=user_id,
            bet=data.get("bet"),
            prediction=(data.get("prediction") or "").strip(),
            difficulty=(data.get("difficulty") or "").strip() or None,
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/counter-pick-hint", methods=["GET"])
def casino_counter_pick_hint():
    try:
        difficulty = request.args.get("difficulty")
        player_move = request.args.get("player_move")
        return jsonify(casino_service.get_counter_pick_hint(
            difficulty=difficulty,
            player_move=player_move,
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/rps-counter-pick", methods=["POST"])
def casino_rps_counter_pick():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_rps_counter_pick(
            user_id=user_id,
            bet=data.get("bet"),
            choice=(data.get("choice") or "").strip(),
            difficulty=(data.get("difficulty") or "").strip() or None,
            player_move=(data.get("player_move") or "").strip() or None,
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/slot-classic", methods=["POST"])
def casino_slot_classic():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_slot_classic(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/slot-diamond", methods=["POST"])
def casino_slot_diamond():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_slot_diamond(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/slots", methods=["GET"])
def casino_list_slots():
    try:
        return jsonify(casino_service.list_slot_machines()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/slot", methods=["POST"])
def casino_play_slot():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        slot_id = (data.get("slot_id") or data.get("game") or "").strip()
        if not slot_id:
            return jsonify({"success": False, "error": "slot_id required"}), 400
        if not slot_id.startswith("slot_"):
            slot_id = "slot_" + slot_id
        result = casino_service.play_slot(
            user_id=user_id,
            slot_id=slot_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/crash", methods=["POST"])
def casino_crash_start():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.start_crash_round(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
            auto_cashout=data.get("auto_cashout"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/crash/cashout", methods=["POST"])
def casino_crash_cashout():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.cashout_crash_round(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
            multiplier=data.get("multiplier"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/plinko", methods=["POST"])
def casino_plinko():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_plinko(
            user_id=user_id,
            bet=data.get("bet"),
            risk=(data.get("risk") or "medium").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/wheel", methods=["POST"])
def casino_wheel():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_wheel(
            user_id=user_id,
            bet=data.get("bet"),
            risk=(data.get("risk") or "medium").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/mines", methods=["POST"])
def casino_mines_start():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.start_mines_round(
            user_id=user_id,
            bet=data.get("bet"),
            mines=data.get("mines", 3),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/mines/reveal", methods=["POST"])
def casino_mines_reveal():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.reveal_mines_tile(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
            tile=data.get("tile"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/mines/cashout", methods=["POST"])
def casino_mines_cashout():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.cashout_mines_round(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/keno", methods=["POST"])
def casino_keno():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_keno(
            user_id=user_id,
            bet=data.get("bet"),
            spots=data.get("spots") or [],
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/roulette", methods=["POST"])
def casino_roulette():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_roulette(
            user_id=user_id,
            bet=data.get("bet"),
            bet_type=(data.get("bet_type") or "").strip(),
            selection=data.get("selection"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/hilo", methods=["POST"])
def casino_hilo_start():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.start_hilo_round(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/hilo/guess", methods=["POST"])
def casino_hilo_guess():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.hilo_guess(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
            direction=(data.get("direction") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/hilo/cashout", methods=["POST"])
def casino_hilo_cashout():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.hilo_cashout(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/tournaments", methods=["GET"])
def casino_tournaments_list():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.list_tournaments(user_id=user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/tournaments/<tournament_id>", methods=["GET"])
def casino_tournament_detail(tournament_id):
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_tournament(tournament_id, user_id=user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/tournaments/join", methods=["POST"])
def casino_tournament_join():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.join_tournament(
            user_id=user_id,
            tournament_id=(data.get("tournament_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/tournaments/reconcile", methods=["GET"])
def casino_tournaments_reconcile():
    try:
        return jsonify(casino_service.reconcile_tournaments()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/fairness/seed", methods=["GET"])
def casino_fairness_seed():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_fairness_state(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/fairness/client-seed", methods=["POST"])
def casino_fairness_client_seed():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.set_fairness_client_seed(user_id, (data.get("client_seed") or "").strip())
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/fairness/rotate", methods=["POST"])
def casino_fairness_rotate():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.rotate_fairness(user_id, (data.get("client_seed") or "").strip() or None)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/fairness/verify", methods=["POST"])
def casino_fairness_verify():
    try:
        data = request.get_json(silent=True) or {}
        result = casino_service.verify_fairness(
            server_seed=(data.get("server_seed") or "").strip(),
            client_seed=(data.get("client_seed") or "").strip(),
            nonce=data.get("nonce"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/jackpots", methods=["GET"])
def casino_jackpots():
    try:
        return jsonify(casino_service.get_jackpots()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/jackpots/reconcile", methods=["GET"])
def casino_jackpots_reconcile():
    try:
        return jsonify(casino_service.reconcile_jackpots()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/activity-feed", methods=["GET"])
def casino_activity_feed():
    try:
        limit = request.args.get("limit", 12)
        currency = request.args.get("currency")
        return jsonify(casino_service.get_activity_feed(limit=limit, currency=currency)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/house-stats", methods=["GET"])
def casino_house_stats():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_house_stats(user_id, currency=_currency_from_query())), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social-mini-board", methods=["GET"])
def casino_social_mini_board():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        period = request.args.get("period", "today")
        limit = request.args.get("limit", 5)
        return jsonify(casino_service.get_social_mini_board(
            user_id=user_id,
            period=period,
            limit=limit,
            currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/paypal/deposit-packs", methods=["GET"])
def casino_paypal_deposit_packs():
    try:
        return jsonify(casino_service.get_paypal_deposit_packs()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/paypal/deposit", methods=["POST"])
def casino_paypal_deposit():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        if user_id.strip().lower() == "default_user":
            return jsonify({
                "success": False,
                "error": "Create an account first",
                "code": "ACCOUNT_REQUIRED",
            }), 400
        result = casino_service.create_paypal_deposit_order(
            user_id=user_id,
            pack_id=(data.get("pack_id") or "").strip(),
            base_url=_casino_base_url(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/paypal/capture", methods=["POST"])
def casino_paypal_capture():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        order_id = data.get("order_id") or request.args.get("token") or request.args.get("order_id")
        result = casino_service.capture_paypal_deposit(
            user_id=user_id,
            order_id=order_id,
            pack_id=(data.get("pack_id") or request.args.get("pack_id") or "").strip() or None,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/ops/income-summary", methods=["GET"])
def casino_ops_income_summary():
    import os
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if secret:
        token = (request.headers.get("X-Ops-Token") or request.args.get("token") or "").strip()
        if token != secret:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.house_income_aggregator import summarize
        hours = int(request.args.get("since_hours", 24))
        return jsonify(summarize(since_hours=hours)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/callback/bet", methods=["POST"])
def casino_callback_bet():
    """External bet callback — debit MN2/coins. Requires MN2_CALLBACK_SECRET or bypass in dev."""
    from backend.services.mn2_callback_auth import callback_authorized
    if not callback_authorized():
        return jsonify({"success": False, "error": "Unauthorized callback"}), 403
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        currency = (data.get("currency") or "mn2").strip().lower()
        bet = float(data.get("amount") or data.get("bet") or 0)
        game = (data.get("game") or "external_callback").strip()
        if not user_id or bet <= 0:
            return jsonify({"success": False, "error": "user_id and positive amount required"}), 400
        result = casino_service._finalize_bet(
            user_id, game, bet, "callback_bet", 0,
            {"callback": True, "event": "bet", **(data.get("meta") or {})},
            currency=currency,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/callback/win", methods=["POST"])
def casino_callback_win():
    """External win callback — credit MN2/coins payout."""
    from backend.services.mn2_callback_auth import callback_authorized
    if not callback_authorized():
        return jsonify({"success": False, "error": "Unauthorized callback"}), 403
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        currency = (data.get("currency") or "mn2").strip().lower()
        payout = float(data.get("amount") or data.get("payout") or 0)
        bet = float(data.get("bet") or 0)
        game = (data.get("game") or "external_callback").strip()
        if not user_id or payout <= 0:
            return jsonify({"success": False, "error": "user_id and positive payout required"}), 400
        result = casino_service._finalize_bet(
            user_id, game, bet, "callback_win", payout,
            {"callback": True, "event": "win", **(data.get("meta") or {})},
            skip_stake=True,
            currency=currency,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/preferences", methods=["GET", "POST"])
def casino_social_preferences():
    """Opt-in win sharing + geo country for Discord highlights."""
    try:
        from backend.services import casino_social_service
        if request.method == "GET":
            user_id = _resolve_casino_user_id(from_body=False, from_query=True)
            return jsonify({"success": True, "preferences": casino_social_service.get_preferences(user_id)}), 200
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        cc = data.get("country_code")
        if cc is None:
            cc = request.headers.get("CF-IPCountry") or request.headers.get("X-Country-Code")
        return jsonify(
            casino_social_service.set_preferences(
                user_id,
                share_wins=data.get("share_wins") if "share_wins" in data else None,
                country_code=cc,
            )
        ), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/discord/promo/redeem", methods=["POST"])
def casino_discord_promo_redeem():
    try:
        from backend.services import casino_social_service
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        return jsonify(casino_social_service.redeem_discord_promo(user_id, data.get("code") or "")), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/news/platform", methods=["GET"])
def casino_platform_news():
    """Casino channel feed from platform_news.json."""
    try:
        from backend.routes.platform_news_routes import _load_news
        limit = request.args.get("limit", 10, type=int)
        featured_only = request.args.get("featured", "").lower() in ("1", "true", "yes")
        items = [
            i for i in _load_news()
            if (i.get("channel") or i.get("category") or "").lower() == "casino"
        ]
        if featured_only:
            items = [i for i in items if i.get("featured")]
        if limit > 0:
            items = items[:limit]
        return jsonify({"success": True, "news": items, "count": len(items), "channel": "casino"}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "news": []}), 500
