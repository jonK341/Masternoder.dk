"""
Rulebook V1–V16 API. Serves rulebook index, individual rulebooks, and agent context.
Agent context: aggregated agent_prompt, tech_spec, user_guide, manual for prompting agents.
See docs/RULEBOOK_READERS.md for UI readers and compendium progress.
"""
import os
import json
from flask import Blueprint, jsonify, request

rulebook_bp = Blueprint("rulebook", __name__)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.path.join(_BASE_DIR, "data")


def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _load_rulebook_data(rb):
    """Load rulebook content from data_file. Returns dict with agent fields."""
    data_file = rb.get("data_file")
    if not data_file:
        return rb
    data = _load_json(data_file)
    if data:
        return {**rb, **data}
    return rb


@rulebook_bp.route("/api/rulebooks/index", methods=["GET"])
def get_rulebook_index():
    """Return master rulebook index (catalog V1–V16)."""
    data = _load_json("rulebook_index_v15.json")
    if data:
        return jsonify({"success": True, "index": data}), 200
    return jsonify({"success": False, "error": "Index not found"}), 404


@rulebook_bp.route("/api/rulebooks/<version>", methods=["GET"])
def get_rulebook(version):
    """Return specific rulebook by version (v1, v2, v3.2, v4, ... v16)."""
    v = (version or "").lower().strip()
    if not v.startswith("v"):
        v = "v" + v
    index_data = _load_json("rulebook_index_v15.json")
    if not index_data or "rulebooks" not in index_data:
        return jsonify({"success": False, "error": "Index not found"}), 404
    for rb in index_data["rulebooks"]:
        if (rb.get("id") or rb.get("version", "").lower()) == v:
            data_file = rb.get("data_file")
            if data_file:
                data = _load_json(data_file)
                if data:
                    data["_meta"] = {"version": rb.get("version"), "url_path": rb.get("url_path"), "icon": rb.get("icon")}
                    return jsonify({"success": True, "rulebook": data}), 200
            return jsonify({"success": True, "rulebook": rb}), 200
    return jsonify({"success": False, "error": "Rulebook not found"}), 404


@rulebook_bp.route("/api/rulebooks/agent-context", methods=["GET"])
def get_agent_context():
    """
    Return agent-ready context from rulebooks (V1–V16 catalog in rulebook_index_v15.json).
    Query params:
      versions: comma-separated (e.g. v1,v4,v7) or "all" for all
      format: "prompt" (plain text for system prompt) or "json" (default)
      sections: comma-separated agent_prompt,tech_spec,user_guide,manual or "all"
    """
    versions_param = (request.args.get("versions") or "all").strip().lower()
    fmt = (request.args.get("format") or "json").strip().lower()
    sections_param = (request.args.get("sections") or "all").strip().lower()

    index_data = _load_json("rulebook_index_v15.json")
    if not index_data or "rulebooks" not in index_data:
        return jsonify({"success": False, "error": "Index not found"}), 404

    if versions_param == "all":
        versions = [rb.get("id") or rb.get("version", "").lower() for rb in index_data["rulebooks"]]
    else:
        versions = [v.strip().lower() for v in versions_param.split(",") if v.strip()]
        versions = [v if v.startswith("v") else "v" + v for v in versions]

    if sections_param == "all":
        sections = ["agent_prompt", "tech_spec", "user_guide", "manual"]
    else:
        sections = [s.strip() for s in sections_param.split(",") if s.strip()]

    result = []
    for rb in index_data["rulebooks"]:
        vid = (rb.get("id") or rb.get("version", "").lower()).replace(" ", "")
        if vid not in versions:
            continue
        full = _load_rulebook_data(rb)
        entry = {"version": rb.get("version"), "name": full.get("name", rb.get("name"))}
        for sec in sections:
            val = full.get(sec)
            if val:
                entry[sec] = val
        result.append(entry)

    if fmt == "prompt":
        lines = []
        for r in result:
            lines.append(f"\n## {r.get('name', '')} ({r.get('version', '')})\n")
            for sec in sections:
                if r.get(sec):
                    lines.append(f"### {sec}\n{r[sec]}\n")
        text = "\n".join(lines).strip()
        return text, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return jsonify({"success": True, "agent_context": result, "versions": versions, "sections": sections}), 200


_AGENT_KNOWLEDGE_FILE = os.path.join(_DATA_DIR, "agent_learning_knowledge.json")


def _load_agent_knowledge():
    if os.path.exists(_AGENT_KNOWLEDGE_FILE):
        try:
            with open(_AGENT_KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"description": "Agent-learned technology", "entries": [], "updated_at": None}


def _save_agent_knowledge(data):
    os.makedirs(_DATA_DIR, exist_ok=True)
    from datetime import datetime
    data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d")
    with open(_AGENT_KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@rulebook_bp.route("/api/rulebooks/agent-knowledge", methods=["GET"])
def get_agent_knowledge():
    """Return agent-learned knowledge for rulebooks and compendium."""
    data = _load_agent_knowledge()
    return jsonify({"success": True, "knowledge": data}), 200


@rulebook_bp.route("/api/rulebooks/agent-knowledge", methods=["POST"])
def post_agent_knowledge():
    """Append an agent-learned entry (agents with knowledge skills use this)."""
    data = _load_agent_knowledge()
    entries = data.get("entries") or []
    body = request.get_json() or {}
    entry = {
        "id": body.get("id") or f"entry_{len(entries)+1}",
        "source": body.get("source", "agent"),
        "title": body.get("title", "Learned technology"),
        "text": body.get("text", ""),
        "rulebook_ref": body.get("rulebook_ref") or [],
        "created_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d"),
    }
    entries.append(entry)
    data["entries"] = entries
    _save_agent_knowledge(data)
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('agent_knowledge', count=len(entries))
    except Exception:
        pass
    return jsonify({"success": True, "entry": entry}), 201
