#!/usr/bin/env python3
"""Normalize navigation-toolbar.css/js links to a single cache-bust version."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "20260910"
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "removed_scripts_backup",
    "server_backup",
    "vidgenerator.backup",
    ".pytest-tmp",
}

CSS_RE = re.compile(
    r'(<link rel="stylesheet" href="/static/css/navigation-toolbar\.css)(?:\?v=[^"]*)?(">)'
)
JS_RE = re.compile(
    r'(<script src="/static/js/navigation-toolbar\.js)(?:\?v=[^"]*)?(")'
)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    updated = CSS_RE.sub(rf"\1?v={VERSION}\2", text)
    updated = JS_RE.sub(rf"\1?v={VERSION}\2", updated)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        if path.suffix not in {".html", ".py"}:
            continue
        if "navigation-toolbar" not in path.read_text(encoding="utf-8", errors="replace"):
            continue
        if process_file(path):
            print(path.relative_to(ROOT))
            changed += 1
    print(f"Updated {changed} files to navigation-toolbar v={VERSION}")


if __name__ == "__main__":
    main()
