"""Parse performer wave files for 250-scale roster batch onboarding."""
from __future__ import annotations

import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REQUIRED_PERFORMER_FIELDS = ("display_name",)
_MEDIA_FIELDS = ("slug", "initials", "c1", "c2")


def _abs_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(_ROOT, path)


def _slugify_token(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (raw or "").strip().lower())
    return s.strip("_") or "performer"


def _default_id_prefix(batch: Optional[int], wave_doc: Dict[str, Any]) -> str:
    if wave_doc.get("id_prefix"):
        return str(wave_doc["id_prefix"]).strip()
    if batch is not None:
        return f"performer_wave{batch}_"
    wave_num = wave_doc.get("wave")
    if wave_num is not None:
        return f"performer_wave{wave_num}_"
    return "performer_wave_"


def _parse_json_wave(path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {}, data
    if not isinstance(data, dict):
        raise ValueError("wave JSON must be an object or performers array")
    rows = data.get("performers")
    if not isinstance(rows, list):
        raise ValueError("wave JSON missing performers array")
    return data, rows


def _parse_csv_wave(path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        for raw in reader:
            if not raw:
                continue
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
            if row.get("_skip") or row.get("skip") in ("1", "true", "yes"):
                continue
            media: Dict[str, Any] = {}
            for key in _MEDIA_FIELDS:
                if row.get(key):
                    media[key] = row[key]
            if media:
                row["media"] = media
            for key in list(row.keys()):
                if key in _MEDIA_FIELDS:
                    del row[key]
            rows.append(row)
    return {}, rows


def load_wave_rows(path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Load wave document metadata + raw performer stub rows from JSON or CSV."""
    path = _abs_path(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    low = path.lower()
    if low.endswith(".csv"):
        return _parse_csv_wave(path)
    return _parse_json_wave(path)


def normalize_wave_stub(
    row: Dict[str, Any],
    *,
    index: int,
    id_prefix: str,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Turn one wave stub into a performer row + optional media meta entry."""
    if not isinstance(row, dict):
        raise ValueError(f"row {index}: expected object")
    if row.get("_example"):
        raise ValueError(f"row {index}: example row (_example) — remove before onboard")

    media_raw = row.get("media")
    media: Dict[str, Any] = {}
    if isinstance(media_raw, dict):
        media = {k: media_raw[k] for k in _MEDIA_FIELDS if media_raw.get(k)}

    pid = (row.get("id") or "").strip()
    slug_token = (row.get("slug") or media.get("slug") or "").strip()
    if not pid:
        suffix = _slugify_token(slug_token) if slug_token else f"{index:03d}"
        pid = f"{id_prefix}{suffix}"

    display_name = (row.get("display_name") or "").strip()
    if not display_name:
        raise ValueError(f"row {index} ({pid}): display_name required")

    media_slug = (media.get("slug") or slug_token or pid.replace("performer_", "", 1)).strip()
    media_slug = re.sub(r"[^a-zA-Z0-9\-]+", "-", media_slug).strip("-") or "studio"

    if not media.get("initials"):
        parts = display_name.split()
        if len(parts) >= 2:
            media["initials"] = (parts[0][:1] + parts[-1][:1]).upper()
        else:
            media["initials"] = (display_name[:2] or "MN").upper()
    media.setdefault("c1", "#6366f1")
    media.setdefault("c2", "#312e81")
    media["slug"] = media_slug

    performer: Dict[str, Any] = {
        "id": pid,
        "display_name": display_name,
        "bio": (row.get("bio") or "").strip() or f"{display_name} — MN2 camgirls studio host.",
        "tagline": (row.get("tagline") or "").strip() or "Live AI · studio chat",
        "unlock_price_mn2": int(row.get("unlock_price_mn2") or 12),
        "chat_price_mn2": int(row.get("chat_price_mn2") or 2),
        "tip_min_mn2": int(row.get("tip_min_mn2") or 5),
        "goal_mn2": int(row.get("goal_mn2") or 150),
        "active": row.get("active") not in (False, "false", "0", 0),
        "ai_enabled": row.get("ai_enabled") not in (False, "false", "0", 0),
    }
    avatar = (row.get("avatar_url") or "").strip()
    performer["avatar_url"] = avatar or f"/static/camgirls/media/{media_slug}/icon.svg"

    for extra in ("voice_persona", "studio_theme", "tags", "paypal_email"):
        if extra in row and row[extra] not in (None, ""):
            performer[extra] = row[extra]

    media_entry = {"slug": media["slug"], "initials": media["initials"], "c1": media["c1"], "c2": media["c2"]}
    return performer, media_entry


def build_wave_batch(
    path: str,
    *,
    wave_size: Optional[int] = None,
    batch: Optional[int] = None,
    id_prefix: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Parse wave file and return (performer_rows, media_meta_by_id, summary).
    """
    wave_doc, raw_rows = load_wave_rows(path)
    prefix = (id_prefix or "").strip() or _default_id_prefix(batch, wave_doc)

    performers: List[Dict[str, Any]] = []
    media_by_id: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    limit = wave_size if wave_size is not None and wave_size > 0 else len(raw_rows)
    for i, row in enumerate(raw_rows[:limit], start=1):
        if not isinstance(row, dict):
            errors.append(f"row {i}: not an object")
            continue
        if row.get("_example"):
            continue
        try:
            perf, media = normalize_wave_stub(row, index=i, id_prefix=prefix)
            performers.append(perf)
            if media:
                media_by_id[perf["id"]] = media
        except ValueError as exc:
            errors.append(str(exc))

    summary = {
        "source": path,
        "id_prefix": prefix,
        "wave": wave_doc.get("wave"),
        "batch": batch,
        "raw_rows": len(raw_rows),
        "selected": limit,
        "normalized": len(performers),
        "errors": errors,
    }
    return performers, media_by_id, summary
