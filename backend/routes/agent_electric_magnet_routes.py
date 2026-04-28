"""
Electric Magnet Routes
API endpoints for Electric Magnet agent technology (12 improvements + verification & DNA test specials)
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_techs.agent_electric_magnet import agent_electric_magnet

agent_electric_magnet_bp = Blueprint("agent_electric_magnet", __name__)

# ========== STATUS & METRICS ==========


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/status", methods=["GET"])
def get_agent_electric_magnet_status():
    """Get Electric Magnet status (includes specials)"""
    try:
        status = agent_electric_magnet.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/metrics", methods=["GET"])
def get_agent_electric_magnet_metrics():
    """Get Electric Magnet metrics"""
    try:
        metrics = agent_electric_magnet.get_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== IMPROVEMENT FUNCTIONS ==========

_IMPROVEMENTS = [
    "optimize_performance",
    "enhance_security",
    "improve_reliability",
    "scale_capacity",
    "reduce_latency",
    "increase_throughput",
    "add_monitoring",
    "enable_auto_recovery",
    "improve_caching",
    "enhance_logging",
    "add_analytics",
    "upgrade_algorithm",
]


def _improvement_route(fn: str):
    def handler():
        try:
            data = request.get_json() or {}
            user_id = data.get("user_id", "default_user")
            params = data.get("params", {})
            method = getattr(agent_electric_magnet, fn)
            result = method(user_id, params)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    handler.__name__ = f"agent_electric_magnet_{fn}"
    return handler


for _fn in _IMPROVEMENTS:
    _handler = _improvement_route(_fn)
    agent_electric_magnet_bp.add_url_rule(
        f"/api/agent-tech/agent_electric_magnet/{_fn}",
        f"agent_electric_magnet_{_fn}",
        _handler,
        methods=["POST"],
    )
    agent_electric_magnet_bp.add_url_rule(
        f"/api/agent-tech/agent_electric_magnet/{_fn}",
        f"agent_electric_magnet_{_fn}_vid",
        _handler,
        methods=["POST"],
    )


# ========== SPECIALS: Verification & DNA Test ==========


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/run_verification", methods=["POST"])
def agent_electric_magnet_run_verification():
    """Execute run_verification special"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "default_user")
        params = data.get("params", {})
        result = agent_electric_magnet.run_verification(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/run_dna_test", methods=["POST"])
def agent_electric_magnet_run_dna_test():
    """Execute run_dna_test special"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "default_user")
        params = data.get("params", {})
        result = agent_electric_magnet.run_dna_test(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/view_star_map", methods=["GET", "POST"])
def agent_electric_magnet_view_star_map():
    """Execute view_star_map special – 7 nearest stars, planets, life-bearing b"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", request.args.get("user_id", "default_user"))
        params = data.get("params", {})
        result = agent_electric_magnet.view_star_map(user_id, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== DOWNLOAD & EXECUTE ==========


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/download", methods=["POST", "GET"])
def agent_electric_magnet_download():
    """Download Electric Magnet technology (ensure enabled)"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", request.args.get("user_id", "default_user"))
        
        # Mark as downloaded and increment download_count
        agent_electric_magnet.data["downloaded"] = True
        agent_electric_magnet.data["status"] = "active"
        m = agent_electric_magnet.data.setdefault("metrics", {})
        m["download_count"] = m.get("download_count", 0) + 1
        m["total_operations"] = m.get("total_operations", 0) + 1
        agent_electric_magnet.save_data()
        
        # Award unified points for downloading tech
        try:
            from backend.services.agent_trigger_system import agent_trigger_system
            # Use 'run_verification' trigger as a proxy for tech download (or create new trigger)
            # Award points for downloading Electric Magnet tech
            agent_trigger_system.award_points("run_verification", user_id, {
                "source": "electric_magnet_download",
                "action": "download_tech",
                "tech_id": "agent_electric_magnet"
            })
        except Exception as trigger_error:
            # Don't fail download if points trigger fails
            print(f"[Electric Magnet] Points trigger error: {trigger_error}")
        
        m = agent_electric_magnet.data.get("metrics", {})
        return (
            jsonify(
                {
                    "success": True,
                    "tech_id": "agent_electric_magnet",
                    "tech_name": "Electric Magnet",
                    "downloaded": True,
                    "specials": agent_electric_magnet.specials,
                    "user_id": user_id,
                    "download_count": m.get("download_count", 0),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_electric_magnet_bp.route("/api/agent-tech/agent_electric_magnet/execute", methods=["POST"])
def execute_agent_electric_magnet():
    """Execute Electric Magnet action"""
    try:
        data = request.get_json() or {}
        action = data.get("action", "default")
        params = data.get("params", {})
        result = agent_electric_magnet.execute(action, params)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
