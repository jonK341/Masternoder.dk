#!/usr/bin/env python3
"""Add mn-portal-topnav.js to site pages that still lack any topnav include."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = (
    '    <script src="/static/js/mn-portal-topnav.js?v=20261128static" defer></script>\n'
)
TARGETS = [
    "business-control/index.html",
    "discord-play/index.html",
    "starmap25/index.html",
    "casino/crash/index.html",
    "casino/go/index.html",
    "casino/slots/index.html",
    "casino/small-games/index.html",
    "discord/verify/index.html",
    "legal/privacy/index.html",
    "legal/terms/index.html",
]


def add_include(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "mn-portal-topnav.js" in text or "navigation-toolbar.js" in text:
        return False
    if re.search(r"</body>", text, re.I):
        new_text = re.sub(r"</body>", INCLUDE + "</body>", text, count=1, flags=re.I)
    elif re.search(r"</head>", text, re.I):
        new_text = re.sub(r"</head>", INCLUDE + "</head>", text, count=1, flags=re.I)
    else:
        new_text = text + "\n" + INCLUDE
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    for rel in TARGETS:
        path = ROOT / rel
        if not path.is_file():
            print(f"[SKIP] missing {rel}")
            continue
        if add_include(path):
            print(f"[OK] added include to {rel}")
        else:
            print(f"[INFO] already has include: {rel}")


if __name__ == "__main__":
    main()
