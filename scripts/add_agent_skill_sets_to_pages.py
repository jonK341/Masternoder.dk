"""
Add agent skill sets integration to HTML pages (enhanced 10x).

- Scope: all HTML under project root (vidgenerator + any other dirs), not just vidgenerator.
- Options: version query, defer/async, media, backup, dry-run, configurable paths.
- Report: summary, updated/skipped/error lists, optional JSON report file.
- Marks enriched pages with data-agent-skill-sets="enriched".
"""
import os
import re
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Defaults (can override via env or args)
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CSS_PATH = "/vidgenerator/static/css/agent-skill-sets.css"
DEFAULT_JS_PATH = "/vidgenerator/static/js/agent-skill-sets.js"
DEFAULT_VERSION = None  # set to e.g. "20260305" for cache busting
BACKUP_DIR_NAME = "agent_skill_sets_backup"
REPORT_DIR = PROJECT_ROOT / "logs"
REPORT_FILENAME = "add_agent_skill_sets_report.json"


def get_css_link(css_path: str, version: str = None, media: str = None) -> str:
    """Build CSS link tag with optional version and media."""
    href = css_path
    if version:
        href += "?v=" + version
    media_attr = f' media="{media}"' if media else ""
    return f'<link rel="stylesheet" href="{href}"{media_attr}>'


def get_js_script(js_path: str, version: str = None, defer: bool = True, async_attr: bool = False) -> str:
    """Build script tag with optional version, defer, async."""
    src = js_path
    if version:
        src += "?v=" + version
    attrs = []
    if defer:
        attrs.append("defer")
    if async_attr:
        attrs.append("async")
    attr_str = " " + " ".join(attrs) if attrs else ""
    return f'<script src="{src}"{attr_str}></script>'


def add_agent_skill_sets_to_file(
    file_path: Path,
    css_path: str = DEFAULT_CSS_PATH,
    js_path: str = DEFAULT_JS_PATH,
    version: str = None,
    defer_js: bool = True,
    media_css: str = None,
    add_data_attribute: bool = True,
) -> dict:
    """
    Add agent skill sets CSS and JS to an HTML file.
    Returns dict: modified (bool), already_has_css (bool), already_has_js (bool), error (str|None).
    """
    result = {"modified": False, "already_has_css": False, "already_has_js": False, "error": None}
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        result["error"] = str(e)
        return result

    css_link = get_css_link(css_path, version=version, media=media_css)
    # Match existing link that points to agent-skill-sets.css (any query)
    existing_css_pattern = re.compile(
        r'<link\s+rel=["\']stylesheet["\']\s+href=["\'][^"\']*agent-skill-sets\.css[^"\']*["\']',
        re.I,
    )
    if existing_css_pattern.search(content):
        result["already_has_css"] = True
    if css_link not in content and not result["already_has_css"]:
        if "</head>" in content:
            content = content.replace("</head>", f"    {css_link}\n</head>", 1)
            result["modified"] = True

    js_script = get_js_script(js_path, version=version, defer=defer_js)
    existing_js_pattern = re.compile(
        r'<script\s+[^>]*src=["\'][^"\']*agent-skill-sets\.js[^"\']*["\']',
        re.I,
    )
    if existing_js_pattern.search(content):
        result["already_has_js"] = True
    if js_script not in content and not result["already_has_js"]:
        if "</body>" in content:
            content = content.replace("</body>", f"    {js_script}\n</body>", 1)
            result["modified"] = True

    if add_data_attribute and result["modified"]:
        # Add data-agent-skill-sets="enriched" to <html> if present
        if "<html" in content and "data-agent-skill-sets" not in content:
            content = re.sub(
                r"(<html\s+[^>]*)(>)",
                r'\1 data-agent-skill-sets="enriched"\2',
                content,
                count=1,
                flags=re.I,
            )
            if "<html>" in content and "data-agent-skill-sets" not in content:
                content = content.replace("<html>", '<html data-agent-skill-sets="enriched">', 1)

    if result["modified"]:
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            result["error"] = str(e)
            result["modified"] = False

    return result


def find_html_files(root: Path, include_vidgenerator_only: bool = False) -> list:
    """Find all HTML files under root. If include_vidgenerator_only, only under vidgenerator/."""
    if include_vidgenerator_only:
        base = root / "vidgenerator"
        if not base.exists():
            return []
        return list(base.rglob("*.html"))
    return list(root.rglob("*.html"))


