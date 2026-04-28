"""
DNA Monster Calendar Routes (Restored Source)
Endpoints for DNA manipulation and cloning actions.

This file used to exist (pyc present) but sources were missing; recreated to match expected URLs.
"""
from flask import Blueprint, jsonify, request

from backend.services.dna_manipulation_system import dna_manipulation_system


dna_monster_calendar_bp = Blueprint("dna_monster_calendar", __name__)


@dna_monster_calendar_bp.route("/dna/manipulate", methods=["POST"])
@dna_monster_calendar_bp.route("/vidgenerator/dna/manipulate", methods=["POST"])
@dna_monster_calendar_bp.route("/api/dna/manipulate", methods=["POST"])
def dna_manipulate():
    data = request.get_json() or {}
    user_id = data.get("user_id", "default_user")
    intensity = data.get("intensity", 1)
    meta = data.get("metadata") or {}
    try:
        result = dna_manipulation_system.dna_manipulation(user_id=user_id, intensity=intensity, metadata=meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dna_monster_calendar_bp.route("/dna/giga-clone", methods=["POST"])
@dna_monster_calendar_bp.route("/vidgenerator/dna/giga-clone", methods=["POST"])
@dna_monster_calendar_bp.route("/api/dna/clone", methods=["POST"])
def dna_clone():
    data = request.get_json() or {}
    user_id = data.get("user_id", "default_user")
    batch_size = data.get("batch_size", 1)
    meta = data.get("metadata") or {}
    try:
        result = dna_manipulation_system.dna_cloning(user_id=user_id, batch_size=batch_size, metadata=meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

