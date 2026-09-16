"""Super Encoder v2 — 250-upgrade catalog, unlocks, and encode tuning."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set

from backend.services.encoder_upgrade_service import (
    bulk_unlock_free,
    get_unlocked_ids,
    get_user_progress,
    is_unlocked,
    unlock_upgrade,
)
from backend.services.generator_encode_service import (
    ENCODE_CRF,
    ENCODE_PRESET,
    VALID_PROFILES,
    build_write_kwargs,
    hardware_encode_status,
)
from backend.services.super_encoder_service import build_super_encode_package, super_encoder_status

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_PATH = os.path.join(_BASE, "data", "encoder_v2_catalog.json")
_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_MTIME: float = 0.0

_PRESET_LADDER = ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow")


def _create_app_cfg() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            return (json.load(f).get("create_app") or {})
    except Exception:
        return {}


def load_catalog(force: bool = False) -> Dict[str, Any]:
    global _CATALOG_CACHE, _CATALOG_MTIME
    try:
        mtime = os.path.getmtime(_CATALOG_PATH)
    except Exception:
        mtime = 0.0
    if not force and _CATALOG_CACHE and mtime == _CATALOG_MTIME:
        return _CATALOG_CACHE
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _CATALOG_CACHE = data
            _CATALOG_MTIME = mtime
            return data
    except Exception:
        pass
    return {
        "version": 2,
        "encoder_id": "encoder_v2",
        "upgrade_count": 0,
        "upgrades": [],
        "categories": [],
    }


def catalog_upgrades() -> List[Dict[str, Any]]:
    data = load_catalog()
    raw = data.get("upgrades") or []
    return [u for u in raw if isinstance(u, dict) and isinstance(u.get("id"), str)]


def catalog_by_id() -> Dict[str, Dict[str, Any]]:
    return {u["id"]: u for u in catalog_upgrades()}


def _free_upgrade_ids() -> List[str]:
    return [
        u["id"]
        for u in catalog_upgrades()
        if (u.get("unlock") or {}).get("free")
    ]


def ensure_free_unlocks(user_id: str) -> Dict[str, Any]:
    return bulk_unlock_free(user_id, _free_upgrade_ids())


def encoder_v2_status(user_id: Optional[str] = None) -> Dict[str, Any]:
    cat = load_catalog()
    uid = str(user_id or "default_user")
    ensure_free_unlocks(uid)
    progress = get_user_progress(uid)
    total = int(cat.get("upgrade_count") or len(catalog_upgrades()))
    unlocked = progress.get("unlocked_count") or 0
    cfg = _create_app_cfg()
    v2_cfg = cfg.get("encoder_v2") or {}
    return {
        "success": True,
        "encoder_id": "encoder_v2",
        "encoder_version": 2,
        "label": cat.get("label") or "Super Encoder v2 — 250 upgrades",
        "upgrade_count": total,
        "unlocked_count": unlocked,
        "unlock_percent": round(100.0 * unlocked / total, 1) if total else 0.0,
        "categories": cat.get("categories") or [],
        "v1_encoder_id": "new_encoder_nr_1",
        "enabled": bool(v2_cfg.get("enabled", True)),
        "free_starter_count": len(_free_upgrade_ids()),
        "user_id": uid,
    }


def list_upgrades_for_user(
    user_id: str,
    *,
    category: Optional[str] = None,
    limit: int = 250,
    offset: int = 0,
) -> Dict[str, Any]:
    ensure_free_unlocks(user_id)
    unlocked = get_unlocked_ids(user_id)
    rows: List[Dict[str, Any]] = []
    for u in catalog_upgrades():
        if category and str(u.get("category") or u.get("chapter") or "") != category:
            continue
        uid = u["id"]
        unlock_meta = u.get("unlock") or {}
        rows.append({
            "id": uid,
            "index": u.get("index"),
            "name": u.get("name"),
            "desc": u.get("desc"),
            "category": u.get("category") or u.get("chapter"),
            "tier": u.get("tier"),
            "icon": u.get("icon"),
            "effect": u.get("effect"),
            "unlocked": uid in unlocked,
            "free": bool(unlock_meta.get("free")),
            "mn2_cost": float(unlock_meta.get("mn2_cost") or 0),
        })
    total = len(rows)
    page = rows[offset : offset + max(1, min(limit, 250))]
    return {
        "success": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "upgrades": page,
        "unlocked_count": len(unlocked),
    }


def purchase_upgrade(user_id: str, upgrade_id: str, *, skip_payment: bool = False) -> Dict[str, Any]:
    cat = catalog_by_id()
    uid = str(upgrade_id or "").strip()
    if uid not in cat:
        return {"success": False, "error": "unknown_upgrade", "upgrade_id": uid}

    if is_unlocked(user_id, uid):
        return {"success": True, "duplicate": True, "upgrade_id": uid, "progress": get_user_progress(user_id)}

    meta = cat[uid].get("unlock") or {}
    cost = float(meta.get("mn2_cost") or 0)
    if meta.get("free"):
        cost = 0.0

    if cost > 0 and not skip_payment:
        from backend.services.encoder_order_service import create_balance_order

        return create_balance_order(
            user_id,
            "encoder_v2_unlock",
            {"upgrade_id": uid},
            auto_fulfill=True,
        )

    res = unlock_upgrade(user_id, uid)
    res["mn2_spent"] = 0.0
    res["progress"] = get_user_progress(user_id)
    res["upgrade"] = cat[uid]
    return res


def aggregate_tuning(user_id: str) -> Dict[str, Any]:
    ensure_free_unlocks(user_id)
    unlocked = get_unlocked_ids(user_id)
    by_id = catalog_by_id()
    crf_delta = 0
    preset_step = 0
    lufs_target: Optional[float] = None
    hw_rank = 0
    quality_bias = 0
    qa_strictness = 0

    for uid in unlocked:
        u = by_id.get(uid)
        if not u:
            continue
        eff = u.get("effect") or {}
        etype = str(eff.get("type") or "")
        if etype == "video_tune":
            crf_delta += int(eff.get("crf_delta") or 0)
            preset_step += int(eff.get("preset_step") or 0)
        elif etype == "audio_tune":
            lufs = eff.get("lufs_target")
            if isinstance(lufs, (int, float)):
                lufs_target = float(lufs) if lufs_target is None else min(lufs_target, float(lufs))
        elif etype == "hw_path":
            hw_rank = max(hw_rank, int(eff.get("prefer_codec_rank") or 0))
        elif etype == "ai_rule":
            quality_bias += int(eff.get("quality_bias") or 0)
        elif etype == "qa_gate":
            qa_strictness += int(eff.get("strictness") or 0)

    return {
        "unlocked_count": len(unlocked),
        "crf_delta": crf_delta,
        "preset_step": preset_step,
        "lufs_target": lufs_target,
        "hw_rank": hw_rank,
        "quality_bias": quality_bias,
        "qa_strictness": qa_strictness,
    }


def _step_preset(base: str, steps: int) -> str:
    try:
        idx = _PRESET_LADDER.index(base)
    except ValueError:
        idx = 2
    idx = max(0, min(len(_PRESET_LADDER) - 1, idx + steps))
    return _PRESET_LADDER[idx]


def apply_v2_to_package(package: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
    if not user_id:
        return package
    cfg = _create_app_cfg()
    v2_cfg = cfg.get("encoder_v2") or {}
    if not v2_cfg.get("enabled", True):
        return package

    out = dict(package)
    tuning = aggregate_tuning(str(user_id))
    video = str(out.get("video_profile") or "standard").strip().lower()
    if video not in VALID_PROFILES:
        video = "standard"

    base_crf = ENCODE_CRF.get(video, 26)
    base_preset = ENCODE_PRESET.get(video, "veryfast")
    crf = max(15, min(30, base_crf + int(tuning.get("crf_delta") or 0)))
    preset = _step_preset(base_preset, int(tuning.get("preset_step") or 0) // 3)

    bias = int(tuning.get("quality_bias") or 0)
    if bias >= 8 and video != "ultra":
        video = "premium" if video in ("fast_ai", "standard") else "ultra"

    out["encoder_version"] = 2
    out["encoder_id"] = "encoder_v2"
    out["v1_encoder_id"] = package.get("encoder_id") or "new_encoder_nr_1"
    out["video_profile"] = video
    out["v2_tuning"] = {
        **tuning,
        "effective_crf": crf,
        "effective_preset": preset,
        "audio_lufs_target": tuning.get("lufs_target") or -16,
        "hardware": hardware_encode_status(),
    }
    return out


def apply_v2_write_kwargs(kwargs: Dict[str, Any], user_id: Optional[str], profile: str) -> Dict[str, Any]:
    if not user_id:
        return kwargs
    cfg = _create_app_cfg()
    if not (cfg.get("encoder_v2") or {}).get("enabled", True):
        return kwargs

    tuning = aggregate_tuning(str(user_id))
    out = dict(kwargs)
    prof = str(profile or "fast_ai").strip().lower()
    base_crf = ENCODE_CRF.get(prof, 26)
    crf = max(15, min(30, base_crf + int(tuning.get("crf_delta") or 0)))
    preset = _step_preset(str(out.get("preset") or ENCODE_PRESET.get(prof, "veryfast")), int(tuning.get("preset_step") or 0) // 3)

    params = list(out.get("ffmpeg_params") or [])
    params = [p for i, p in enumerate(params) if not (p == "-crf" or (i > 0 and params[i - 1] == "-crf"))]
    params = ["-crf", str(crf)] + [p for p in params if p != str(base_crf)]
    out["ffmpeg_params"] = params
    if "preset" in out:
        out["preset"] = preset
    out["encoder_v2_tuning"] = tuning
    return out


def build_v2_encode_package(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = dict(config or {})
    base = build_super_encode_package(cfg)
    user_id = cfg.get("user_id")
    return apply_v2_to_package(base, user_id)


def gather_encoder_v2_hub(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = dict(config or {})
    user_id = str(cfg.get("user_id") or "default_user")
    ensure_free_unlocks(user_id)
    status = encoder_v2_status(user_id)
    v1 = super_encoder_status()
    package = build_v2_encode_package(cfg)
    sample = list_upgrades_for_user(user_id, limit=12)
    tuning = aggregate_tuning(user_id)
    return {
        "success": True,
        "hub_id": "encoder_v2_hub",
        "encoder_version": 2,
        "label": "Super Encoder v2 — 250 upgrades",
        "status": status,
        "v1_status": v1,
        "package": package,
        "tuning": tuning,
        "preview_upgrades": sample.get("upgrades") or [],
        "sections": {
            "catalog": {
                "title": "250 upgrade lanes",
                "upgrade_count": status.get("upgrade_count"),
                "unlocked_count": status.get("unlocked_count"),
                "categories": status.get("categories") or [],
            },
            "tuning": {
                "title": "Active v2 tuning",
                "effective": package.get("v2_tuning") or tuning,
            },
            "package": {
                "title": "Merged v1 + v2 encode package",
                "selected": package,
            },
        },
    }


def write_kwargs_with_v2(doc_id: str, profile: str, user_id: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    base = build_write_kwargs(doc_id, profile, **kwargs)
    return apply_v2_write_kwargs(base, user_id, profile)


def apply_v2_audio_filter_chain(filter_chain: str, user_id: Optional[str]) -> str:
    """Adjust loudnorm LUFS target in FFmpeg audio filter chain from v2 unlocks."""
    import re

    chain = str(filter_chain or "")
    if not chain or not user_id:
        return chain
    cfg = _create_app_cfg()
    if not (cfg.get("encoder_v2") or {}).get("enabled", True):
        return chain
    tuning = aggregate_tuning(str(user_id))
    lufs = tuning.get("lufs_target")
    if lufs is None:
        return chain
    target = int(lufs) if float(lufs).is_integer() else float(lufs)
    return re.sub(r"(loudnorm=I=)-?\d+(?:\.\d+)?", rf"\g<1>{target}", chain)


def resolve_v2_encode_profile(config: Optional[Dict[str, Any]]) -> str:
    """Merge v1 profile selection with v2 unlock bias for the effective video profile."""
    cfg = dict(config or {})
    user_id = cfg.get("user_id")
    base_profile = str(cfg.get("encode_profile") or "fast_ai").strip().lower()
    if not user_id:
        return base_profile if base_profile in VALID_PROFILES else "fast_ai"
    pkg = apply_v2_to_package(
        build_super_encode_package({"encode_profile": base_profile, "user_id": user_id}),
        str(user_id),
    )
    return str(pkg.get("video_profile") or base_profile)
