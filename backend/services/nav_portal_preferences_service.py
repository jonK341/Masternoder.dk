"""Portal nav template/theme preferences stored in user profile preferences."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _ROOT / "static" / "data" / "nav_portal_manifest.json"
_MANIFEST_IDS: Optional[Tuple[Set[str], Set[str]]] = None

PREF_TEMPLATE = "nav_portal_template"
PREF_THEME = "nav_portal_theme"
PREF_UPDATED = "nav_portal_updated_at"


def _manifest_ids() -> Tuple[Set[str], Set[str]]:
    global _MANIFEST_IDS
    if _MANIFEST_IDS is not None:
        return _MANIFEST_IDS
    templates: Set[str] = set()
    themes: Set[str] = set()
    try:
        raw = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        templates = set((raw.get("templates") or {}).keys())
        themes = set((raw.get("themes") or {}).keys())
    except Exception:
        pass
    _MANIFEST_IDS = (templates, themes)
    return _MANIFEST_IDS


def validate_template(template_id: Optional[str]) -> bool:
    if not template_id:
        return True
    templates, _ = _manifest_ids()
    return template_id in templates


def validate_theme(theme_id: Optional[str]) -> bool:
    if not theme_id:
        return True
    _, themes = _manifest_ids()
    return theme_id in themes


def _parse_preferences(profile: Optional[dict]) -> dict:
    if not profile:
        return {}
    raw = profile.get("preferences") or {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def get_nav_portal_preferences(user_id: str) -> Dict[str, Any]:
    from backend.services.user_onboarding import user_onboarding

    profile = user_onboarding.get_user_profile(user_id) or {}
    prefs = _parse_preferences(profile)
    return {
        "success": True,
        "user_id": user_id,
        "nav_template": prefs.get(PREF_TEMPLATE) or None,
        "nav_theme": prefs.get(PREF_THEME) or None,
        "updated_at": prefs.get(PREF_UPDATED) or None,
    }


def save_nav_portal_preferences(
    user_id: str,
    nav_template: Optional[str] = None,
    nav_theme: Optional[str] = None,
) -> Dict[str, Any]:
    from datetime import datetime, timezone

    from backend.services.user_onboarding import user_onboarding

    if nav_template is not None and not validate_template(nav_template):
        return {"success": False, "error": "invalid nav_template"}
    if nav_theme is not None and not validate_theme(nav_theme):
        return {"success": False, "error": "invalid nav_theme"}

    profile = user_onboarding.get_user_profile(user_id)
    prefs = _parse_preferences(profile)
    if nav_template is not None:
        prefs[PREF_TEMPLATE] = nav_template
    if nav_theme is not None:
        prefs[PREF_THEME] = nav_theme
    prefs[PREF_UPDATED] = datetime.now(timezone.utc).isoformat()

    result = user_onboarding.update_user_profile(user_id, {"preferences": prefs})
    if not result.get("success"):
        return {"success": False, "error": result.get("error") or "profile update failed"}

    return {
        "success": True,
        "user_id": user_id,
        "nav_template": prefs.get(PREF_TEMPLATE),
        "nav_theme": prefs.get(PREF_THEME),
        "updated_at": prefs.get(PREF_UPDATED),
    }
