"""
Compendium (Rulebook V2.1) routes — record page views and award compendium_points.
Integrated with unified points and user index/ID.
All endpoints resolve user_id via session > body/query > identification.
"""
from flask import Blueprint, jsonify, request

compendium_bp = Blueprint("compendium", __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')

COMPENDIUM_POINTS_PER_PAGE = 15
POINT_TYPE = "compendium_points"
SOURCE = "compendium_view"


@compendium_bp.route("/api/compendium/view", methods=["POST"])
def record_view():
    """Record a compendium page view and award compendium_points. Uses user_id from body."""
    data = request.get_json() or {}
    user_id = _resolve_uid()
    page_number = data.get("page_number") or data.get("page")
    if page_number is None:
        try:
            page_number = int(request.args.get("page_number", 0))
        except Exception:
            page_number = 0
    else:
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 0
    if page_number < 1 or page_number > 25:
        return jsonify({"success": False, "error": "page_number must be 1-25"}), 400

    try:
        from backend.services.compendium_access_service import can_access_page, get_access_status

        if not can_access_page(user_id, page_number):
            return jsonify({
                "success": False,
                "error": "premium_required",
                "page_number": page_number,
                **get_access_status(user_id),
            }), 403
    except Exception:
        pass

    amount = COMPENDIUM_POINTS_PER_PAGE
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            unified_points_db.add_points(
                user_id,
                POINT_TYPE,
                amount,
                source=SOURCE,
                metadata={"page_number": page_number, "compendium": "rulebook_v2_1", "part": "II" if page_number == 11 else "I"},
            )
        try:
            from backend.services.user_engagement import record_compendium_page
            record_compendium_page(user_id, page_number)
        except Exception:
            pass
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('compendium')
        except Exception:
            pass
        try:
            from backend.services.ai_user_controller import on_user_activity
            on_user_activity(user_id, "compendium_read", {"page_number": page_number})
        except Exception:
            pass
        crypto_reward = {}
        try:
            from backend.services.compendium_crypto_rewards_service import award_page_read_reward
            crypto_reward = award_page_read_reward(user_id, page_number)
        except Exception:
            pass
        return jsonify({
            "success": True,
            "user_id": user_id,
            "page_number": page_number,
            "points_awarded": amount,
            "point_type": POINT_TYPE,
            "crypto_reward": crypto_reward,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@compendium_bp.route("/api/compendium/crypto-rewards", methods=["GET"])
def compendium_crypto_rewards():
    """Public MN2 earn rates for compendium page reads and theory study."""
    from backend.services.compendium_crypto_rewards_service import get_crypto_rewards_info

    return jsonify(get_crypto_rewards_info(_resolve_uid())), 200


@compendium_bp.route("/api/compendium/access", methods=["GET"])
def compendium_access():
    user_id = _resolve_uid()
    from backend.services.compendium_access_service import get_access_status

    return jsonify(get_access_status(user_id)), 200


def _annotate_pages_with_access(pages: list, user_id: str) -> list:
    from backend.services.compendium_access_service import FREE_PAGE_MAX, can_access_page

    out = []
    for row in pages:
        p = dict(row)
        num = p.get("number")
        if num is not None:
            p["free"] = int(num) <= FREE_PAGE_MAX
            p["locked"] = not can_access_page(user_id, int(num))
        else:
            p["free"] = True
            p["locked"] = False
        out.append(p)
    return out


@compendium_bp.route("/api/compendium/pages", methods=["GET"])
def list_pages():
    """Return unified compendium: Comm Psych, Hunters, Rulebooks V1–V16."""
    user_id = _resolve_uid()
    part_i = [
        {"number": 1, "title": "Magtdynamikker 1-3", "url": "/compendium/page-1.html", "section": "I"},
        {"number": 2, "title": "Magt + Social 4-6", "url": "/compendium/page-2.html", "section": "I"},
        {"number": 3, "title": "Social indflydelse 7-8", "url": "/compendium/page-3.html", "section": "I"},
        {"number": 4, "title": "Retorik 9-11", "url": "/compendium/page-4.html", "section": "I"},
        {"number": 5, "title": "Retorik + Psyk 12-14", "url": "/compendium/page-5.html", "section": "I"},
        {"number": 6, "title": "Psyk krig 15-16", "url": "/compendium/page-6.html", "section": "I"},
        {"number": 7, "title": "Digital magt 17-19", "url": "/compendium/page-7.html", "section": "I"},
        {"number": 8, "title": "Digital + Monet 20-21", "url": "/compendium/page-8.html", "section": "I"},
        {"number": 9, "title": "Monetarisering 22-24", "url": "/compendium/page-9.html", "section": "I"},
        {"number": 10, "title": "Halo Effect (25)", "url": "/compendium/page-10.html", "section": "I"},
    ]
    part_ii = [
        {"number": 11, "title": "Trophy Hunters Rulebook — 19 Spells", "url": "/compendium/hunters-rulebook.html", "section": "II"},
    ]
    part_iii = [
        {"number": 12, "title": "V1 Core Rules", "url": "/compendium/rulebook-v1.html", "section": "III"},
        {"number": 13, "title": "V4 Star Map", "url": "/compendium/rulebook-v4.html", "section": "III"},
        {"number": 14, "title": "V5 Effect Clusters", "url": "/compendium/rulebook-v5.html", "section": "III"},
        {"number": 15, "title": "V6 Electric Magnet", "url": "/compendium/rulebook-v6.html", "section": "III"},
        {"number": 16, "title": "V7 Unified Points", "url": "/compendium/rulebook-v7.html", "section": "III"},
        {"number": 17, "title": "V8 Agents", "url": "/compendium/rulebook-v8.html", "section": "III"},
        {"number": 18, "title": "V9 Shop", "url": "/compendium/rulebook-v9.html", "section": "III"},
        {"number": 19, "title": "V10 Battle", "url": "/compendium/rulebook-v10.html", "section": "III"},
        {"number": 20, "title": "V11 DNA Theory", "url": "/compendium/rulebook-v11.html", "section": "III"},
        {"number": 21, "title": "V12 Generator", "url": "/compendium/rulebook-v12.html", "section": "III"},
        {"number": 22, "title": "V13 Geo & Session", "url": "/compendium/rulebook-v13.html", "section": "III"},
        {"number": 23, "title": "V14 Analytics", "url": "/compendium/rulebook-v14.html", "section": "III"},
        {"number": 24, "title": "V15 Master Index", "url": "/compendium/", "section": "III"},
        {"number": 25, "title": "V16 Sync Mechanisms", "url": "/compendium/rulebook-v16.html", "section": "III"},
    ]
    pages = part_i + part_ii + part_iii
    pages = _annotate_pages_with_access(pages, user_id)
    part_i = _annotate_pages_with_access(part_i, user_id)
    part_ii = _annotate_pages_with_access(part_ii, user_id)
    part_iii = _annotate_pages_with_access(part_iii, user_id)
    from backend.services.compendium_access_service import get_access_status

    return jsonify({
        "success": True,
        "name": "Compendium V1–V16",
        "pages": pages,
        "access": get_access_status(user_id),
        "extras": [
            {"title": "V3.2 Systemic Protocols", "url": "/compendium/rulebook-v3-2.html", "section": "III", "note": "Browse-only; no compendium page number"},
        ],
        "sections": [
            {"id": "I", "name": "Communication Psychology (25 teorier)", "pages": part_i},
            {"id": "II", "name": "Trophy Hunters Rulebook (19 spells)", "pages": part_ii},
            {"id": "III", "name": "Rulebooks V1–V16", "pages": part_iii},
        ],
    }), 200
