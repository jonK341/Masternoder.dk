"""Camgirls studio — gifts, dances, voice/music metadata, standard program features."""
from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_FILE = os.path.join(_BASE, "data", "camgirls_studio_catalog.json")


def _read_catalog() -> Dict[str, Any]:
    if not os.path.isfile(_CATALOG_FILE):
        return {}
    try:
        with open(_CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def studio_catalog() -> Dict[str, Any]:
    cat = _read_catalog()
    return {
        "success": True,
        "standard_program_features": list(cat.get("standard_program_features") or []),
        "gifts": cat.get("gifts") or {},
        "dances": cat.get("dances") or {},
        "music_themes": cat.get("music_themes") or {},
        "voice_profiles": cat.get("voice_profiles") or {},
    }


def _performer_studio(row: Dict[str, Any]) -> Dict[str, Any]:
    studio = row.get("studio") if isinstance(row.get("studio"), dict) else {}
    cat = _read_catalog()
    gifts = studio.get("gifts") or list((cat.get("gifts") or {}).keys())
    dances = studio.get("dances") or list((cat.get("dances") or {}).keys())
    features = studio.get("features") or list(cat.get("standard_program_features") or [])
    music = studio.get("music_theme") or "neon_pulse"
    voice = studio.get("voice_profile") or "nova"
    goal = float(studio.get("goal_mn2") or row.get("goal_mn2") or 500)
    return {
        "features": features,
        "gifts": gifts,
        "dances": dances,
        "music_theme": music,
        "voice_profile": voice,
        "goal_mn2": goal,
        "goal_label": studio.get("goal_label") or f"Goal: {int(goal)} MN2",
        "catchphrases": list(studio.get("catchphrases") or []),
        "lingo_style": studio.get("lingo_style") or "",
    }


def public_studio(row: Dict[str, Any], *, unlocked: bool) -> Dict[str, Any]:
    """Studio block for API — teaser when locked, full when unlocked."""
    st = _performer_studio(row)
    teaser = {
        "voice_enabled": "voice_reply" in st["features"],
        "music_enabled": "room_music" in st["features"],
        "dance_enabled": "dance_requests" in st["features"],
        "feature_count": len(st["features"]),
    }
    if not unlocked:
        return teaser
    cat = _read_catalog()
    gift_defs = cat.get("gifts") or {}
    dance_defs = cat.get("dances") or {}
    music_defs = cat.get("music_themes") or {}
    voice_defs = cat.get("voice_profiles") or {}
    return {
        **teaser,
        "features": st["features"],
        "gifts": {gid: gift_defs.get(gid) for gid in st["gifts"] if gid in gift_defs},
        "dances": {did: dance_defs.get(did) for did in st["dances"] if did in dance_defs},
        "music": music_defs.get(st["music_theme"]) or {},
        "music_theme": st["music_theme"],
        "voice": voice_defs.get(st["voice_profile"]) or {},
        "voice_profile": st["voice_profile"],
        "goal_mn2": st["goal_mn2"],
        "goal_label": st["goal_label"],
        "catchphrases": st["catchphrases"][:8],
        "lingo_style": st["lingo_style"],
    }


def lingo_for_prompt(row: Dict[str, Any]) -> str:
    """Extra persona text from studio + agent lingo banks."""
    st = _performer_studio(row)
    parts: List[str] = []
    if st.get("lingo_style"):
        parts.append(f"Lingo style: {st['lingo_style']}")
    if st.get("catchphrases"):
        parts.append("Catchphrases you may sprinkle in: " + " | ".join(st["catchphrases"][:12]))
    try:
        from backend.services.camgirls_agents_service import agent_for_performer
        agent = agent_for_performer(str(row.get("id") or ""))
        if agent:
            bank = agent.get("lingo_banks") or {}
            for key, lines in bank.items():
                if isinstance(lines, list) and lines:
                    parts.append(f"{key}: " + " · ".join(str(x) for x in lines[:8]))
    except Exception:
        pass
    return "\n".join(parts)


def request_dance(user_id: str, performer_id: str, dance_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer, is_age_verified, _user_unlocks

    uid = (user_id or "").strip()
    if not is_age_verified(uid):
        return {"success": False, "error": "age_verification_required", "code": "age_verification_required"}
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    if not _user_unlocks(uid).get(pid):
        return {"success": False, "error": "unlock_required", "code": "unlock_required"}
    st = _performer_studio(row)
    if "dance_requests" not in st["features"]:
        return {"success": False, "error": "dance_not_enabled"}
    did = (dance_id or "").strip() or random.choice(st["dances"] or ["shimmy"])
    if did not in st["dances"]:
        return {"success": False, "error": "dance_not_available", "dance_id": did}
    cat = _read_catalog()
    dance = (cat.get("dances") or {}).get(did) or {}
    name = row.get("display_name") or pid
    lingo = dance.get("lingo") or f"{name} dances for you."
    catch = st.get("catchphrases") or []
    if catch and random.random() > 0.4:
        lingo = f"{random.choice(catch)} — {lingo}"
    return {
        "success": True,
        "performer_id": pid,
        "dance_id": did,
        "animation": dance.get("animation") or did,
        "lingo": lingo,
        "label": dance.get("label") or did,
    }


def tip_with_gift(
    user_id: str,
    performer_id: str,
    *,
    gift_id: Optional[str] = None,
    amount_mn2: Optional[float] = None,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer, tip_performer

    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    cat = _read_catalog()
    gifts = cat.get("gifts") or {}
    gid = (gift_id or "").strip()
    amt = amount_mn2
    gift_meta: Dict[str, Any] = {}
    if gid:
        gdef = gifts.get(gid)
        if not gdef:
            return {"success": False, "error": "gift_not_found", "gift_id": gid}
        amt = float(gdef.get("mn2") or amt or 0)
        gift_meta = {"gift_id": gid, "gift_label": gdef.get("label"), "gift_emoji": gdef.get("emoji"), "buzz": gdef.get("buzz")}
    if amt is None:
        amt = 10.0
    result = tip_performer(user_id, performer_id, float(amt))
    if result.get("success") and gift_meta:
        result.update(gift_meta)
        st = _performer_studio(row)
        catch = st.get("catchphrases") or []
        emoji = gift_meta.get("gift_emoji") or "✨"
        thanks = f"Thank you for the {gift_meta.get('gift_label') or 'gift'} {emoji}!"
        if catch:
            thanks = f"{random.choice(catch)} {thanks}"
        result["performer_reply"] = thanks
    return result


def gift_after_payment(
    user_id: str,
    performer_id: str,
    *,
    gift_id: Optional[str],
    payment_ref: str,
    provider: str = "paypal",
) -> Dict[str, Any]:
    from backend.services.camgirls_service import tip_performer_after_payment

    gid = (gift_id or "").strip()
    cat = _read_catalog()
    gifts = cat.get("gifts") or {}
    gdef = gifts.get(gid) if gid else None
    amt = float(gdef.get("mn2") or 10) if gdef else 10.0
    result = tip_performer_after_payment(user_id, performer_id, amt, payment_ref=payment_ref, provider=provider)
    if result.get("success") and gdef:
        result.update({
            "gift_id": gid,
            "gift_label": gdef.get("label"),
            "gift_emoji": gdef.get("emoji"),
        })
    return result
