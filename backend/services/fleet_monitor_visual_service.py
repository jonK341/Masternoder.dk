"""Fleet monitor visuals — themes + generator-encoded background pool."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_THEMES_PATH = os.path.join(_BASE, "data", "fleet_monitor_themes.json")


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_themes() -> Dict[str, Any]:
    data = _read_json(_THEMES_PATH, {})
    themes = list(data.get("themes") or [])
    return {
        "version": data.get("version", "1.0.0"),
        "default_theme_id": data.get("default_theme_id") or "fleet_neon",
        "themes": themes,
        "theme_count": len(themes),
    }


def _generator_encode_snippets() -> List[str]:
    out: List[str] = []
    try:
        from backend.services.generator_encode_service import encode_profile_public

        pub = encode_profile_public()
        for key, meta in (pub.get("profiles") or {}).items():
            label = meta.get("label") or key
            crf = meta.get("crf")
            raw = f"GEN|{key}|CRF{crf}|{label}"
            out.append(base64.b64encode(raw.encode("utf-8")).decode("ascii"))
    except Exception:
        pass
    return out


def _chapter_encode_snippets() -> List[str]:
    out: List[str] = []
    try:
        from backend.services.fleet_stream_composer_service import _load_catalog, decode_chapter_content

        for ch in (_load_catalog().get("chapters") or [])[:6]:
            text = decode_chapter_content(ch)
            if text:
                chunk = text[:120]
                out.append(base64.b64encode(chunk.encode("utf-8")).decode("ascii"))
    except Exception:
        pass
    return out


def encoded_background_pool(theme_id: Optional[str] = None) -> List[str]:
    pool = _generator_encode_snippets() + _chapter_encode_snippets()
    if theme_id:
        cat = load_themes()
        th = next((t for t in cat["themes"] if t.get("id") == theme_id), None)
        if th and th.get("encode_profile"):
            extra = base64.b64encode(
                f"ENCODE_PROFILE:{th['encode_profile']}".encode("utf-8")
            ).decode("ascii")
            pool.insert(0, extra)
    # de-dupe preserve order
    seen = set()
    uniq: List[str] = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq[:64]


def theme_by_id(theme_id: str) -> Dict[str, Any]:
    cat = load_themes()
    for t in cat["themes"]:
        if t.get("id") == theme_id:
            return dict(t)
    for t in cat["themes"]:
        if t.get("id") == cat["default_theme_id"]:
            return dict(t)
    return (cat["themes"] or [{}])[0] if cat["themes"] else {}


def visual_payload(*, theme_id: Optional[str] = None) -> Dict[str, Any]:
    cat = load_themes()
    tid = theme_id or cat.get("default_theme_id") or "fleet_neon"
    theme = theme_by_id(tid)
    return {
        "success": True,
        "default_theme_id": cat.get("default_theme_id"),
        "theme_count": cat.get("theme_count", 0),
        "themes": cat["themes"],
        "active_theme_id": theme.get("id", tid),
        "active_theme": theme,
        "encoded_pool": encoded_background_pool(theme.get("id")),
    }
