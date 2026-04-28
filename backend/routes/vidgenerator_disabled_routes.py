"""
/vidgenerator/api is disabled. All API is at /api/. Returns 410 Gone with message.
"""
from flask import Blueprint, jsonify

vidgenerator_disabled_bp = Blueprint("vidgenerator_disabled", __name__)


@vidgenerator_disabled_bp.route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@vidgenerator_disabled_bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def disabled(path=""):
    """Return 410 Gone for any /vidgenerator/api request."""
    return jsonify({
        "success": False,
        "error": "This API prefix is disabled.",
        "message": "Use /api/ instead. masternoder.dk/api is the only API base.",
        "use": "/api/",
        "status": 410,
    }), 410, {"X-API-Disabled": "vidgenerator", "Cache-Control": "public, max-age=3600"}
