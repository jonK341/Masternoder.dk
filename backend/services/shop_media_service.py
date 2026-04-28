"""
Shop catalog media: optional AI-generated stills and clips served as static URLs.

Manifest: data/shop_item_media.json (mapping item_id -> image_url, clip_url, prompts, timestamps).
Populated by: scripts/generate_shop_item_media.py
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST = os.path.join(_ROOT, "data", "shop_item_media.json")


def manifest_path() -> str:
    return _MANIFEST


def load_manifest() -> Dict[str, Any]:
    if not os.path.isfile(_MANIFEST):
        return {}
    try:
        with open(_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_manifest(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_MANIFEST), exist_ok=True)
    with open(_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_into_items(items: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Attach image_url / clip_url / media from manifest onto each item (mutates list)."""
    if not items:
        return items or []
    m = load_manifest()
    for item in items:
        iid = item.get("id")
        if not iid or iid not in m:
            continue
        entry = m[iid]
        if not isinstance(entry, dict):
            continue
        if entry.get("image_url"):
            item["image_url"] = entry["image_url"]
        if entry.get("poster_url"):
            item["poster_url"] = entry["poster_url"]
        if entry.get("clip_url"):
            item["clip_url"] = entry["clip_url"]
        if entry.get("gif_url"):
            item["gif_url"] = entry["gif_url"]
        if entry.get("sound_url"):
            item["sound_url"] = entry["sound_url"]
        if entry.get("generated_at"):
            item["media_generated_at"] = entry["generated_at"]
        if entry.get("prompt_image"):
            item["media_prompt_image"] = entry["prompt_image"]
    return items


def build_image_prompt(item: Dict[str, Any]) -> str:
    """Short English prompt for storefront hero still (Pollinations / SD)."""
    name = (item.get("name") or "item").strip()
    desc = (item.get("description") or "").strip()
    cat = (item.get("category") or "game item").strip()
    rarity = (item.get("rarity") or "").strip()
    base = f"Premium game shop item, {cat}, {name}"
    if rarity:
        base += f", {rarity} rarity"
    base += ", dark sci-fi UI, glowing accents, high detail product art, no text, centered icon-style illustration"
    if len(desc) > 0 and len(desc) < 200:
        base += f", concept: {desc[:180]}"
    return base[:480]


def safe_file_stem(item_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_id).strip("_")
    return (s[:96] or "item") + ".jpg"


def safe_clip_stem(item_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_id).strip("_")
    return (s[:96] or "item") + ".mp4"
