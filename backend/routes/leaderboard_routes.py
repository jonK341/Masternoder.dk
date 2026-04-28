"""
Leaderboard Routes — AI-powered rankings, insights, and rivalries.

Endpoints:
  GET  /api/leaderboard                    — full leaderboard (XP-ranked)
  GET  /api/leaderboard/all                — alias for UI; rows include points + username
  GET  /api/leaderboard/categories         — system selector (all, xp, generation, …)
  GET  /api/leaderboard/<system>           — per-system ranking (after static routes)
  GET  /api/leaderboard/top10              — top 10 players
  GET  /api/leaderboard/ai-insights        — Gemini analysis of leaderboard trends
  GET  /api/leaderboard/player/<user_id>   — player rank + AI-generated profile blurb
  POST /api/leaderboard/rivalry            — generate AI rivalry narrative between two players
"""
import hashlib
from flask import Blueprint, jsonify, request

leaderboard_bp = Blueprint("leaderboard", __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(val, default: int = 0) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _get_all_players() -> list:
    """Get all ranked players from the points DB."""
    players = []
    try:
        from backend.services.unified_points_database import unified_points_db
        all_data = unified_points_db.get_all_users_points()
        if all_data:
            for uid, data in all_data.items():
                if not isinstance(data, dict):
                    continue
                xp = _safe_int(data.get("xp_total", data.get("xp", 0)))
                level = _safe_int(data.get("level", 1), 1)
                sysd = data.get("systems", {})
                if not isinstance(sysd, dict):
                    sysd = {}
                players.append({
                    "user_id":    uid,
                    "xp":         xp,
                    "level":      level,
                    "rank":       0,
                    "display_name": _display_name(uid),
                    "systems":    sysd,
                })
    except Exception:
        pass

    if not players:
        # Seed with platform-level stats if no real players yet
        players = [
            {"user_id": "hunter_alpha",  "xp": 12500, "level": 8,  "rank": 0, "display_name": "Hunter Alpha",  "systems": {}},
            {"user_id": "creator_01",    "xp": 9800,  "level": 6,  "rank": 0, "display_name": "Creator Prime",  "systems": {}},
            {"user_id": "noder_master",  "xp": 7200,  "level": 5,  "rank": 0, "display_name": "NoderMaster",    "systems": {}},
            {"user_id": "video_wizard",  "xp": 5500,  "level": 4,  "rank": 0, "display_name": "VideoWizard",    "systems": {}},
            {"user_id": "battle_king",   "xp": 3100,  "level": 3,  "rank": 0, "display_name": "BattleKing",     "systems": {}},
        ]

    players.sort(key=lambda p: (p["xp"], p["level"]), reverse=True)
    for i, p in enumerate(players):
        p["rank"] = i + 1
        p["badge"] = ["👑", "🥈", "🥉"][i] if i < 3 else "⚔️"
    return players


def _display_name(uid: str) -> str:
    """Generate a consistent display name from user_id."""
    h = int(hashlib.md5(uid.encode()).hexdigest()[:4], 16)
    nouns   = ["Hunter", "Master", "Creator", "Wizard", "Noder", "Coder", "Seeker", "Ranger"]
    adjectives = ["Alpha", "Prime", "Ultra", "Swift", "Dark", "Neon", "Gold", "Elite"]
    return adjectives[h % len(adjectives)] + " " + nouns[(h // len(adjectives)) % len(nouns)]


def _points_for_system(player: dict, system_id: str) -> int:
    """Score used for sorting a non-XP leaderboard column."""
    sysd = player.get("systems") or {}
    if not isinstance(sysd, dict):
        sysd = {}
    sid = (system_id or "all").lower()
    if sid in ("all", "xp"):
        return _safe_int(player.get("xp", 0))
    if sid == "activity":
        return _safe_int(sysd.get("activity_points", 0))
    if sid == "battle":
        return _safe_int(sysd.get("battle_points", 0) or sysd.get("competition_points", 0))
    if sid == "trophies":
        return _safe_int(sysd.get("trophy_points", 0) or sysd.get("trophies", 0))
    if sid == "generation":
        return _safe_int(sysd.get("generation_points", 0))
    return _safe_int(player.get("xp", 0))


def _normalize_leaderboard_row(p: dict, points: int) -> dict:
    """Shape expected by leaderboards/index.html (points, username, user_id, rank)."""
    row = dict(p)
    pt = _safe_int(points)
    row["points"] = pt
    row["total_points"] = pt
    row["username"] = p.get("display_name") or p.get("user_id")
    return row


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@leaderboard_bp.route("/api/leaderboard/all", methods=["GET"])
def leaderboard_all():
    """Alias for UI: full board with normalized rows. ?limit=&offset=&timeframe= (timeframe ignored for now)."""
    try:
        limit = min(1000, int(request.args.get("limit", 200)))
        offset = max(0, int(request.args.get("offset", 0)))
        players = _get_all_players()
        total = len(players)
        page = players[offset : offset + limit]
        lb = [_normalize_leaderboard_row(p, _safe_int(p.get("xp", 0))) for p in page]
        return jsonify({"success": True, "leaderboard": lb, "total": total, "system": "all"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leaderboard_bp.route("/api/leaderboard/categories", methods=["GET"])
def leaderboard_categories():
    """System selector cards for /leaderboards page."""
    return jsonify({
        "success": True,
        "categories": [
            {"id": "all", "name": "All Systems", "icon": "🌟"},
            {"id": "xp", "name": "XP Points", "icon": "⭐"},
            {"id": "generation", "name": "Generation", "icon": "🎬"},
            {"id": "activity", "name": "Activity", "icon": "🔥"},
            {"id": "battle", "name": "Battle", "icon": "⚔️"},
            {"id": "trophies", "name": "Trophies", "icon": "🏆"},
        ],
    }), 200


@leaderboard_bp.route("/api/leaderboard", methods=["GET"])
def leaderboard_full():
    """Full leaderboard ranked by XP. ?limit=50&offset=0"""
    try:
        limit  = min(200, int(request.args.get("limit",  50)))
        offset = max(0,   int(request.args.get("offset", 0)))
        players = _get_all_players()
        total   = len(players)
        page    = players[offset: offset + limit]
        return jsonify({
            "success": True,
            "leaderboard": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leaderboard_bp.route("/api/leaderboard/top10", methods=["GET"])
def leaderboard_top10():
    """Top 10 players with AI-generated one-line achievement summary (Groq, cached)."""
    try:
        players = _get_all_players()[:10]

        # Add quick achievement summary per player (speed tier — Groq)
        try:
            from backend.services.llm_service import chat as llm_chat
            top3 = players[:3]
            names = ", ".join(f"{p['display_name']} (lvl {p['level']}, {p['xp']} XP)" for p in top3)
            resp = llm_chat(
                messages=[{"role": "user", "content":
                    f"Write ONE epic sentence about the top 3 leaderboard champions: {names}. "
                    "Max 20 words. Make it dramatic and motivating."}],
                task_type="speed",
                max_tokens=60,
                temperature=0.9,
            )
            if resp.success:
                for p in players:
                    p["ai_note"] = resp.content.strip() if p["rank"] <= 3 else None
        except Exception:
            pass

        return jsonify({"success": True, "top10": players, "total_players": len(_get_all_players())}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leaderboard_bp.route("/api/leaderboard/ai-insights", methods=["GET"])
def leaderboard_ai_insights():
    """
    AI analysis of leaderboard trends using Gemini.
    Returns meta-insights: who's rising, dominant strategies, predictions.
    """
    try:
        players = _get_all_players()[:20]
        if not players:
            return jsonify({"success": False, "error": "No players found"}), 200

        summary = "\n".join(
            f"#{p['rank']} {p['display_name']}: level {p['level']}, {p['xp']} XP"
            for p in players[:10]
        )

        from backend.services.llm_service import chat as llm_chat
        resp = llm_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the AI analyst for MasterNoder.dk leaderboard. "
                        "Analyse player data and return JSON with these keys: "
                        "dominant_strategy (str), rising_star (str), prediction (str), "
                        "meta_tip (str — advice for players wanting to climb), "
                        "power_gap (str — analysis of gap between #1 and #2), "
                        "fun_fact (str — interesting observation about the top 10)."
                        " Respond ONLY with valid JSON."
                    ),
                },
                {"role": "user", "content": f"Leaderboard top 10:\n{summary}"},
            ],
            task_type="reason",
            max_tokens=500,
            temperature=0.7,
        )

        insights = {}
        if resp.success:
            raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            try:
                import json as _json
                insights = _json.loads(raw)
            except Exception:
                insights = {"raw": resp.content}

        return jsonify({
            "success": True,
            "total_players": len(players),
            "insights": insights,
            "provider": resp.provider if resp.success else None,
            "top3_snapshot": players[:3],
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leaderboard_bp.route("/api/leaderboard/player/<user_id>", methods=["GET"])
def leaderboard_player(user_id):
    """Player rank + AI-generated profile blurb."""
    try:
        players = _get_all_players()
        player  = next((p for p in players if p["user_id"] == user_id), None)

        if not player:
            return jsonify({"success": False, "error": "Player not found"}), 200

        # Quick AI blurb
        blurb = ""
        try:
            from backend.services.llm_service import chat as llm_chat
            resp = llm_chat(
                messages=[{"role": "user", "content":
                    f"Write a 1-sentence epic description for a game player: "
                    f"rank #{player['rank']}, level {player['level']}, {player['xp']} XP. "
                    "Be dramatic. Max 15 words."}],
                task_type="speed",
                max_tokens=40,
                temperature=0.9,
            )
            if resp.success:
                blurb = resp.content.strip().strip('"')
        except Exception:
            pass

        player["ai_blurb"] = blurb
        nearby = [p for p in players if abs(p["rank"] - player["rank"]) <= 2 and p["user_id"] != user_id]
        return jsonify({"success": True, "player": player, "nearby_players": nearby[:4]}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leaderboard_bp.route("/api/leaderboard/rivalry", methods=["POST"])
def leaderboard_rivalry():
    """
    Generate an AI rivalry narrative between two players.
    Body: {"player1_id": "X", "player2_id": "Y"}
    """
    try:
        data      = request.get_json(silent=True) or {}
        p1_id     = data.get("player1_id", "")
        p2_id     = data.get("player2_id", "")
        if not p1_id or not p2_id:
            return jsonify({"success": False, "error": "player1_id and player2_id required"}), 200

        players = _get_all_players()
        p1 = next((p for p in players if p["user_id"] == p1_id), None)
        p2 = next((p for p in players if p["user_id"] == p2_id), None)

        if not p1 or not p2:
            return jsonify({"success": False, "error": "One or both players not found"}), 200

        from backend.services.llm_service import chat as llm_chat
        resp = llm_chat(
            messages=[{"role": "user", "content":
                f"Create a 3-sentence epic rivalry narrative between two MasterNoder champions:\n"
                f"Player 1: {p1['display_name']} — rank #{p1['rank']}, level {p1['level']}, {p1['xp']} XP\n"
                f"Player 2: {p2['display_name']} — rank #{p2['rank']}, level {p2['level']}, {p2['xp']} XP\n"
                "Make it dramatic, like a sports announcer. Mention their XP gap if relevant."}],
            task_type="speed",
            max_tokens=150,
            temperature=1.0,
        )

        narrative = resp.content.strip() if resp.success else (
            f"{p1['display_name']} and {p2['display_name']} are locked in an epic battle for supremacy!"
        )
        return jsonify({
            "success": True,
            "rivalry_narrative": narrative,
            "player1": p1,
            "player2": p2,
            "xp_gap": abs(p1["xp"] - p2["xp"]),
            "leader": p1 if p1["xp"] >= p2["xp"] else p2,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Registered after /top10, /player/<id>, /rivalry, etc. so those paths are not captured.
@leaderboard_bp.route("/api/leaderboard/<string:system>", methods=["GET"])
def leaderboard_by_system(system: str):
    """Per-system leaderboard (generation, activity, battle, trophies, xp, all)."""
    try:
        limit = min(1000, int(request.args.get("limit", 200)))
        offset = max(0, int(request.args.get("offset", 0)))
        sid = (system or "all").lower()
        base = _get_all_players()
        if sid in ("all", "xp"):
            total = len(base)
            page = base[offset : offset + limit]
            lb = [_normalize_leaderboard_row(p, _safe_int(p.get("xp", 0))) for p in page]
            return jsonify({"success": True, "leaderboard": lb, "total": total, "system": sid}), 200
        ranked = []
        for p in base:
            pc = dict(p)
            pc["_sort_pts"] = _points_for_system(pc, sid)
            ranked.append(pc)
        ranked.sort(key=lambda x: (x.get("_sort_pts", 0), x.get("xp", 0)), reverse=True)
        for i, p in enumerate(ranked):
            p["rank"] = i + 1
            p["badge"] = ["👑", "🥈", "🥉"][i] if i < 3 else "⚔️"
        total = len(ranked)
        page = ranked[offset : offset + limit]
        lb = []
        for p in page:
            pt = _safe_int(p.get("_sort_pts", 0))
            row = {k: v for k, v in p.items() if k != "_sort_pts"}
            lb.append(_normalize_leaderboard_row(row, pt))
        return jsonify({"success": True, "leaderboard": lb, "total": total, "system": sid}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
