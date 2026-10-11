"""Performer media packs — gallery, preview clip, icon/logo for resell."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MEDIA_ROOT = os.path.join(_ROOT, "static", "camgirls", "media")

# Slug + brand colors per performer (generated assets live under static/camgirls/media/<slug>/)
_MEDIA_META_OVERLAY_FILE = os.path.join(_ROOT, "data", "camgirls_performer_media_meta.json")

_PERFORMER_MEDIA_META: Dict[str, Dict[str, Any]] = {
    "performer_nova": {"slug": "nova", "initials": "NS", "c1": "#a855f7", "c2": "#4c1d95"},
    "performer_luna": {"slug": "luna", "initials": "LE", "c1": "#6366f1", "c2": "#312e81"},
    "performer_sage": {"slug": "sage", "initials": "SW", "c1": "#34d399", "c2": "#065f46"},
    "performer_ember": {"slug": "ember", "initials": "EB", "c1": "#f97316", "c2": "#9a3412"},
    "performer_iris": {"slug": "iris", "initials": "IP", "c1": "#ec4899", "c2": "#831843"},
    "performer_aurora": {"slug": "aurora", "initials": "AF", "c1": "#7fdbff", "c2": "#2e86ab"},
    "performer_jade": {"slug": "jade", "initials": "JL", "c1": "#4ade80", "c2": "#166534"},
    "performer_velvet": {"slug": "velvet", "initials": "VN", "c1": "#c084fc", "c2": "#581c87"},
    "performer_skylar": {"slug": "skylar", "initials": "SC", "c1": "#38bdf8", "c2": "#0c4a6e"},
    "performer_rio": {"slug": "rio", "initials": "RS", "c1": "#fbbf24", "c2": "#b45309"},
    "performer_mist": {"slug": "mist", "initials": "MS", "c1": "#94a3b8", "c2": "#334155"},
    "performer_honey": {"slug": "honey", "initials": "HG", "c1": "#fcd34d", "c2": "#ca8a04"},
    "performer_storm": {"slug": "storm", "initials": "SV", "c1": "#60a5fa", "c2": "#1e3a8a"},
    "performer_pixie": {"slug": "pixie", "initials": "PG", "c1": "#f472b6", "c2": "#be185d"},
    "performer_venus": {"slug": "venus", "initials": "VO", "c1": "#e879f9", "c2": "#701a75"},
}


def _load_media_meta_overlay() -> Dict[str, Dict[str, Any]]:
    if not os.path.isfile(_MEDIA_META_OVERLAY_FILE):
        return {}
    try:
        with open(_MEDIA_META_OVERLAY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return {}
    bucket = data.get("performers") if isinstance(data, dict) else None
    if isinstance(bucket, dict):
        return {str(k): v for k, v in bucket.items() if isinstance(v, dict)}
    return {}


def all_performer_media_meta() -> Dict[str, Dict[str, Any]]:
    merged = dict(_PERFORMER_MEDIA_META)
    merged.update(_load_media_meta_overlay())
    return merged


def get_performer_media_meta(performer_id: str) -> Dict[str, Any]:
    overlay = _load_media_meta_overlay()
    if performer_id in overlay:
        return overlay[performer_id]
    return _PERFORMER_MEDIA_META.get(performer_id) or {}


def upsert_performer_media_meta(
    entries: Dict[str, Dict[str, Any]],
    *,
    dry_run: bool = False,
) -> List[str]:
    """Merge media meta entries into data/camgirls_performer_media_meta.json."""
    updated: List[str] = []
    if not entries:
        return updated
    overlay = _load_media_meta_overlay()
    performers = dict(overlay)
    for pid, meta in entries.items():
        if not pid or not isinstance(meta, dict):
            continue
        clean = {
            k: meta[k]
            for k in ("slug", "initials", "c1", "c2")
            if meta.get(k)
        }
        if not clean.get("slug"):
            continue
        performers[pid] = {**performers.get(pid, {}), **clean}
        updated.append(pid)
    if dry_run or not updated:
        return updated
    os.makedirs(os.path.dirname(_MEDIA_META_OVERLAY_FILE), exist_ok=True)
    with open(_MEDIA_META_OVERLAY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "performers": performers,
                "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            },
            f,
            indent=2,
        )
        f.write("\n")
    return updated


def _slug_for(performer_id: str) -> str:
    meta = get_performer_media_meta(performer_id)
    if meta.get("slug"):
        return str(meta["slug"])
    return performer_id.replace("performer_", "", 1) or "demo"


def _media_base(slug: str) -> str:
    return f"/static/camgirls/media/{slug}"


def media_paths_for_performer(performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_media_paths import (
        gallery_urls,
        pick_media_url,
        preview_video_mp4_url,
        preview_video_url,
    )

    slug = _slug_for(performer_id)
    base = _media_base(slug)
    disk = os.path.join(_MEDIA_ROOT, slug)
    gallery = gallery_urls(disk, base) if os.path.isdir(disk) else [
        f"{base}/gallery-{i}.webp" for i in (1, 2, 3)
    ]
    preview_loop = pick_media_url(disk, base, "preview-loop") if os.path.isdir(disk) else f"{base}/preview-loop.svg"
    pack: Dict[str, Any] = {
        "gallery": gallery,
        "preview_poster_url": gallery[0] if gallery else f"{base}/gallery-1.webp",
        "preview_loop_svg_url": preview_loop,
        "icon_url": pick_media_url(disk, base, "icon") if os.path.isdir(disk) else f"{base}/icon.webp",
        "logo_url": pick_media_url(disk, base, "logo") if os.path.isdir(disk) else f"{base}/logo.svg",
        "avatar_hd_url": gallery[1] if len(gallery) > 1 else f"{base}/gallery-2.webp",
        "resell_manifest_url": f"{base}/resell-pack.json",
        "media_tier": "phase2_raster" if _disk_has_raster(disk) else "phase1_svg",
    }
    if os.path.isdir(disk):
        pack["preview_video_url"] = preview_video_url(disk, base)
        pack["preview_video_mp4_url"] = preview_video_mp4_url(disk, base)
    else:
        pack["preview_video_url"] = None
        pack["preview_video_mp4_url"] = None
    if not os.path.isdir(disk):
        pack["note"] = "media_assets_pending_run_generator"
    return pack


def _disk_has_raster(disk: str) -> bool:
    if not os.path.isdir(disk):
        return False
    for fn in os.listdir(disk):
        low = fn.lower()
        if low.endswith((".webp", ".png", ".jpg", ".jpeg")) and low.startswith("gallery-"):
            return True
    return False


def card_avatar_url(performer_id: str, fallback_avatar: str = "") -> str:
    """Best avatar for catalog cards (icon WebP > gallery > JSON avatar)."""
    paths = media_paths_for_performer(performer_id)
    return paths.get("icon_url") or paths.get("avatar_hd_url") or fallback_avatar


def resell_pack_for_performer(performer_id: str, display_name: str = "") -> Dict[str, Any]:
    paths = media_paths_for_performer(performer_id)
    slug = _slug_for(performer_id)
    meta = get_performer_media_meta(performer_id)
    assets = {
        "icon": paths["icon_url"],
        "logo": paths["logo_url"],
        "avatar_hd": paths["avatar_hd_url"],
        "gallery": paths["gallery"],
        "preview_video": paths["preview_video_url"],
        "preview_poster": paths["preview_poster_url"],
    }
    return {
        "performer_id": performer_id,
        "slug": slug,
        "display_name": display_name or performer_id,
        "license": "MN2 studio affiliate — resale allowed with disclosure on masternoder.dk",
        "assets": assets,
        "initials": meta.get("initials"),
        "brand_colors": [meta.get("c1"), meta.get("c2")],
    }


def attach_media_to_row(performer_row: Dict[str, Any], *, lite: bool = False) -> Dict[str, Any]:
    pid = str(performer_row.get("id") or "")
    if not pid:
        return performer_row
    media = media_paths_for_performer(pid)
    if lite:
        performer_row["media_preview"] = media.get("preview_poster_url")
        performer_row["icon_url"] = media.get("icon_url")
    else:
        performer_row["media"] = media
        try:
            from backend.services.camgirls_resell_shop_service import shop_item_id_for_performer

            shop_sku = shop_item_id_for_performer(pid)
        except Exception:
            shop_sku = None
        performer_row["resell"] = {
            "manifest_url": media.get("resell_manifest_url"),
            "logo_url": media.get("logo_url"),
            "icon_url": media.get("icon_url"),
            "shop_item_id": shop_sku,
            "shop_query": (
                f"highlight={shop_sku}"
                if shop_sku
                else "category=digital_goods&tag=camgirls"
            ),
        }
    return performer_row


def load_resell_manifest_file(performer_id: str) -> Optional[Dict[str, Any]]:
    slug = _slug_for(performer_id)
    path = os.path.join(_MEDIA_ROOT, slug, "resell-pack.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None
