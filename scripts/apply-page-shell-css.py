#!/usr/bin/env python3
"""Add page-shell.css and missing base CSS stack to index.html pages."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE_SHELL = '<link rel="stylesheet" href="/static/css/page-shell.css?v=20260623">'
MODERN_DS = '<link rel="stylesheet" href="/static/css/modern-design-system.css">'
NAV_TOOLBAR = '<link rel="stylesheet" href="/static/css/navigation-toolbar.css">'

SKIP_DIRS = {
    "market",
    "proof-of-reserves",
    "staking-teams",
    "staking-leaderboard",
    "staking-monitor",
    "backend",
    ".pytest-tmp",
    "node_modules",
    "scripts",
    ".venv",
    "server_backup",
    "vidgenerator.backup",
}

SKIP_FILES: set[str] = set()


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    return len(rel.parts) > 2


def find_index_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("index.html")):
        if should_skip(path):
            continue
        if path in SKIP_FILES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if 'http-equiv="refresh"' in text and "url=" in text:
            continue
        files.append(path)
    return files


def insert_after_line(text: str, needle: str, insert: str) -> tuple[str, bool]:
    if insert in text:
        return text, False
    idx = text.find(needle)
    if idx == -1:
        return text, False
    end = text.find("\n", idx)
    if end == -1:
        end = len(text)
    return text[: end + 1] + insert + "\n" + text[end + 1 :], True


def ensure_modern_design_system(text: str) -> tuple[str, bool]:
    if "modern-design-system.css" in text:
        return text, False
    head_end = text.find("</head>")
    head = text[:head_end] if head_end != -1 else text
    m = re.search(
        r'(\s*)<link rel="stylesheet" href="/static/css/navigation-toolbar\.css[^"]*">',
        head,
    )
    if m:
        indent = m.group(1) or "    "
        insert = f"{indent}{MODERN_DS}\n"
        return text[: m.start()] + insert + text[m.start() :], True
    m = re.search(r'<link rel="stylesheet"', head)
    if m:
        return text[: m.start()] + MODERN_DS + "\n    " + text[m.start() :], True
    if head_end == -1:
        return text, False
    return text[:head_end] + f"\n    {MODERN_DS}\n" + text[head_end:], True


def ensure_page_shell(text: str) -> tuple[str, bool]:
    if "page-shell.css" in text:
        return text, False
    # Prefer after navigation-toolbar.css (any query string)
    m = re.search(
        r'<link rel="stylesheet" href="/static/css/navigation-toolbar\.css[^"]*">',
        text,
    )
    if m:
        end = text.find("\n", m.end())
        if end == -1:
            end = m.end()
        return text[: end + 1] + "    " + PAGE_SHELL + "\n" + text[end + 1 :], True
    # After modern-design-system if no nav
    m = re.search(
        r'<link rel="stylesheet" href="/static/css/modern-design-system\.css">',
        text,
    )
    if m:
        end = text.find("\n", m.end())
        if end == -1:
            end = m.end()
        return text[: end + 1] + "    " + PAGE_SHELL + "\n" + text[end + 1 :], True
    return text, False


def process_file(path: Path) -> list[str]:
    changes: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text

    text, ch = ensure_modern_design_system(text)
    if ch:
        changes.append("added modern-design-system.css")

    text, ch = ensure_page_shell(text)
    if ch:
        changes.append("added page-shell.css")

    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
    return changes


def main() -> None:
    updated = 0
    for path in find_index_files():
        changes = process_file(path)
        if changes:
            updated += 1
            rel = path.relative_to(ROOT)
            print(f"{rel}: {', '.join(changes)}")
    print(f"\nDone. Updated {updated} file(s).")


if __name__ == "__main__":
    main()
