"""
MN2 staking API routes.

User parity endpoints (resolve user via session > query > body, like other MN2 routes)
plus ops accrual. See docs/MN2_STAKING_PLAN.md and docs/AGENTS_MN2.md.
"""
import os
import json
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


def _resolve_owner():
    """
    Identity for money-moving actions (stake/unstake): resolved server-side ONLY
    (session > IP/fingerprint identification). Never from a caller-supplied user_id
    in the body/query — otherwise anyone could act on another account by passing its id.
    Returns (user_id, error_response_or_None).
    """
    uid = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    if not uid or uid == "default_user":
        return None, (jsonify({
            "success": False,
            "error": "You must be signed in to perform this action.",
            "code": "auth_required",
        }), 401)
    return uid, None


@mn2_staking_bp.route("/api/mn2/staking/proof-of-reserves", methods=["GET"])
def staking_proof_of_reserves():
    """Public transparency: custodial assets vs user liabilities + coverage + reconcile (plan §20 #11)."""
    try:
        from backend.services.mn2_proof_of_reserves_service import proof_of_reserves
        force = (request.args.get("force") or "").lower() in ("1", "true", "yes")
        return jsonify(proof_of_reserves(force=force)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/yield-report", methods=["GET"])
def staking_yield_report():
    """Public transparency: realized daemon yield vs rewards paid vs site margin (plan §20 #12)."""
    try:
        from backend.services.mn2_proof_of_reserves_service import yield_report
        force = (request.args.get("force") or "").lower() in ("1", "true", "yes")
        return jsonify(yield_report(force=force)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


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
        # Server-resolved identity only: a caller cannot read another account's
        # balance/staked totals by passing ?user_id=. Falls back to identification.
        user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
        return jsonify({"success": True, **staking.get_stake(user_id)}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/stake", methods=["POST"])
def staking_stake():
    try:
        data = _body()
        user_id, err = _resolve_owner()
        if err:
            return err
        result = staking.stake(user_id, data.get("amount"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/unstake", methods=["POST"])
def staking_unstake():
    try:
        data = _body()
        user_id, err = _resolve_owner()
        if err:
            return err
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
        # Server-resolved identity only — your own reward history, not another user's.
        user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
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
            from backend.routes.mn2_routes import _explorer_base_url
            overview["explorer_base_url"] = _explorer_base_url()
        except Exception:
            overview["explorer_base_url"] = None
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
        try:
            from backend.services import mn2_rpc_client
            overview["staking_health"] = mn2_rpc_client.staking_health()
        except Exception:
            overview["staking_health"] = None
        # Record a throttled snapshot for sparklines + run stop-staking/stall alerts (best-effort).
        try:
            from backend.services import mn2_network_stats
            mn2_network_stats.record_snapshot(overview)
        except Exception:
            pass
        payload = {"success": True, **overview}
        resp = jsonify(payload)
        # Short cache + weak ETag so clients/CDNs can revalidate cheaply (E4 #4).
        import hashlib
        try:
            etag = 'W/"%s"' % hashlib.md5(
                json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            resp.headers["ETag"] = etag
            if request.headers.get("If-None-Match") == etag:
                return ("", 304, {"ETag": etag, "Cache-Control": "public, max-age=30"})
        except Exception:
            pass
        resp.headers["Cache-Control"] = "public, max-age=30"
        return resp, 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/network-history", methods=["GET"])
def network_history():
    try:
        from backend.services import mn2_network_stats
        hours = float(request.args.get("hours", 24) or 24)
        limit = int(request.args.get("limit", 500) or 500)
        rows = mn2_network_stats.get_history(hours=hours, limit=limit)
        resp = jsonify({"success": True, "history": rows, "count": len(rows)})
        resp.headers["Cache-Control"] = "public, max-age=60"
        return resp, 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/network-alerts", methods=["GET"])
def network_alerts():
    try:
        from backend.services import mn2_network_stats
        limit = int(request.args.get("limit", 20) or 20)
        return jsonify({"success": True, "alerts": mn2_network_stats.get_alerts(limit=limit)}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/recent-blocks", methods=["GET"])
def recent_blocks():
    try:
        from backend.services import mn2_explorer_data
        limit = int(request.args.get("limit", 10) or 10)
        blocks = mn2_explorer_data.recent_blocks(limit=limit)
        resp = jsonify({"success": True, "blocks": blocks, "count": len(blocks)})
        resp.headers["Cache-Control"] = "public, max-age=30"
        return resp, 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/masternodes", methods=["GET"])
def masternodes():
    try:
        from backend.services import mn2_explorer_data
        limit = int(request.args.get("limit", 50) or 50)
        data = mn2_explorer_data.masternodes(limit=limit)
        resp = jsonify({"success": True, **data})
        resp.headers["Cache-Control"] = "public, max-age=60"
        return resp, 200
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


@mn2_staking_bp.route("/api/mn2/staking/ops/reconcile", methods=["POST", "GET"])
def staking_ops_reconcile():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services import mn2_staking_reconcile_service as recon
        result = recon.reconcile()
        # 200 when the books balance, 409 (Conflict) on hard drift so monitors can alert.
        return jsonify(result), 200 if result.get("ok") else 409
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
