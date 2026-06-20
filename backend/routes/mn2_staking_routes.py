"""
MN2 staking API routes.

User parity endpoints (resolve user via session > query > body, like other MN2 routes)
plus ops accrual. See docs/MN2_STAKING_PLAN.md and docs/AGENTS_MN2.md.
"""
import os
import json
import time
from flask import Blueprint, jsonify, request, Response, stream_with_context

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


@mn2_staking_bp.route("/api/mn2/staking/goal-planner", methods=["GET"])
def staking_goal_planner():
    """Reach X MN2 by date → required stake estimate (Top-10 #10)."""
    try:
        return jsonify(staking.goal_planner(
            target_mn2=request.args.get("target_mn2", 0),
            target_date=request.args.get("target_date", ""),
            current_mn2=request.args.get("current_mn2", 0),
            uptime=request.args.get("uptime", 1.0),
            boost=request.args.get("boost", 1.0),
        )), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_staking_bp.route("/api/mn2/staking/notification-prefs", methods=["GET", "POST"])
def staking_notification_prefs():
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.mn2_staking_notifications import get_prefs, set_prefs
    if request.method == "GET":
        return jsonify({"success": True, "user_id": user_id, "prefs": get_prefs(user_id)}), 200
    data = _body()
    allowed = {"reward_alerts", "weekly_digest", "large_reward_mn2"}
    updates = {k: data[k] for k in allowed if k in data}
    return jsonify(set_prefs(user_id, updates)), 200


@mn2_staking_bp.route("/api/mn2/staking/leaderboard-settings", methods=["GET", "POST"])
def staking_leaderboard_settings():
    """Opt-in public leaderboard + display name (Top-10 #7)."""
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.user_engagement import get_settings, update_settings
    if request.method == "GET":
        s = get_settings(user_id).get("settings") or {}
        return jsonify({
            "success": True,
            "staking_leaderboard_opt_in": bool(s.get("staking_leaderboard_opt_in")),
            "staking_display_name": s.get("staking_display_name") or "",
            "staking_show_amounts": bool(s.get("staking_show_amounts")),
        }), 200
    data = _body()
    updates = {}
    if "staking_leaderboard_opt_in" in data:
        updates["staking_leaderboard_opt_in"] = bool(data["staking_leaderboard_opt_in"])
    if "staking_display_name" in data:
        updates["staking_display_name"] = str(data["staking_display_name"] or "")[:32]
    if "staking_show_amounts" in data:
        updates["staking_show_amounts"] = bool(data["staking_show_amounts"])
    return jsonify(update_settings(user_id, updates)), 200


@mn2_staking_bp.route("/api/mn2/staking/share-card", methods=["GET"])
def staking_share_card():
    """Simple SVG share card — no yield promises (Top-10 #7)."""
    from flask import Response
    user_id, err = _resolve_owner()
    if err:
        return err
    status = staking.get_stake(user_id)
    staked = round(float(status.get("staked") or 0), 4)
    tier = status.get("longevity_label") or status.get("longevity_tier") or "Bronze"
    days = round(float(status.get("longevity_days") or 0), 1)
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="315" viewBox="0 0 600 315">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#0a1628"/><stop offset="100%" stop-color="#0d3320"/>'
        '</linearGradient></defs>'
        '<rect width="600" height="315" fill="url(#g)"/>'
        '<text x="40" y="70" fill="#00d4ff" font-family="system-ui,sans-serif" font-size="28" font-weight="700">MN2 Staker</text>'
        f'<text x="40" y="130" fill="#ffffff" font-family="system-ui,sans-serif" font-size="22">Staking {staked} MN2</text>'
        f'<text x="40" y="175" fill="#00ff88" font-family="system-ui,sans-serif" font-size="18">{tier} · {days} days</text>'
        '<text x="40" y="260" fill="#8899aa" font-family="system-ui,sans-serif" font-size="14">'
        'masternoder.dk · Rewards variable, not guaranteed</text>'
        '</svg>'
    )
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "private, max-age=60"})


@mn2_staking_bp.route("/api/mn2/staking/team", methods=["GET"])
def staking_team_get():
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.mn2_staking_teams import get_team_for_user
    return jsonify(get_team_for_user(user_id)), 200


@mn2_staking_bp.route("/api/mn2/staking/team/create", methods=["POST"])
def staking_team_create():
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.mn2_staking_teams import create_team
    data = _body()
    return jsonify(create_team(user_id, data.get("name") or "")), 200


@mn2_staking_bp.route("/api/mn2/staking/team/join", methods=["POST"])
def staking_team_join():
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.mn2_staking_teams import join_team
    data = _body()
    code = (data.get("code") or data.get("invite_code") or "").strip()
    result = join_team(user_id, code)
    return jsonify(result), 200 if result.get("success") else 400


@mn2_staking_bp.route("/api/mn2/staking/team/leave", methods=["POST"])
def staking_team_leave():
    user_id, err = _resolve_owner()
    if err:
        return err
    from backend.services.mn2_staking_teams import leave_team
    return jsonify(leave_team(user_id)), 200


@mn2_staking_bp.route("/api/mn2/staking/teams/leaderboard", methods=["GET"])
def staking_teams_leaderboard():
    try:
        from backend.services.mn2_staking_teams import team_leaderboard
        limit = int(request.args.get("limit", 20))
        return jsonify(team_leaderboard(limit=limit)), 200
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
            from backend.services.mn2_explorer_urls import explorer_kind
            overview["explorer_base_url"] = _explorer_base_url()
            overview["explorer_kind"] = explorer_kind()
        except Exception:
            overview["explorer_base_url"] = None
            overview["explorer_kind"] = None
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
        try:
            from backend.services.mn2_rpc_failover import status_summary
            fo = status_summary()
            overview["rpc_failover"] = fo
            if fo.get("enabled") and fo.get("active") == "standby":
                overview["rpc_degraded"] = True
        except Exception:
            overview["rpc_failover"] = None
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


@mn2_staking_bp.route("/api/mn2/explorer/stream", methods=["GET"])
def explorer_overview_stream():
    """SSE push of network-overview tiles (poll fallback remains in mn2-explorer-overview.js)."""
    interval = max(10, min(int(request.args.get("interval", 30)), 120))

    def generate():
        yield "data: " + json.dumps({"type": "connected", "interval_sec": interval}) + "\n\n"
        last_sig = None
        while True:
            try:
                from backend.services import mn2_chainz
                overview = mn2_chainz.network_overview()
                overview["pool_total_staked"] = staking.total_staked()
                overview["pool_apr_percent"] = staking.dynamic_apr()
                payload = {"success": True, **overview}
                sig = json.dumps(payload, sort_keys=True, default=str)
                if sig != last_sig:
                    last_sig = sig
                    yield "data: " + json.dumps({"type": "overview", "data": payload, "ts": time.time()}) + "\n\n"
                else:
                    yield "data: " + json.dumps({"type": "heartbeat", "ts": time.time()}) + "\n\n"
            except Exception as exc:
                yield "data: " + json.dumps({"type": "error", "error": str(exc)}) + "\n\n"
            time.sleep(interval)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


@mn2_staking_bp.route("/api/mn2/staking/ops/weekly-digest", methods=["POST", "GET"])
def staking_ops_weekly_digest():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_staking_notifications import run_weekly_digest
        force = request.args.get("force", "").lower() in ("1", "true", "yes")
        return jsonify(run_weekly_digest(force=force)), 200
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
