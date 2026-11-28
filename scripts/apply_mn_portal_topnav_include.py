#!/usr/bin/env python3
"""Replace per-page navigation-toolbar includes with the static Portals topnav loader."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".venv",
    "node_modules",
    "removed_scripts_backup",
    "agent-tools",
    ".git",
    ".pytest-tmp-local",
    "__pycache__",
}

INCLUDE_JS = (
    '<script src="/static/js/mn-portal-topnav.js?v=20261128static" defer></script>'
)
INCLUDE_JS_VID = (
    '<script src="/static/js/mn-portal-topnav.js?v=20261128static" defer></script>'
)

TOOLBAR_JS_RE = re.compile(
    r"""<script\b[^>]*\bsrc=["'][^"']*navigation-toolbar\.js[^"']*["'][^>]*>\s*</script>""",
    re.I,
)
TOOLBAR_CSS_RE = re.compile(
    r"""\s*<link\b[^>]*\bhref=["'][^"']*navigation-toolbar\.css[^"']*["'][^>]*>""",
    re.I,
)
THEMES_CSS_RE = re.compile(
    r"""\s*<link\b[^>]*\bhref=["'][^"']*nav-portal-themes\.css[^"']*["'][^>]*>""",
    re.I,
)
PORTAL_VOID_SCRIPT_RE = re.compile(
    r"""\s*<script>\s*window\.MN_NAV_PORTAL_VOID\s*=\s*true\s*;\s*</script>""",
    re.I,
)
NAV_TEMPLATE_SCRIPT_RE = re.compile(
    r"""\s*<script>\s*window\.MN_NAV_TEMPLATE\s*=\s*['"][^'"]+['"]\s*;\s*</script>""",
    re.I,
)
INCLUDE_ALREADY_RE = re.compile(r"mn-portal-topnav\.js", re.I)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & SKIP_DIRS)


def transform(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    if not TOOLBAR_JS_RE.search(text) and not INCLUDE_ALREADY_RE.search(text):
        return text, changes

    if INCLUDE_ALREADY_RE.search(text):
        # Already has include: strip legacy toolbar script/css if still present.
        new_text, n = TOOLBAR_JS_RE.subn("", text)
        if n:
            text = new_text
            changes.append(f"removed {n} legacy toolbar script(s)")
    else:
        new_text, n = TOOLBAR_JS_RE.subn(INCLUDE_JS, text, count=1)
        if n:
            text = new_text
            changes.append("replaced toolbar script with mn-portal-topnav.js")
            # Remove any remaining duplicate toolbar scripts
            text2, n2 = TOOLBAR_JS_RE.subn("", text)
            if n2:
                text = text2
                changes.append(f"removed {n2} duplicate toolbar script(s)")
        else:
            # No script tag matched unexpectedly
            return text, changes

    new_text, n = TOOLBAR_CSS_RE.subn("", text)
    if n:
        text = new_text
        changes.append(f"removed {n} navigation-toolbar.css link(s)")

    new_text, n = THEMES_CSS_RE.subn("", text)
    if n:
        text = new_text
        changes.append(f"removed {n} nav-portal-themes.css link(s)")

    new_text, n = PORTAL_VOID_SCRIPT_RE.subn("", text)
    if n:
        text = new_text
        changes.append("removed MN_NAV_PORTAL_VOID page override")

    new_text, n = NAV_TEMPLATE_SCRIPT_RE.subn("", text)
    if n:
        text = new_text
        changes.append("removed MN_NAV_TEMPLATE page override")

    # Keep include near end of body if it somehow ended up duplicated
    matches = list(INCLUDE_ALREADY_RE.finditer(text))
    if len(matches) > 1:
        # leave first, remove other full script tags containing mn-portal-topnav.js
        scripts = list(
            re.finditer(
                r"""<script\b[^>]*\bsrc=["'][^"']*mn-portal-topnav\.js[^"']*["'][^>]*>\s*</script>""",
                text,
                re.I,
            )
        )
        if len(scripts) > 1:
            keep = scripts[0].group(0)
            text = re.sub(
                r"""<script\b[^>]*\bsrc=["'][^"']*mn-portal-topnav\.js[^"']*["'][^>]*>\s*</script>""",
                "",
                text,
                flags=re.I,
            )
            # re-insert once before </body> or at end
            if re.search(r"</body>", text, re.I):
                text = re.sub(r"</body>", f"    {keep}\n</body>", text, count=1, flags=re.I)
            else:
                text += "\n" + keep + "\n"
            changes.append("deduped mn-portal-topnav.js includes")

    # Normalize include path for vidgenerator absolute paths that pointed at /vidgenerator/static
    text2 = text.replace(
        'src="/vidgenerator/static/js/mn-portal-topnav.js',
        'src="/static/js/mn-portal-topnav.js',
    )
    if text2 != text:
        text = text2
        changes.append("normalized include to /static/js/mn-portal-topnav.js")

    # Ensure INCLUDE_JS string is canonical
    text = re.sub(
        r"""<script\b[^>]*\bsrc=["'][^"']*mn-portal-topnav\.js[^"']*["'][^>]*>\s*</script>""",
        INCLUDE_JS,
        text,
        count=1,
        flags=re.I,
    )

    return text, changes


def main() -> None:
    updated = 0
    scanned = 0
    for path in ROOT.rglob("*.html"):
        if should_skip(path):
            continue
        scanned += 1
        original = path.read_text(encoding="utf-8", errors="ignore")
        if "navigation-toolbar.js" not in original and "mn-portal-topnav.js" not in original:
            continue
        new_text, changes = transform(original)
        if not changes or new_text == original:
            continue
        path.write_text(new_text, encoding="utf-8")
        updated += 1
        rel = path.relative_to(ROOT)
        print(f"[OK] {rel}: {', '.join(changes)}")

    print(f"\nDone. Updated {updated} HTML files (scanned {scanned}).")


if __name__ == "__main__":
    main()
