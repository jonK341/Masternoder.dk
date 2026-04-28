#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate short playful WAV chimes for featured shop items (stdlib only).

Writes static/shop/sounds/<id>.wav and sets sound_url in data/shop_item_media.json.

Default: items that already have clip_url (video/GIF set) plus a few extra catalog ids
for variety (themes / boosts).

  python scripts/generate_shop_item_sounds.py
  python scripts/generate_shop_item_sounds.py --extra shop-1 shop-4 shop-8
  python scripts/generate_shop_item_sounds.py --tag media_priority
"""
from __future__ import annotations

import argparse
import math
import os
import re
import struct
import sys
import time
import wave

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _freq_pair(item_id: str) -> tuple[float, float]:
    """Deterministic two-tone frequencies from id (Hz)."""
    h = 0
    for c in item_id:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    base = 180.0 + (h % 520)
    second = base * (1.12 + (h >> 8) % 8 / 100.0)
    return base, second


def _write_wav(path: str, item_id: str, duration: float = 0.42, sample_rate: int = 22050) -> None:
    f1, f2 = _freq_pair(item_id)
    n = int(sample_rate * duration)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Two-note "ding": first half f1, second half f2 with decay envelope
        half = n // 2
        for i in range(n):
            t = i / sample_rate
            env = math.exp(-3.2 * t / duration)  # decay
            if i < half:
                ph = 2 * math.pi * f1 * t
            else:
                ph = 2 * math.pi * f2 * t
            # soft square-ish mix
            s = 0.55 * math.sin(ph) + 0.12 * math.sin(2 * ph)
            s *= env
            if i < 400:  # attack
                s *= i / 400.0
            val = int(max(-32767, min(32767, s * 28000)))
            wf.writeframes(struct.pack("<h", val))


def _filter_by_tags(items, tag_any):
    if not tag_any:
        return items
    want = set(tag_any)
    return [it for it in items if want & set(it.get("tags") or [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", nargs="*", default=[], help="Additional item ids to add sounds for")
    ap.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Add sounds for shop items with any of these tags that have manifest media (OR)",
    )
    args = ap.parse_args()
    os.chdir(_ROOT)

    from backend.services.shop_media_service import load_manifest, manifest_path, save_manifest

    manifest = load_manifest()
    ids: list[str] = []

    for iid, entry in manifest.items():
        if isinstance(entry, dict) and entry.get("clip_url"):
            ids.append(iid)

    for x in args.extra:
        x = (x or "").strip()
        if x and x not in ids:
            ids.append(x)

    if args.tag:
        from backend.routes.shop_routes import _get_shop_items

        for it in _filter_by_tags(_get_shop_items() or [], args.tag):
            iid = it.get("id")
            if not iid or iid in ids:
                continue
            m = manifest.get(iid)
            if isinstance(m, dict) and (m.get("clip_url") or m.get("image_url")):
                ids.append(iid)

    # Default spice: a few early catalog rows if manifest had no clips
    if not ids:
        for j in ("shop-1", "shop-4", "shop-7", "shop-10", "shop-15", "shop-20"):
            if j in manifest:
                ids.append(j)

    out_dir = os.path.join(_ROOT, "static", "shop", "sounds")
    seen = set()
    for iid in ids:
        if iid in seen:
            continue
        seen.add(iid)
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", iid).strip("_") or "item"
        fname = stem + ".wav"
        disk = os.path.join(out_dir, fname)
        rel = f"/static/shop/sounds/{fname}"
        print(f"Sound: {iid} -> {rel}")
        _write_wav(disk, iid)
        entry = manifest.get(iid) or {}
        entry["sound_url"] = rel
        entry["sound_generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest[iid] = entry

    save_manifest(manifest)
    print()
    print(f"Manifest: {manifest_path()}")
    print(f"Sounds written: {len(seen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