def main():
    parser = argparse.ArgumentParser(
        description="Add agent skill sets CSS/JS to HTML pages (enhanced)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Process all HTML in project; default is only vidgenerator/",
    )
    parser.add_argument(
        "--css",
        type=str,
        default=DEFAULT_CSS_PATH,
        help="CSS href path",
    )
    parser.add_argument(
        "--js",
        type=str,
        default=DEFAULT_JS_PATH,
        help="JS src path",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=os.environ.get("AGENT_SKILL_SETS_VERSION", DEFAULT_VERSION),
        help="Query version for cache busting (e.g. 20260305)",
    )
    parser.add_argument(
        "--no-defer",
        action="store_true",
        help="Do not add defer to script tag",
    )
    parser.add_argument(
        "--media",
        type=str,
        default=None,
        help="CSS media (e.g. 'print' for print then all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only report what would change",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup each file before modifying (under logs/agent_skill_sets_backup/)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Write JSON report to this path (default: logs/add_agent_skill_sets_report.json)",
    )
    parser.add_argument(
        "--no-data-attr",
        action="store_true",
        help="Do not add data-agent-skill-sets attribute",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    vidgenerator_only = not getattr(args, "all_pages", False)
    html_files = find_html_files(root, include_vidgenerator_only=vidgenerator_only)

    # Optionally backup
    backup_root = None
    if args.backup and not args.dry_run:
        backup_root = REPORT_DIR / BACKUP_DIR_NAME
        backup_root.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = backup_root / ts
        backup_root.mkdir(parents=True, exist_ok=True)

    updated = []
    skipped = []
    errors = []
    would_update = []

    for html_file in html_files:
        try:
            rel = html_file.relative_to(root)
        except ValueError:
            rel = html_file

        if args.backup and backup_root and not args.dry_run:
            dest = backup_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(html_file, dest)
            except Exception as e:
                errors.append({"file": str(rel), "error": f"backup: {e}"})

        result = add_agent_skill_sets_to_file(
            html_file,
            css_path=args.css,
            js_path=args.js,
            version=args.version,
            defer_js=not args.no_defer,
            media_css=args.media,
            add_data_attribute=not args.no_data_attr,
        )

        if result.get("error"):
            errors.append({"file": str(rel), "error": result["error"]})
            continue

        if result["modified"]:
            if args.dry_run:
                would_update.append(str(rel))
            else:
                updated.append(str(rel))
                print(f"  Updated: {rel}")
        else:
            reason = []
            if result.get("already_has_css"):
                reason.append("css")
            if result.get("already_has_js"):
                reason.append("js")
            skipped.append({"file": str(rel), "reason": ",".join(reason) or "no head/body"})
            print(f"  Skipped: {rel} ({reason or 'already has support'})")

    # Summary
    print()
    print("=" * 60)
    print("Agent skill sets integration (enhanced)")
    print("=" * 60)
    print(f"  Root: {root}")
    print(f"  HTML files found: {len(html_files)}")
    if args.dry_run:
        print(f"  Would update: {len(would_update)}")
        for f in would_update[:20]:
            print(f"    - {f}")
        if len(would_update) > 20:
            print(f"    ... and {len(would_update) - 20} more")
    else:
        print(f"  Updated: {len(updated)}")
        print(f"  Skipped: {len(skipped)}")
    print(f"  Errors: {len(errors)}")
    if errors:
        for e in errors[:10]:
            print(f"    - {e['file']}: {e['error']}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    print("=" * 60)

    # Report file
    report_path = args.report or (REPORT_DIR / REPORT_FILENAME)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "root": str(root),
        "vidgenerator_only": vidgenerator_only,
        "dry_run": args.dry_run,
        "total_files": len(html_files),
        "updated": updated if not args.dry_run else would_update,
        "updated_count": len(updated) if not args.dry_run else len(would_update),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "errors": errors,
        "error_count": len(errors),
        "options": {
            "css": args.css,
            "js": args.js,
            "version": args.version,
            "defer": not args.no_defer,
            "media": args.media,
        },
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Report saved to: {report_path}")

    return 0 if not errors else 1


if __name__ == "__main__":
    exit(main())
