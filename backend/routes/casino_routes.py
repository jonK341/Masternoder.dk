"""
Virtual-coins casino API with optional MN2 and PayPal USD rails.
"""
import json
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.casino_service as casino_service


casino_bp = Blueprint("virtual_casino", __name__)

_MARKETING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "casino_marketing.json",
)


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


def _load_casino_marketing() -> dict:
    try:
        with open(_MARKETING_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


@casino_bp.route("/api/casino/health", methods=["GET"])
def casino_health():
    return jsonify({
        "success": True,
        "service": "casino",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }), 200


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


@casino_bp.route("/api/casino/marketing", methods=["GET"])
def casino_marketing():
    """Public marketing copy, tags, and banner URLs for store listings and social."""
    try:
        payload = _load_casino_marketing()
        payload["success"] = True
        return jsonify(payload), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/balance", methods=["GET"])
def casino_balance():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_balance(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/exchange-bridge", methods=["GET"])
def casino_exchange_bridge():
    """Unified wallet strip: casino balance + exchange profit cash-out."""
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        from backend.services.exchange_user_controller_service import hub_state, load_config as ctrl_cfg

        hub = hub_state(user_id)
        pub = casino_service.get_public_config()
        rm = (pub.get("real_money") or {}) if isinstance(pub, dict) else {}
        bridge = rm.get("exchange_bridge") or {}
        ctrl = ctrl_cfg()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "bridge": bridge,
            "mn2_balance": (hub.get("balances") or {}).get("mn2", 0),
            "shop_coins": (hub.get("balances") or {}).get("coins", 0),
            "exchange_profit_usd": hub.get("cash_out_available_usd", 0),
            "rental_count": hub.get("rental_count", 0),
            "controller_url": bridge.get("exchange_page_url") or "/exchange#cex-control-center",
            "cross_promo": bridge.get("cross_promo") or ctrl.get("casino_bridge", {}).get("note", ""),
            "casino_coins_per_usd": (ctrl.get("cash_out") or {}).get("casino_coins_per_usd", 100),
        }), 200
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


