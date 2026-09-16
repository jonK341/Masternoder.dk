#!/usr/bin/env python3
"""Build data/encoder_v2_catalog.json — 250 Super Encoder v2 upgrades."""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_OUT = _ROOT / "data" / "encoder_v2_catalog.json"

_CATEGORIES = [
    ("video", "v2_vid", 38, "Video", "🎬"),
    ("audio", "v2_aud", 33, "Audio", "🎙️"),
    ("hardware", "v2_hw", 24, "E1 HW", "⚡"),
    ("ai", "v2_ai", 28, "AI tune", "🤖"),
    ("mobile", "v2_mob", 28, "Mobile", "📱"),
    ("podcast", "v2_pod", 22, "Podcast", "📻"),
    ("workflow", "v2_wf", 23, "Workflow", "🛠️"),
    ("mn2", "v2_mn2", 18, "MN2", "💠"),
    ("qa", "v2_qa", 19, "QA", "✅"),
    ("ops", "v2_ops", 17, "Ops", "📡"),
]


def _tier(i: int, total: int) -> str:
    pct = i / max(total, 1)
    if pct < 0.25:
        return "Core"
    if pct < 0.5:
        return "Signal"
    if pct < 0.75:
        return "Pro"
    return "Ultra"


def _effect(cat: str, i: int) -> dict:
    if cat == "video":
        return {"type": "video_tune", "crf_delta": -(i % 3), "preset_step": i % 4}
    if cat == "audio":
        return {"type": "audio_tune", "lufs_target": -16 - (i % 5), "filter_stage": i % 3}
    if cat == "hardware":
        return {"type": "hw_path", "prefer_codec_rank": i % 4}
    if cat == "ai":
        return {"type": "ai_rule", "quality_bias": i % 5}
    if cat == "mobile":
        return {"type": "mobile_surface", "shortcut_rank": i % 3}
    if cat == "podcast":
        return {"type": "podcast_meta", "episode_template": i % 4}
    if cat == "workflow":
        return {"type": "workflow", "retry_policy": i % 3}
    if cat == "mn2":
        return {"type": "mn2_rebate", "bps": i % 10}
    if cat == "qa":
        return {"type": "qa_gate", "strictness": i % 4}
    return {"type": "ops_hook", "metric": f"enc_v2_{i}"}


def build() -> dict:
    upgrades = []
    idx = 0
    for cat, prefix, count, label, icon in _CATEGORIES:
        for n in range(1, count + 1):
            idx += 1
            uid = f"{prefix}_{n:03d}"
            tier = _tier(n, count)
            free = idx <= 12 or (cat in ("qa", "ops") and n <= 2)
            upgrades.append({
                "id": uid,
                "index": idx,
                "chapter": cat,
                "category": cat,
                "icon": icon,
                "name": f"{label} Upgrade {n}",
                "desc": f"Super Encoder v2 {label.lower()} tuning lane {n} — unlocks finer encode control.",
                "tier": tier,
                "encoder_version": 2,
                "effect": _effect(cat, n),
                "unlock": {"free": free, "mn2_cost": 0.0 if free else round(0.001 + (idx % 7) * 0.0005, 4)},
            })
    return {
        "version": 2,
        "encoder_id": "encoder_v2",
        "label": "Super Encoder v2 — 250 upgrades",
        "upgrade_count": len(upgrades),
        "categories": [{"id": c[0], "prefix": c[1], "count": c[2], "label": c[3]} for c in _CATEGORIES],
        "upgrades": upgrades,
    }


def main() -> None:
    data = build()
    assert data["upgrade_count"] == 250, data["upgrade_count"]
    _OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {data['upgrade_count']} upgrades to {_OUT}")


if __name__ == "__main__":
    main()
