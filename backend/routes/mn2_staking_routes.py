"""
MN2 staking API routes.

User parity endpoints (resolve user via session > query > body, like other MN2 routes)
plus ops accrual. See docs/MN2_STAKING_PLAN.md and docs/AGENTS_MN2.md.
"""
import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.mn2_staking_service as staking

mn2_staking_bp = Blueprint("mn2_staking", __name__)


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Scanner-Token")
        or request.args.get("token")
        or ""
    ).strip()
    return token == secret


def _body() -> dict:
    return request.get_json(silent=True) or {}


@mn2_staking_bp.route("/api/mn2/staking/config", methods=["GET"])
def staking_config():
    try:
        cfg = staking.get_config()
        public = {
            "success": True,
            "enabled": cfg.get("enabled"),
            "min_stake": cfg.get("min_stake"),
            "max_stake_per_user": cfg.get("max_stake_per_user"),
            "instant_unstake": cfg.get("instant_unstake"),
            "apr_percent": staking.dynamic_apr(),
            "longevity_tiers": cfg.get("longevity_tiers"),
            "accrual_interval_minutes": cfg.get("accrual_interval_minutes"),
            "terms_version": cfg.get("terms_version"),
            "disclaimer": cfg.get("disclaimer"),
        }
        return jsonify(public), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/terms", methods=["GET"])
def staking_terms():
    try:
        return jsonify({"success": True, "terms": staking.get_terms()}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/accept-terms", methods=["POST"])
def staking_accept_terms():
    try:
        user_id = resolve_user_id(from_body=True, from_query=True)
        version = (_body().get("version") or request.args.get("version") or "").strip() or None
        result = staking.accept_terms(user_id, version)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/status", methods=["GET"])
def staking_status():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        return jsonify({"success": True, **staking.get_stake(user_id)}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/stake", methods=["POST"])
def staking_stake():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = staking.stake(user_id, data.get("amount"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/unstake", methods=["POST"])
def staking_unstake():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = staking.unstake(user_id, data.get("amount"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/auto-compound", methods=["POST"])
def staking_auto_compound():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        enabled = data.get("enabled")
        if enabled is None:
            enabled = request.args.get("enabled", "true").lower() in ("1", "true", "yes")
        result = staking.set_auto_compound(user_id, bool(enabled))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/work", methods=["POST"])
def staking_work():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = staking.submit_work_proof(
            user_id,
            proof=data.get("proof"),
            nonce=data.get("nonce"),
            ts=data.get("ts"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/calculator", methods=["GET"])
def staking_calculator():
    try:
        return jsonify(staking.estimate_rewards(
            amount=request.args.get("amount", 0),
            days=request.args.get("days", 30),
            uptime=request.args.get("uptime", 1.0),
            boost=request.args.get("boost", 1.0),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/rewards-table", methods=["GET"])
def staking_rewards_table():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        limit = int(request.args.get("limit", 100))
        since = (request.args.get("from") or "").strip() or None
        result = staking.get_rewards_table(user_id, limit=limit, since_iso=since)
        if (request.args.get("format") or "").lower() == "csv":
            import csv
            import io
            from flask import Response
            cols = ["accrued_at", "interval_id", "staked", "longevity_tier", "longevity_mult",
                    "uptime_ratio", "boost_mult", "referral_mult", "effective_apr", "pool_share_pct",
                    "reward_mn2", "compounded_mn2", "cumulative_earned_mn2", "balance_after_mn2", "source"]
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for row in result.get("rows", []):
                writer.writerow(row)
            return Response(
                buf.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=mn2_staking_rewards.csv"},
            )
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/leaderboard", methods=["GET"])
def staking_leaderboard():
    try:
        limit = int(request.args.get("limit", 10))
        return jsonify(staking.get_staking_leaderboard(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/monitor", methods=["GET"])
def staking_monitor():
    try:
        limit = int(request.args.get("limit", 50))
        return jsonify(staking.get_staking_monitor(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/network-overview", methods=["GET"])
def network_overview():
    try:
        from backend.services import mn2_chainz
        overview = mn2_chainz.network_overview()
        overview["pool_total_staked"] = staking.total_staked()
        overview["pool_apr_percent"] = staking.dynamic_apr()
        try:
            from backend.services import mn2_onramp_service
            overview["onramp"] = mn2_onramp_service.onramp_stats()
        except Exception:
            overview["onramp"] = None
        try:
            from backend.services import mn2_p2p_service
            overview["p2p"] = mn2_p2p_service.p2p_stats()
        except Exception:
            overview["p2p"] = None
        return jsonify({"success": True, **overview}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/ops/accrue", methods=["POST", "GET"])
def staking_ops_accrue():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        force = request.args.get("force", "").lower() in ("1", "true", "yes")
        result = staking.accrue_rewards(force=force)
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