@casino_bp.route("/api/casino/global/leaderboard", methods=["GET"])
def casino_global_leaderboard():
    try:
        from backend.services import casino_global_controller
        period = request.args.get("period", "today")
        limit = request.args.get("limit", 25)
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_global_controller.get_global_leaderboard(
            period=period,
            limit=limit,
            user_id=user_id,
            currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/global/stats", methods=["GET"])
def casino_global_stats():
    try:
        from backend.services import casino_global_controller
        return jsonify(casino_global_controller.get_global_stats()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/revenue/daily", methods=["GET"])
def casino_revenue_daily():
    try:
        from backend.services import casino_revenue_report
        days = request.args.get("days", 7)
        return jsonify(casino_revenue_report.daily_reports(days=days)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/revenue/report/today", methods=["GET"])
def casino_revenue_today():
    try:
        from backend.services import casino_revenue_report
        return jsonify(casino_revenue_report.today_summary()), 200
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


@casino_bp.route("/api/casino/big-wins/hall-of-fame", methods=["GET"])
def casino_big_win_hall_of_fame():
    try:
        days = request.args.get("days", 7, type=int)
        limit = request.args.get("limit", 15, type=int)
        currency = request.args.get("currency") or None
        return jsonify(casino_service.get_big_win_hall_of_fame(
            days=days, limit=limit, currency=currency,
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/slot-of-the-day", methods=["GET"])
def casino_slot_of_the_day():
    try:
        return jsonify(casino_service.get_slot_of_the_day()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/responsible-gaming/status", methods=["GET"])
def casino_responsible_gaming_status():
    try:
        from backend.services.casino_responsible_gaming import status_for_user
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        currency = _currency_from_query()
        return jsonify(status_for_user(user_id, currency)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/revenue/reconcile", methods=["GET"])
def casino_revenue_reconcile():
    try:
        from backend.services import casino_revenue_report
        day = request.args.get("day")
        return jsonify(casino_revenue_report.reconcile_check(day=day)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/shop/rtp-audit", methods=["GET"])
def casino_shop_rtp_audit():
    try:
        from backend.services import casino_shop_service
        return jsonify(casino_shop_service.audit_rtp_compliance()), 200
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


@casino_bp.route("/api/casino/play/blackjack", methods=["POST"])
def casino_blackjack_start():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.start_blackjack_round(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/blackjack/hit", methods=["POST"])
def casino_blackjack_hit():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.blackjack_hit(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/blackjack/stand", methods=["POST"])
def casino_blackjack_stand():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.blackjack_stand(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/blackjack/double", methods=["POST"])
def casino_blackjack_double():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.blackjack_double(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/baccarat", methods=["POST"])
def casino_baccarat():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.play_baccarat(
            user_id=user_id,
            bet=data.get("bet"),
            side=(data.get("side") or data.get("choice") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/video-poker", methods=["POST"])
def casino_video_poker_start():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.start_video_poker_round(
            user_id=user_id,
            bet=data.get("bet"),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/play/video-poker/draw", methods=["POST"])
def casino_video_poker_draw():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.video_poker_draw(
            user_id=user_id,
            round_id=(data.get("round_id") or "").strip(),
            hold=data.get("hold"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/progression", methods=["GET"])
def casino_progression():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_progression(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/achievements", methods=["GET"])
def casino_achievements():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_achievements(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/daily-wheel/spin", methods=["POST"])
def casino_daily_wheel_spin():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.spin_daily_wheel(user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/duels", methods=["GET"])
def casino_duels_list():
    try:
        status = request.args.get("status") or "open"
        return jsonify(casino_service.list_pvp_duels(status=status)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/duels/create", methods=["POST"])
def casino_duels_create():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.create_pvp_duel(
            user_id=user_id,
            bet=data.get("bet"),
            game=(data.get("game") or "coin_flip").strip(),
            choice=(data.get("choice") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/duels/accept", methods=["POST"])
def casino_duels_accept():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.accept_pvp_duel(
            user_id=user_id,
            duel_id=(data.get("duel_id") or "").strip(),
            choice=(data.get("choice") or "").strip(),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/shop/catalog", methods=["GET"])
def casino_shop_catalog():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_shop_catalog(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/shop/owned", methods=["GET"])
def casino_shop_owned():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_shop_owned(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/shop/purchase", methods=["POST"])
def casino_shop_purchase():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_service.purchase_shop_item(
            user_id=user_id,
            item_id=(data.get("item_id") or "").strip(),
            currency=_currency_from_body(data),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/trophies", methods=["GET"])
def casino_trophies():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_casino_trophies(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/rivals", methods=["GET"])
def casino_rivals():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        period = request.args.get("period", "week")
        return jsonify(casino_service.get_rival_board(
            user_id, period=period, currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/achievement-races", methods=["GET"])
def casino_achievement_races():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_achievement_races(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/crew-leaderboard", methods=["GET"])
def casino_crew_leaderboard():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_crew_casino_leaderboard(
            user_id, currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/crew/leaderboard", methods=["GET"])
def casino_crew_leaderboard_v2():
    """Wave 2 alias — weekly crew net leaderboard with discord guild metadata."""
    return casino_crew_leaderboard()


@casino_bp.route("/api/casino/seasonal/slots", methods=["GET"])
def casino_seasonal_slots():
    try:
        return jsonify(casino_service.get_seasonal_slots()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/vip/lounge", methods=["GET"])
def casino_vip_lounge():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_service.get_vip_lounge(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/fairness/export", methods=["GET"])
def casino_fairness_export():
    try:
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        limit = request.args.get("limit", 100, type=int)
        fmt = (request.args.get("format") or "csv").strip().lower()
        if fmt == "json":
            return jsonify(casino_service.export_fairness_audit(user_id, limit=limit)), 200
        from flask import Response
        csv_body = casino_service.fairness_audit_csv(user_id, limit=limit)
        filename = f"casino-fairness-{user_id[:16]}.csv"
        return Response(
            csv_body,
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/activity-feed/stream", methods=["GET"])
def casino_activity_feed_stream():
    """SSE stream of recent casino wins from ledger mirror — poll fallback in JS."""
    import json
    import time
    from flask import Response, request, stream_with_context

    interval = max(3, min(int(request.args.get("interval", 8)), 60))
    limit = max(3, min(int(request.args.get("limit", 12)), 50))
    currency = request.args.get("currency")
    max_ticks = request.args.get("max_ticks", type=int)

    def generate():
        yield "data: " + json.dumps({
            "type": "connected",
            "channel": "casino_wins",
            "interval_sec": interval,
        }) + "\n\n"
        last_sig = None
        tick = 0
        while True:
            try:
                payload = casino_service.get_activity_feed(limit=limit, currency=currency)
                feed = payload.get("feed") or []
                sig = json.dumps(feed[:3], sort_keys=True, default=str)
                if sig != last_sig:
                    last_sig = sig
                    yield "data: " + json.dumps({
                        "type": "wins",
                        "feed": feed,
                        "count": len(feed),
                        "ts": time.time(),
                    }) + "\n\n"
                else:
                    yield "data: " + json.dumps({"type": "heartbeat", "ts": time.time()}) + "\n\n"
            except Exception as exc:
                yield "data: " + json.dumps({"type": "error", "error": str(exc)}) + "\n\n"
            tick += 1
            if max_ticks is not None and tick >= max_ticks:
                break
            time.sleep(interval)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


@casino_bp.route("/api/casino/activity-stats", methods=["GET"])
def casino_activity_stats():
    try:
        days = request.args.get("days", 5)
        currency = request.args.get("currency")
        return jsonify(casino_service.get_activity_stats(days=days, currency=currency)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/preferences", methods=["GET", "POST"])
def casino_social_preferences():
    try:
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        if request.method == "GET":
            return jsonify(casino_service.get_casino_social_preferences(user_id)), 200
        data = request.get_json(silent=True) or {}
        result = casino_service.set_casino_social_preferences(
            user_id,
            share_wins=data.get("share_wins"),
            country_code=data.get("country_code"),
        )
        return jsonify(result), 200 if result.get("success") else 400
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


def _casino_ops_ok() -> bool:
    secret = (
        os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("MN2_SCAN_SECRET")
        or ""
    ).strip()
    if not secret:
        return False
    token = (request.headers.get("X-Ops-Secret") or request.headers.get("X-Ops-Token") or "").strip()
    if token == secret:
        return True
    return request.args.get("ops_secret") == secret or request.args.get("token") == secret


@casino_bp.route("/api/casino/mobile/config", methods=["GET"])
def casino_mobile_config():
    try:
        from backend.services import casino_social_service
        return jsonify(casino_social_service.get_mobile_config()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/links", methods=["GET"])
def casino_social_links():
    try:
        from backend.services import casino_social_service
        return jsonify(casino_social_service.get_social_links()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/share/big-win", methods=["POST"])
def casino_share_big_win():
    try:
        from backend.services import casino_social_service
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        mult = data.get("multiplier")
        result = casino_social_service.build_big_win_share(
            user_id,
            game=(data.get("game") or "").strip() or None,
            net=data.get("net"),
            currency=(data.get("currency") or "").strip() or None,
            multiplier=float(mult) if mult is not None else None,
            bet_id=(data.get("bet_id") or "").strip() or None,
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/referral", methods=["GET"])
def casino_social_referral():
    try:
        from backend.services import casino_social_service
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_social_service.get_referral_invite(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/referral/register", methods=["POST"])
def casino_social_referral_register():
    try:
        from backend.services import casino_social_service
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_social_service.register_casino_referral(
            user_id,
            data.get("referral_code") or data.get("ref") or "",
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/referral/leaderboard", methods=["GET"])
def casino_social_referral_leaderboard():
    try:
        from backend.services import casino_social_service
        limit = request.args.get("limit", 10, type=int)
        return jsonify(casino_social_service.get_referral_leaderboard(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/referral/quests", methods=["GET"])
def casino_social_referral_quests():
    try:
        from backend.services import casino_social_service
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_social_service.get_referral_quests(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/follow", methods=["GET", "POST", "DELETE"])
def casino_social_follow():
    try:
        from backend.services import casino_social_service
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        if request.method == "GET":
            period = request.args.get("period", "week")
            limit = request.args.get("limit", 5, type=int)
            currency = _currency_from_query()
            return jsonify(casino_social_service.get_top_players_to_follow(
                user_id, period=period, limit=limit, currency=currency,
            )), 200
        data = request.get_json(silent=True) or {}
        target = (data.get("target_user_id") or request.args.get("target_user_id") or "").strip()
        if request.method == "DELETE":
            return jsonify(casino_social_service.unfollow_player(user_id, target)), 200
        return jsonify(casino_social_service.follow_player(user_id, target)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/follow/list", methods=["GET"])
def casino_social_follow_list():
    try:
        from backend.services import casino_social_service
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_social_service.get_follow_state(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/feed/reactions", methods=["GET", "POST"])
def casino_social_feed_reactions():
    try:
        from backend.services import casino_social_service
        if request.method == "GET":
            raw_ids = request.args.get("item_ids") or ""
            item_ids = [x.strip() for x in raw_ids.split(",") if x.strip()] or None
            return jsonify(casino_social_service.get_feed_reactions(item_ids)), 200
        data = request.get_json(silent=True) or {}
        user_id = _resolve_casino_user_id(from_body=True, from_query=True)
        result = casino_social_service.react_to_feed_item(
            user_id,
            data.get("item_id") or data.get("bet_id") or "",
            data.get("reaction") or "",
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/social/crew-challenge", methods=["GET"])
def casino_social_crew_challenge():
    try:
        from backend.services import casino_social_service
        user_id = _resolve_casino_user_id(from_body=False, from_query=True)
        return jsonify(casino_social_service.get_crew_casino_challenge_hook(
            user_id, currency=_currency_from_query(),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


def _fanout_dry_run(data: dict) -> bool:
    """Default dry_run=True for ops/cron safety unless explicitly disabled."""
    if "dry_run" not in data:
        return True
    if data.get("dry_run") is False:
        return False
    return bool(data.get("dry_run"))


@casino_bp.route("/api/casino/discord/notify", methods=["POST"])
def casino_discord_notify():
    """Internal/cron hook — fan out pending casino events to Discord #casino."""
    if not _casino_ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    try:
        from backend.services import casino_discord_fanout
        data = request.get_json(silent=True) or {}
        result = casino_discord_fanout.run_fanout(dry_run=_fanout_dry_run(data))
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@casino_bp.route("/api/casino/news/platform", methods=["GET"])
def casino_news_platform():
    try:
        from backend.routes import platform_news_routes
        limit = request.args.get("limit", 10, type=int)
        items = platform_news_routes._load_news()
        casino_items = [i for i in items if (i.get("channel") or "") == "casino"][:limit]
        return jsonify({"success": True, "count": len(casino_items), "news": casino_items}), 200
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
