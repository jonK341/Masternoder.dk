#!/usr/bin/env python3
"""Generate camgirls wave JSON files for scale toward 250 (waves of 25 stubs)."""
from __future__ import annotations

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# First/last name pools for stub display names (no PII).
_FIRST = [
    "Ava", "Bea", "Cleo", "Dina", "Elle", "Faye", "Gia", "Hera", "Ines", "Joss",
    "Kira", "Lana", "Mira", "Nia", "Orla", "Pia", "Quinn", "Rae", "Sia", "Tess",
    "Uma", "Vera", "Willa", "Xena", "Yara", "Zara", "Ada", "Blair", "Cora", "Dove",
]
_LAST = [
    "Ash", "Bloom", "Crest", "Dale", "Echo", "Frost", "Glen", "Hart", "Iris", "Jade",
    "Knot", "Lake", "Moss", "North", "Opal", "Park", "Quill", "Reed", "Shore", "Tide",
    "Vale", "West", "Yarn", "Zeal", "Birch", "Cove", "Dusk", "Elm", "Fox", "Grove",
]
_PALETTE = [
    ("#f472b6", "#9d174d"), ("#fb7185", "#be123c"), ("#c084fc", "#6b21a8"),
    ("#67e8f9", "#0e7490"), ("#4ade80", "#166534"), ("#fbbf24", "#92400e"),
    ("#94a3b8", "#1e293b"), ("#a78bfa", "#5b21b6"), ("#38bdf8", "#075985"),
    ("#fdba74", "#c2410c"), ("#34d399", "#047857"), ("#e879f9", "#a21caf"),
    ("#818cf8", "#3730a3"), ("#f43f5e", "#9f1239"), ("#fde047", "#a16207"),
    ("#2dd4bf", "#115e59"), ("#f97316", "#9a3412"), ("#0ea5e9", "#075985"),
]


def _slug(first: str, last: str, wave: int, index: int) -> str:
    base = f"{first}-{last}".lower().replace(" ", "-")
    return f"w{wave}-{base}-{index:02d}"


def build_wave(wave: int, size: int = 25) -> dict:
    performers = []
    for i in range(size):
        first = _FIRST[(wave * 7 + i) % len(_FIRST)]
        last = _LAST[(wave * 11 + i * 3) % len(_LAST)]
        c1, c2 = _PALETTE[(wave + i) % len(_PALETTE)]
        slug = _slug(first, last, wave, i + 1)
        name = f"{first} {last}"
        initials = (first[:1] + last[:1]).upper()
        performers.append(
            {
                "slug": slug,
                "display_name": name,
                "bio": f"{name} — MN2 camgirls studio host for wave {wave}.",
                "tagline": f"Live AI · wave {wave}",
                "unlock_price_mn2": 10 + ((wave + i) % 8),
                "media": {"slug": slug, "initials": initials, "c1": c1, "c2": c2},
            }
        )
    return {
        "wave": wave,
        "id_prefix": f"performer_wave{wave}_",
        "notes": f"Wave {wave} auto stubs toward 250-scale roster.",
        "performers": performers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate camgirls scale wave JSON files")
    parser.add_argument("--from-wave", type=int, default=5)
    parser.add_argument("--to-wave", type=int, default=10)
    parser.add_argument("--wave-size", type=int, default=25)
    args = parser.parse_args()
    out_dir = os.path.join(ROOT, "data", "camgirls_waves")
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for wave in range(args.from_wave, args.to_wave + 1):
        doc = build_wave(wave, size=args.wave_size)
        path = os.path.join(out_dir, f"wave{wave}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
            f.write("\n")
        total += len(doc["performers"])
        print(f"wrote {path} ({len(doc['performers'])})")
    print(f"total stubs: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
