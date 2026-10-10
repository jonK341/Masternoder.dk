#!/usr/bin/env python3
"""Generate minimal SVG icons referenced by navigation-toolbar.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img" / "nav"
OUT.mkdir(parents=True, exist_ok=True)

# Accent stroke for dark toolbar backgrounds
STROKE = "#00ff88"
FILL = "rgba(0,255,136,0.18)"

ICONS: dict[str, str] = {
    "home": '<path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
    "brand": '<circle cx="12" cy="12" r="9" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M8 12h8M12 8v8" stroke="{stroke}" stroke-width="1.4"/>',
    "trophy": '<path d="M7 5h10v3a5 5 0 0 1-10 0V5Zm2 11h6v2H9v-2Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
    "stories": '<path d="M6 5h9l3 3v11H6V5Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M9 10h6M9 13h4" stroke="{stroke}" stroke-width="1.1"/>',
    "game": '<rect x="5" y="8" width="14" height="8" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><circle cx="9" cy="12" r="1.2" fill="{stroke}"/><circle cx="15" cy="12" r="1.2" fill="{stroke}"/>',
    "casino": '<rect x="4" y="6" width="16" height="12" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><text x="12" y="14" text-anchor="middle" font-size="7" fill="{stroke}" font-family="sans-serif">7</text>',
    "news": '<path d="M5 6h14v12H5V6Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M8 9h8M8 12h8M8 15h5" stroke="{stroke}" stroke-width="1"/>',
    "battlegrounds": '<path d="M4 18 9 6l3 4 3-4 5 12H4Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
    "profile": '<circle cx="12" cy="9" r="3.5" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M5 19c1.5-3 4-4.5 7-4.5s5.5 1.5 7 4.5" fill="none" stroke="{stroke}" stroke-width="1.2"/>',
    "shop": '<path d="M6 8h12l-1 11H7L6 8Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M9 8V6a3 3 0 0 1 6 0v2" fill="none" stroke="{stroke}" stroke-width="1.2"/>',
    "customers": '<circle cx="9" cy="10" r="2.5" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/><circle cx="15" cy="10" r="2.5" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/><path d="M5 18c.8-2.5 2.5-4 4-4M15 14c1.5 0 3.2 1.5 4 4" stroke="{stroke}" stroke-width="1.1"/>',
    "chat": '<path d="M5 6h14v9H9l-4 3V6Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
    "lab": '<path d="M9 4h6l4 14H5L9 4Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><circle cx="12" cy="14" r="2" fill="{stroke}"/>',
    "starmap": '<circle cx="12" cy="12" r="8" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><circle cx="9" cy="10" r="1" fill="{stroke}"/><circle cx="14" cy="8" r="1" fill="{stroke}"/><circle cx="13" cy="14" r="1" fill="{stroke}"/>',
    "explorer": '<circle cx="11" cy="11" r="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/><path d="M16 16l4 4" stroke="{stroke}" stroke-width="1.4"/>',
}


def _svg(inner: str) -> str:
    body = inner.format(fill=FILL, stroke=STROKE)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" '
        'role="img" aria-hidden="true">\n'
        f"  {body}\n"
        "</svg>\n"
    )


def main() -> None:
    for name, markup in ICONS.items():
        path = OUT / f"{name}.svg"
        path.write_text(_svg(markup), encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
