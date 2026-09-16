"""Equip a trophy edition as the featured badge on the user profile."""
from __future__ import annotations

import json
from typing import Any, Dict


def _load_prefs(profile: Dict[str, Any]) -> Dict[str, Any]:
    prefs = profile.get("preferences") or {}
    if isinstance(prefs, str):
        try:
            prefs = json.loads(prefs) if prefs else {}
        except Exception:
            prefs = {}
    return prefs if isinstance(prefs, dict) else {}


def equip_trophy_on_profile(user_id: str, edition_key: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    ekey = (edition_key or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}
    if not ekey:
        return {"success": False, "error": "missing_edition_key"}

    try:
        from backend.services.trophy_metadata_service import find_edition_globally

        found = find_edition_globally(ekey)
        if not found.get("success"):
            return found
        if (found.get("user_id") or "").strip() != uid:
            return {"success": False, "error": "not_owner", "edition_key": ekey}

        edition = found.get("edition") or {}
        if edition.get("revoked"):
            return {"success": False, "error": "edition_revoked"}

        from backend.services.user_onboarding import user_onboarding

        profile = user_onboarding.get_user_profile(uid) or {}
        prefs = _load_prefs(profile)
        badges = prefs.get("trophy_badges") or {}
        badges["equipped_trophy_key"] = ekey
        badges["equipped_trophy_name"] = edition.get("item_name") or edition.get("item_id") or ekey
        badges["equipped_trophy_gif"] = (
            edition.get("gif_url") or edition.get("edition_gif_url") or edition.get("image_url")
        )
        badges["profile_label"] = badges.get("profile_label") or "Trophy collector"
        prefs["trophy_badges"] = badges
        update = user_onboarding.update_user_profile(uid, {"preferences": prefs})
        if not update.get("success", True):
            return update

        return {
            "success": True,
            "edition_key": ekey,
            "equipped_trophy_name": badges["equipped_trophy_name"],
            "equipped_trophy_gif": badges.get("equipped_trophy_gif"),
            "trophy_badges": badges,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def unequip_trophy_from_profile(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}

    try:
        from backend.services.user_onboarding import user_onboarding

        profile = user_onboarding.get_user_profile(uid) or {}
        prefs = _load_prefs(profile)
        badges = prefs.get("trophy_badges") or {}
        badges.pop("equipped_trophy_key", None)
        badges.pop("equipped_trophy_name", None)
        badges.pop("equipped_trophy_gif", None)
        prefs["trophy_badges"] = badges
        update = user_onboarding.update_user_profile(uid, {"preferences": prefs})
        if not update.get("success", True):
            return update
        return {"success": True, "trophy_badges": badges}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
